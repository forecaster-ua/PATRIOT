import requests
from statistics import mean
from telegram_bot import telegram_bot  # Импортируем готовый бот
from api_client import api_client  # Импортируем API клиент
from typing import Dict, List, Set, Optional

class SignalProcessor:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.timeframes = ["15m", "1h", "4h"]
        self.price_threshold = 0.005  # 0.05%

    def get_signals(self) -> Dict[str, Optional[Dict]]:
        """Получаем сигналы для всех таймфреймов"""
        return {
            tf: api_client.get_signal(self.ticker, tf)
            for tf in self.timeframes
        }

    @staticmethod
    def check_price_proximity(price1: float, price2: float, threshold: float) -> bool:
        """Проверяет близость цен в пределах threshold"""
        if None in (price1, price2):
            return False
        return abs(price1 - price2) / ((price1 + price2)/2) <= threshold

    def find_matching_timeframes(self, signals: Dict[str, Dict]) -> Set[str]:
        """Находит совпадающие таймфреймы по направлению и цене"""
        matched_tfs = set()
        
        # Проверяем все возможные пары ТФ
        for i, tf1 in enumerate(self.timeframes):
            for tf2 in self.timeframes[i+1:]:
                if (signals[tf1]['signal'] == signals[tf2]['signal'] and 
                    self.check_price_proximity(
                        signals[tf1]['entry_price'],
                        signals[tf2]['entry_price'],
                        self.price_threshold
                    )):
                    matched_tfs.update([tf1, tf2])
        
        return matched_tfs

    def generate_execution_signal(self, matched_tfs: Set[str], signals: Dict) -> Optional[Dict]:
        """Генерирует сигнал для исполнения"""
        if len(matched_tfs) < 2:
            return None

        direction = signals[next(iter(matched_tfs))]['signal']
        entry_prices = [signals[tf]['entry_price'] for tf in matched_tfs]
        avg_price = mean(entry_prices)

        signal_data = {
            'pair': self.ticker,
            'timeframe': ', '.join(matched_tfs),
            'signal': direction,
            'current_price': signals[next(iter(matched_tfs))]['current_price'],
            'entry_price': round(avg_price, 6),
            'stop_loss': round(mean([signals[tf]['stop_loss'] for tf in matched_tfs]), 6),  
            'take_profit': round(mean([signals[tf]['take_profit'] for tf in matched_tfs]), 6),  
            'confidence': mean([signals[tf]['confidence'] for tf in matched_tfs]) / 100,  
            'dominance_change_percent': mean(
                [signals[tf].get('dominance_change_percent', 0) 
                for tf in matched_tfs]
            ),
            'timestamp': signals[next(iter(matched_tfs))]['timestamp']
        }

        return signal_data

    def process(self):
        """Основной метод обработки сигналов"""
        signals = self.get_signals()
        
        if not all(signals.values()):
            print("Не удалось получить сигналы для всех таймфреймов")
            return

        # Filter out None values before passing to find_matching_timeframes
        valid_signals = {tf: signal for tf, signal in signals.items() if signal is not None}
        matched_tfs = self.find_matching_timeframes(valid_signals)
        
        if not matched_tfs:
            print("Нет совпадающих сигналов по направлению и цене")
            return

        execution_signal = self.generate_execution_signal(matched_tfs, signals)
        
        if execution_signal:
            # Отправляем в Telegram через готового бота
            telegram_bot.send_signal(execution_signal)
            
            # Формируем ордер для биржи
            order = {
                'symbol': self.ticker,
                'side': 'BUY' if execution_signal['signal'] == 'LONG' else 'SELL',
                'price': execution_signal['entry_price'],
                'quantity': self.calculate_quantity(execution_signal['entry_price']),
                'timeframes': list(matched_tfs)
            }
            
            print(f"🔔 Сгенерирован сигнал на исполнение для {self.ticker}")
            print(f"Направление: {execution_signal['signal']}")
            print(f"Совпадающие ТФ: {', '.join(matched_tfs)}")
            print(f"Средняя цена входа: {execution_signal['entry_price']:.6f}")
            print(f"Stop Loss: {execution_signal['stop_loss']:.6f}")
            print(f"Take Profit: {execution_signal['take_profit']:.6f}")
            
            # Здесь можно добавить вызов функции для исполнения ордера
            # execute_order(order)

    def calculate_quantity(self, price: float) -> float:
        """Расчет объема позиции (заглушка)"""
        # Реализуйте вашу логику расчета
        return 0.01  # Пример фиксированного объема


# Пример использования
if __name__ == "__main__":
    processor = SignalProcessor("BCHUSDT")
    processor.process()