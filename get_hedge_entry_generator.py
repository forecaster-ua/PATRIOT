import requests
from statistics import mean
from typing import Dict, List, Set, Optional, Tuple
import json
from collections import Counter

# Импортируем telegram_bot для отправки уведомлений
try:
    from telegram_bot import telegram_bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    print("⚠️ telegram_bot не найден, отправка в Telegram недоступна")
    TELEGRAM_AVAILABLE = False
    telegram_bot = None

class MultiSignalAnalyzer:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.timeframes = ["1h", "4h", "1d"]
        self.api_url = "http://194.135.94.212:8001/multi_signal"
        
    def get_multi_signals(self) -> Tuple[Optional[List[Dict]], float]:
        """Получаем мульти-сигналы для всех таймфреймов одним запросом"""
        import time
        
        # Инициализируем время для безопасности
        start_time = time.time()
        response_time = 0.0
        
        try:
            # Формируем URL с множественными параметрами timeframes
            url_parts = [f"{self.api_url}?pair={self.ticker}"]
            
            # Добавляем все таймфреймы как отдельные параметры
            for tf in self.timeframes:
                url_parts.append(f"timeframes={tf}")
            
            # Добавляем служебные параметры в конце
            url_parts.extend([
                "lang=uk",
                "model_type=xgb"
            ])
            
            full_url = "&".join(url_parts)
            
            # Засекаем время перед запросом
            request_start = time.time()
            response = requests.get(full_url, timeout=30)
            request_end = time.time()
            response_time = round(request_end - request_start, 2)
            
            if response.status_code == 200:
                data = response.json()
                return data, response_time
            else:
                print(f"❌ Ошибка API: {response.status_code}")
                return None, response_time
                
        except Exception as e:
            # Безопасно вычисляем время даже при исключении
            error_time = time.time()
            response_time = round(error_time - start_time, 2)
            print(f"❌ Ошибка при запросе к API: {e}")
            return None, response_time

    def format_confidence(self, confidence: float) -> str:
        """Форматирует confidence с предупреждающим значком для высоких значений"""
        if confidence > 90:
            return f"{confidence}% ⚠️ ({confidence}%)"
        return f"{confidence}%"

    def format_telegram_message(self, parsed_signals: Dict, dominant_direction: str, corrections: List[Dict], opposite_mains: List[Dict], response_time: float) -> str:
        """Форматирует данные для отправки в Telegram (дублирует формат терминала)"""
        # Генерируем тот же формат, что и в терминале
        message = f"📊 Анализ: {self.ticker}\n"
        message += "--------------------------------------------------\n"
        message += f"⏱️ Время ответа API: {response_time}с\n"
        message += f"📊 Структура сигналов для {self.ticker}:\n"
        message += f"Простых сигналов: {len(parsed_signals['simple'])}\n"
        message += f"Сложных сигналов: {len(parsed_signals['complex'])}\n\n"
        
        # Доминирующее направление
        message += f"🎯 Доминирующее направление: {dominant_direction}\n\n"
        
        # Простые сигналы
        message += f"📈 ПРОСТЫЕ СИГНАЛЫ:\n"
        for signal in parsed_signals['simple']:
            message += f"   {signal['timeframe']}: {signal['signal']} @ {signal['entry_price']} "
            message += f"(TP: {signal['take_profit']}, SL: {signal['stop_loss']}, "
            message += f"Conf: {self.format_confidence(signal['confidence'])})\n"
        message += "\n"
        
        # Сложные сигналы
        message += f"🔄 СЛОЖНЫЕ СИГНАЛЫ:\n"
        for signal in parsed_signals['complex']:
            main = signal['main_signal']
            corr = signal['correction_signal']
            message += f"   {signal['timeframe']}:\n"
            message += f"      Main: {main['type']} @ {main['entry']} "
            message += f"(TP: {main['tp']}, SL: {main['sl']}, Conf: {self.format_confidence(main['confidence'])})\n"
            message += f"      Correction: {corr['type']} @ {corr['entry']} "
            message += f"(TP: {corr['tp']}, SL: {corr['sl']}, Conf: {self.format_confidence(corr['confidence'])})\n"
        message += "\n"
        
        # Важные противотрендовые main сигналы
        if opposite_mains:
            message += f"🚨 ВАЖНЫЕ ПРОТИВОТРЕНДОВЫЕ MAIN СИГНАЛЫ ({len(opposite_mains)} найдено):\n"
            for signal in opposite_mains:
                message += f"   {signal['timeframe']}: {signal['direction']} @ {signal['entry_price']} "
                message += f"{self.format_confidence(signal['confidence'])} - Сильный уровень против доминирующего {dominant_direction}\n"
            message += "\n"
        
        # Коррекционные сделки
        if corrections:
            message += f"⚠️  КОРРЕКЦИОННЫЕ СДЕЛКИ ({len(corrections)} найдено):\n\n"
            
            for i, correction in enumerate(corrections, 1):
                message += f"   📍 Коррекция #{i} ({correction['timeframe']}, {correction['type']}):\n"
                message += f"      Направление: {correction['direction']} "
                message += f"(против доминирующего {dominant_direction})\n"
                message += f"      Вход: {correction['entry_price']}\n"
                message += f"      TP: {correction['take_profit']}\n"
                message += f"      SL: {correction['stop_loss']}\n"
                message += f"      Уверенность: {self.format_confidence(correction['confidence'])}\n"
                message += f"      R/R: {correction['risk_reward']}\n"
                
                # Рассчитываем потенциалы
                potentials = self.calculate_potentials_to_levels(correction, parsed_signals, dominant_direction)
                
                if potentials:
                    message += f"      \n      🎯 ПОТЕНЦИАЛЫ К УРОВНЯМ КРУПНЫХ ТФ:\n"
                    for j, pot in enumerate(potentials[:5], 1):  # Показываем топ-5
                        message += f"         {j}. {pot['timeframe']} ({pot['level_type']}): "
                        message += f"{pot['level_value']} = {pot['potential_percent']}% "
                        message += f"({pot['direction']})\n"
                else:
                    message += f"      ❌ Нет доступных уровней для расчета потенциалов\n"
                message += "\n"
        else:
            message += f"✅ Коррекционных сделок не найдено\n"
            message += f"   Все сигналы соответствуют доминирующему направлению: {dominant_direction}\n\n"
        
        # Основные сигналы по доминирующему направлению
        message += f"🚀 ОСНОВНЫЕ СИГНАЛЫ ПО ДОМИНИРУЮЩЕМУ НАПРАВЛЕНИЮ ({dominant_direction}):\n"
        
        # Из простых сигналов
        for signal in parsed_signals['simple']:
            if signal['signal'] == dominant_direction:
                message += f"   {signal['timeframe']}: {signal['signal']} @ {signal['entry_price']} "
                message += f"(Conf: {self.format_confidence(signal['confidence'])})\n"
        
        # Из main сигналов сложных
        for signal in parsed_signals['complex']:
            main = signal['main_signal']
            if main['type'] == dominant_direction:
                message += f"   {signal['timeframe']} (main): {main['type']} @ {main['entry']} "
                message += f"(Conf: {self.format_confidence(main['confidence'])})\n"
        
        # Добавляем итоговую статистику
        message += f"   🎯 Доминирующее направление: {dominant_direction}\n"
        message += f"   📈 Простых сигналов: {len(parsed_signals['simple'])}\n"
        message += f"   🔄 Сложных сигналов: {len(parsed_signals['complex'])}\n"
        message += f"   ⚠️ Коррекционных сделок: {len(corrections)}\n"
        
        return message

    def ask_user_confirmation(self) -> bool:
        """Запрашивает подтверждение пользователя для отправки в Telegram"""
        if not TELEGRAM_AVAILABLE:
            print("❌ Telegram недоступен для отправки")
            return False
        
        while True:
            response = input(f"\n📱 Отправить анализ {self.ticker} в Telegram? (y/n): ").strip().lower()
            if response in ['y', 'yes', 'да']:
                return True
            elif response in ['n', 'no', 'нет']:
                return False
            else:
                print("Пожалуйста, введите 'y' для да или 'n' для нет")

    def send_to_telegram(self, message: str) -> bool:
        """Отправляет сообщение в Telegram"""
        if not TELEGRAM_AVAILABLE or telegram_bot is None:
            print("❌ Telegram недоступен")
            return False
            
        try:
            # Используем метод отправки из telegram_bot
            telegram_bot.send_message(message)
            print("✅ Сообщение успешно отправлено в Telegram")
            return True
        except Exception as e:
            print(f"❌ Ошибка при отправке в Telegram: {e}")
            return False

    def parse_signals(self, data: List[Dict]) -> Dict:
        """Парсит сигналы и разделяет на простые и сложные"""
        simple_signals = []  # Сигналы без main/correction
        complex_signals = []  # Сигналы с main/correction
        
        for signal_data in data:
            timeframe = signal_data.get('timeframe')
            
            # Проверяем тип сигнала
            if 'main_signal' in signal_data and 'correction_signal' in signal_data:
                # Сложный сигнал
                complex_signals.append({
                    'timeframe': timeframe,
                    'pair': signal_data.get('pair'),
                    'current_price': signal_data.get('current_price'),
                    'main_signal': signal_data['main_signal'],
                    'correction_signal': signal_data['correction_signal']
                })
            else:
                # Простой сигнал
                simple_signals.append({
                    'timeframe': timeframe,
                    'pair': signal_data.get('pair'),
                    'signal': signal_data.get('signal'),
                    'entry_price': signal_data.get('entry_price'),
                    'take_profit': signal_data.get('take_profit'),
                    'stop_loss': signal_data.get('stop_loss'),
                    'confidence': signal_data.get('confidence'),
                    'risk_reward': signal_data.get('risk_reward'),
                    'current_price': signal_data.get('current_price')
                })
        
        return {'simple': simple_signals, 'complex': complex_signals}

    def determine_dominant_direction(self, parsed_signals: Dict) -> str:
        """Определяет доминирующее направление"""
        all_directions = []
        
        # Собираем все направления из простых сигналов
        for signal in parsed_signals['simple']:
            direction = signal.get('signal')
            if direction:
                all_directions.append(direction)
        
        # Собираем направления из main_signal сложных сигналов
        for signal in parsed_signals['complex']:
            main_direction = signal.get('main_signal', {}).get('type')
            if main_direction:
                all_directions.append(main_direction)
        
        if not all_directions:
            return "НЕОПРЕДЕЛЕНО"
        
        # Находим наиболее часто встречающееся направление
        direction_counts = Counter(all_directions)
        dominant = direction_counts.most_common(1)[0][0]
        
        return dominant

    def find_opposite_main_signals(self, parsed_signals: Dict, dominant_direction: str) -> List[Dict]:
        """Находит противотрендовые main сигналы - сильные уровни сопротивления"""
        opposite_mains = []
        
        for signal in parsed_signals['complex']:
            main_signal = signal.get('main_signal', {})
            main_direction = main_signal.get('type')
            
            # Если main сигнал противоположен доминирующему - это сильный уровень
            if main_direction and main_direction != dominant_direction:
                opposite_mains.append({
                    'timeframe': signal['timeframe'],
                    'direction': main_direction,
                    'entry_price': main_signal.get('entry'),
                    'take_profit': main_signal.get('tp'),
                    'stop_loss': main_signal.get('sl'),
                    'confidence': main_signal.get('confidence'),
                    'risk_reward': main_signal.get('risk_reward')
                })
        
        return opposite_mains

    def find_correction_trades(self, parsed_signals: Dict, dominant_direction: str) -> List[Dict]:
        """Находит коррекционные сделки"""
        corrections = []
        
        # Проверяем сложные сигналы
        for signal in parsed_signals['complex']:
            correction_signal = signal.get('correction_signal', {})
            
            # Добавляем коррекционный сигнал если он есть
            if correction_signal.get('type'):
                corrections.append({
                    'timeframe': signal['timeframe'],
                    'type': 'CORRECTION',
                    'direction': correction_signal.get('type'),
                    'entry_price': correction_signal.get('entry'),
                    'take_profit': correction_signal.get('tp'),
                    'stop_loss': correction_signal.get('sl'),
                    'confidence': correction_signal.get('confidence'),
                    'risk_reward': correction_signal.get('risk_reward'),
                    'current_price': signal.get('current_price')
                })
        
        return corrections

    def calculate_potentials_to_levels(self, correction: Dict, parsed_signals: Dict, dominant_direction: str) -> List[Dict]:
        """Рассчитывает потенциалы с фильтрацией по противоположному доминирующему направлению"""
        correction_price = correction['entry_price']
        if not correction_price:
            return []
        
        potential_levels = []
        timeframe_hierarchy = ['1h', '4h', '1d']
        
        try:
            current_tf_index = timeframe_hierarchy.index(correction['timeframe'])
        except ValueError:
            return []
        
        # Определяем нужное направление (противоположное доминирующему)
        target_direction = 'UP' if dominant_direction == 'SHORT' else 'DOWN'
        
        # Ищем уровни в более крупных таймфреймах
        for i in range(current_tf_index + 1, len(timeframe_hierarchy)):
            target_tf = timeframe_hierarchy[i]
            
            # Ищем только entry_price и stop_loss в простых сигналах
            for signal in parsed_signals['simple']:
                if signal['timeframe'] == target_tf:
                    levels = [
                        ('entry', signal.get('entry_price')),
                        ('sl', signal.get('stop_loss'))
                    ]
                    
                    for level_type, level_value in levels:
                        if level_value and level_value != correction_price:
                            direction = 'UP' if level_value > correction_price else 'DOWN'
                            
                            # Фильтруем только по нужному направлению
                            if direction == target_direction:
                                distance = abs(level_value - correction_price)
                                potential_percent = (distance / correction_price) * 100
                                
                                potential_levels.append({
                                    'timeframe': target_tf,
                                    'level_type': level_type,
                                    'level_value': level_value,
                                    'distance': distance,
                                    'potential_percent': round(potential_percent, 2),
                                    'direction': direction
                                })
            
            # Ищем только entry и stop_loss в main_signal сложных сигналов
            for signal in parsed_signals['complex']:
                if signal['timeframe'] == target_tf:
                    main_signal = signal.get('main_signal', {})
                    
                    levels = [
                        ('entry', main_signal.get('entry')),
                        ('sl', main_signal.get('sl'))
                    ]
                    
                    for level_type, level_value in levels:
                        if level_value and level_value != correction_price:
                            direction = 'UP' if level_value > correction_price else 'DOWN'
                            
                            # Фильтруем только по нужному направлению
                            if direction == target_direction:
                                distance = abs(level_value - correction_price)
                                potential_percent = (distance / correction_price) * 100
                                
                                potential_levels.append({
                                    'timeframe': target_tf,
                                    'level_type': level_type,
                                    'level_value': level_value,
                                    'distance': distance,
                                    'potential_percent': round(potential_percent, 2),
                                    'direction': direction
                                })
        
        # Сортируем по таймфрейму (1h -> 4h -> 1d), затем по расстоянию
        tf_order = {'1h': 1, '4h': 2, '1d': 3}
        potential_levels.sort(key=lambda x: (tf_order.get(x['timeframe'], 4), x['distance']))
        
        return potential_levels[:3]  # Возвращаем только 2-3 ближайших

    def process(self, ask_telegram=True):
        """Основной метод анализа мульти-сигналов"""
        # Получаем данные с измерением времени ответа
        raw_data, response_time = self.get_multi_signals()
        if not raw_data:
            print("❌ Не удалось получить данные от API")
            return None
        
        # Парсим сигналы
        parsed_signals = self.parse_signals(raw_data)
        
        print(f"📊 Анализ: {self.ticker}")
        print("--------------------------------------------------")
        print(f"⏱️ Время ответа API: {response_time}с")
        print(f"📊 Структура сигналов для {self.ticker}:")
        print(f"Простых сигналов: {len(parsed_signals['simple'])}")
        print(f"Сложных сигналов: {len(parsed_signals['complex'])}")
        
        # Определяем доминирующее направление
        dominant_direction = self.determine_dominant_direction(parsed_signals)
        print(f"\n🎯 Доминирующее направление: {dominant_direction}")
        
        # Выводим все сигналы по категориям
        print(f"\n📈 ПРОСТЫЕ СИГНАЛЫ:")
        for signal in parsed_signals['simple']:
            print(f"   {signal['timeframe']}: {signal['signal']} @ {signal['entry_price']} "
                  f"(TP: {signal['take_profit']}, SL: {signal['stop_loss']}, "
                  f"Conf: {self.format_confidence(signal['confidence'])})")
        
        print(f"\n🔄 СЛОЖНЫЕ СИГНАЛЫ:")
        for signal in parsed_signals['complex']:
            main = signal['main_signal']
            corr = signal['correction_signal']
            print(f"   {signal['timeframe']}:")
            print(f"      Main: {main['type']} @ {main['entry']} "
                  f"(TP: {main['tp']}, SL: {main['sl']}, Conf: {self.format_confidence(main['confidence'])})")
            print(f"      Correction: {corr['type']} @ {corr['entry']} "
                  f"(TP: {corr['tp']}, SL: {corr['sl']}, Conf: {self.format_confidence(corr['confidence'])})")
        
        # Находим противотрендовые main сигналы (сильные уровни)
        opposite_mains = self.find_opposite_main_signals(parsed_signals, dominant_direction)
        
        # Показываем противотрендовые main сигналы
        if opposite_mains:
            print(f"\n🚨 ВАЖНЫЕ ПРОТИВОТРЕНДОВЫЕ MAIN СИГНАЛЫ ({len(opposite_mains)} найдено):")
            for signal in opposite_mains:
                print(f"   {signal['timeframe']}: {signal['direction']} @ {signal['entry_price']} "
                      f"{self.format_confidence(signal['confidence'])} - Сильный уровень против доминирующего {dominant_direction}")
        
        # Находим коррекционные сделки
        corrections = self.find_correction_trades(parsed_signals, dominant_direction)
        
        if corrections:
            print(f"\n⚠️  КОРРЕКЦИОННЫЕ СДЕЛКИ ({len(corrections)} найдено):")
            
            for i, correction in enumerate(corrections, 1):
                print(f"\n   📍 Коррекция #{i} ({correction['timeframe']}, {correction['type']}):")
                print(f"      Направление: {correction['direction']} "
                      f"(против доминирующего {dominant_direction})")
                print(f"      Вход: {correction['entry_price']}")
                print(f"      TP: {correction['take_profit']}")
                print(f"      SL: {correction['stop_loss']}")
                print(f"      Уверенность: {self.format_confidence(correction['confidence'])}")
                print(f"      R/R: {correction['risk_reward']}")
                
                # Рассчитываем потенциалы
                potentials = self.calculate_potentials_to_levels(correction, parsed_signals, dominant_direction)
                
                if potentials:
                    print(f"      \n      🎯 ПОТЕНЦИАЛЫ К УРОВНЯМ КРУПНЫХ ТФ:")
                    for j, pot in enumerate(potentials[:5], 1):  # Показываем топ-5
                        print(f"         {j}. {pot['timeframe']} ({pot['level_type']}): "
                              f"{pot['level_value']} = {pot['potential_percent']}% "
                              f"({pot['direction']})")
                else:
                    print(f"      ❌ Нет доступных уровней для расчета потенциалов")
        
        else:
            print(f"\n✅ Коррекционных сделок не найдено")
            print(f"   Все сигналы соответствуют доминирующему направлению: {dominant_direction}")
        
        # Выводим основные сигналы по доминирующему направлению
        print(f"\n🚀 ОСНОВНЫЕ СИГНАЛЫ ПО ДОМИНИРУЮЩЕМУ НАПРАВЛЕНИЮ ({dominant_direction}):")
        
        # Из простых сигналов
        for signal in parsed_signals['simple']:
            if signal['signal'] == dominant_direction:
                print(f"   {signal['timeframe']}: {signal['signal']} @ {signal['entry_price']} "
                      f"(Conf: {self.format_confidence(signal['confidence'])})")
        
        # Из main сигналов сложных
        for signal in parsed_signals['complex']:
            main = signal['main_signal']
            if main['type'] == dominant_direction:
                print(f"   {signal['timeframe']} (main): {main['type']} @ {main['entry']} "
                      f"(Conf: {self.format_confidence(main['confidence'])})")
        
        # Предлагаем отправить в Telegram (только если ask_telegram=True)
        if ask_telegram:
            if self.ask_user_confirmation():
                telegram_message = self.format_telegram_message(parsed_signals, dominant_direction, corrections, opposite_mains, response_time)
                self.send_to_telegram(telegram_message)
        
        # Возвращаем результаты для использования в групповом анализе
        return {
            'parsed_signals': parsed_signals,
            'dominant_direction': dominant_direction,
            'corrections': corrections,
            'opposite_mains': opposite_mains,
            'response_time': response_time
        }

def test_multiple_tickers():
    """Тестирует анализ для нескольких тикеров с групповой отправкой в Telegram"""
    test_tickers = ["BTCUSDT", "AVAXUSDT", "TONUSDT"]
    results = []  # Собираем результаты анализа
    
    print(f"🔍 Анализ {len(test_tickers)} тикеров: {', '.join(test_tickers)}")
    print("="*80)
    
    # Анализируем все тикеры и собираем результаты
    for ticker in test_tickers:
        print(f"\n📊 Анализ: {ticker}")
        print("-"*50)
        
        analyzer = MultiSignalAnalyzer(ticker)
        
        # Анализируем без отправки в Telegram (ask_telegram=False)
        result = analyzer.process(ask_telegram=False)
        
        if not result:
            print(f"❌ Не удалось проанализировать {ticker}")
            continue
        
        # Показываем краткую информацию  
        print(f"   🎯 Доминирующее направление: {result['dominant_direction']}")
        print(f"   📈 Простых сигналов: {len(result['parsed_signals']['simple'])}")
        print(f"   🔄 Сложных сигналов: {len(result['parsed_signals']['complex'])}")
        print(f"   ⚠️ Коррекционных сделок: {len(result['corrections'])}")
        
        # Сохраняем результат для возможной отправки
        results.append({
            'ticker': ticker,
            'analyzer': analyzer,
            'parsed_signals': result['parsed_signals'],
            'dominant_direction': result['dominant_direction'],
            'corrections': result['corrections'],
            'opposite_mains': result['opposite_mains'],
            'response_time': result.get('response_time', 0.0)  # Сохраняем реальное время
        })
    
    print(f"\n{'='*80}")
    print(f"✅ Анализ завершен для {len(results)} тикеров")
    
    # Спрашиваем один раз о отправке всех результатов
    if results and ask_multiple_telegram_confirmation(results):
        send_multiple_to_telegram(results)
        
    print(f"{'='*80}")

def ask_multiple_telegram_confirmation(results: List[Dict]) -> bool:
    """Запрашивает подтверждение для отправки результатов по всем тикерам"""
    if not TELEGRAM_AVAILABLE:
        print("❌ Telegram недоступен для отправки")
        return False
    
    ticker_list = [result['ticker'] for result in results]
    
    while True:
        response = input(f"\n📱 Отправить анализ всех тикеров ({', '.join(ticker_list)}) в Telegram? (y/n): ").strip().lower()
        if response in ['y', 'yes', 'да']:
            return True
        elif response in ['n', 'no', 'нет']:
            return False
        else:
            print("Пожалуйста, введите 'y' для да или 'n' для нет")

def send_multiple_to_telegram(results: List[Dict]) -> None:
    """Отправляет результаты по всем тикерам в Telegram пачкой"""
    if not TELEGRAM_AVAILABLE or telegram_bot is None:
        print("❌ Telegram недоступен")
        return
    
    print(f"\n📤 Отправка {len(results)} сообщений в Telegram...")
    
    success_count = 0
    for i, result in enumerate(results, 1):
        ticker = result['ticker']
        analyzer = result['analyzer']
        
        try:
            # Форматируем сообщение с реальным временем ответа
            message = analyzer.format_telegram_message(
                result['parsed_signals'], 
                result['dominant_direction'], 
                result['corrections'],
                result['opposite_mains'],
                result['response_time']  # Используем реальное время ответа
            )
            
            # Отправляем
            telegram_bot.send_message(message)
            print(f"   ✅ {i}/{len(results)} - {ticker} отправлен")
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ {i}/{len(results)} - Ошибка отправки {ticker}: {e}")
    
    print(f"\n🎉 Отправка завершена: {success_count}/{len(results)} сообщений успешно отправлено")

def interactive_mode():
    """Интерактивный режим выбора тикера и отправки"""
    print("🔍 MultiSignal Analyzer")
    print("="*40)
    print("1. Анализ одного тикера")
    print("2. Анализ всех тестовых тикеров (BTCUSDT, ETHUSDT, AVAXUSDT)")
    print("3. Выход")
    
    while True:
        choice = input("\nВыберите режим (1-3): ").strip()
        
        if choice == "1":
            ticker = input("Введите тикер (например, AVAXUSDT): ").strip().upper()
            if ticker:
                analyzer = MultiSignalAnalyzer(ticker)
                analyzer.process()
            break
            
        elif choice == "2":
            test_multiple_tickers()
            break
            
        elif choice == "3":
            print("До свидания!")
            break
            
        else:
            print("Пожалуйста, выберите 1, 2 или 3")

# Пример использования
if __name__ == "__main__":
    # Для быстрого тестирования - анализируем AVAXUSDT
    # Раскомментируйте interactive_mode() для интерактивного режима
    
    # analyzer = MultiSignalAnalyzer("AVAXUSDT")
    # analyzer.process()
    
    interactive_mode()