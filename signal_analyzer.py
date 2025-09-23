"""
Signal Analyzer - Анализ торговых сигналов
==========================================

Модуль для получения и анализа торговых сигналов с нескольких таймфреймов.
Основная задача - найти схождения между таймфреймами по направлению и цене.

Author: HEDGER
Version: 1.0
"""

import time
from typing import Dict, List, Set, Optional, Tuple, Mapping
from datetime import datetime, timezone

# Local imports
from api_client import api_client
from config import TIMEFRAMES, MAX_API_RETRIES, RETRY_DELAY_SEC
from utils import logger


class SignalAnalyzer:
    """
    Анализатор торговых сигналов
    
    Основные функции:
    1. Получение сигналов с нескольких таймфреймов
    2. Анализ схождений по направлению и цене
    3. Валидация качества сигналов
    """
    
    def __init__(self, ticker: str):
        """
        Инициализация анализатора для конкретного тикера
        
        Args:
            ticker: Торговая пара (например, "BTCUSDT")
        """
        self.ticker = ticker
        self.timeframes = TIMEFRAMES
        self.price_threshold = 0.005  # 0.5% - максимальная разница в ценах входа

        logger.debug(f"Initialized SignalAnalyzer for {ticker}")

    def fetch_all_signals(self, stop_event=None) -> Dict[str, Optional[Dict]]:
        """
        Получает сигналы для всех таймфреймов с retry логикой
        
        Args:
            stop_event: Event для прерывания процесса
            
        Returns:
            Dict[str, Optional[Dict]]: Словарь сигналов по таймфреймам
            
        Example:
            {
                "15m": {"signal": "LONG", "entry_price": 45000, ...},
                "1h": {"signal": "LONG", "entry_price": 45100, ...},
                "4h": None  # не получен
            }
        """
        signals = {}
        
        for timeframe in self.timeframes:
            # Проверяем на прерывание
            if stop_event and stop_event.is_set():
                logger.info(f"Signal fetching interrupted for {self.ticker}")
                break
                
            logger.info(f"Fetching signal: {self.ticker} {timeframe}")
            
            # Получаем сигнал с retry логикой
            signal = self._fetch_single_signal(timeframe)
            
            if signal:
                signals[timeframe] = signal
                logger.info(f"✅ Signal received: {self.ticker} {timeframe}")
            else:
                logger.warning(f"❌ No signal: {self.ticker} {timeframe}")
        
        logger.info(f"📊 Signals summary for {self.ticker}: {len(signals)}/{len(self.timeframes)} received")
        return signals

    def _fetch_single_signal(self, timeframe: str) -> Optional[Dict]:
        """
        Получает сигнал для одного таймфрейма с retry логикой
        
        Args:
            timeframe: Таймфрейм для запроса
            
        Returns:
            Optional[Dict]: Данные сигнала или None
        """
        for attempt in range(1, MAX_API_RETRIES + 1):
            try:
                logger.debug(f"Attempt {attempt}/{MAX_API_RETRIES}: {self.ticker} {timeframe}")
                
                # Запрос к API
                signal = api_client.get_signal(self.ticker, timeframe)
                
                if signal and self._validate_signal_data(signal):
                    return signal
                else:
                    logger.warning(f"Invalid/empty signal data: {self.ticker} {timeframe}")
                    
            except Exception as e:
                logger.error(f"Error attempt {attempt}: {self.ticker} {timeframe} - {str(e)}")
                
                # Если это не последняя попытка, ждем и повторяем
                if attempt < MAX_API_RETRIES:
                    logger.debug(f"Waiting {RETRY_DELAY_SEC}s before retry...")
                    time.sleep(RETRY_DELAY_SEC)
                    continue
                else:
                    logger.error(f"All {MAX_API_RETRIES} attempts failed for {self.ticker} {timeframe}")
                    
        return None

    def analyze_convergence(self, signals: Mapping[str, Optional[Dict]]) -> Optional[Set[str]]:
        """
        Анализирует схождения между таймфреймами
        
        Ищет таймфреймы с:
        1. Одинаковым направлением сигнала (LONG/SHORT)
        2. Близкими ценами входа (в пределах price_threshold)
        
        Args:
            signals: Словарь сигналов по таймфреймам (могут быть None)
            
        Returns:
            Optional[Set[str]]: Множество совпадающих таймфреймов или None
        """
        # Фильтруем только валидные сигналы
        valid_signals = {tf: signal for tf, signal in signals.items() if signal is not None}
        
        if not valid_signals or len(valid_signals) < 2:
            logger.debug(f"Not enough valid signals for convergence analysis: {len(valid_signals)}")
            return None
            
        matched_timeframes = set()
        timeframe_list = list(valid_signals.keys())
        
        # Сравниваем все пары таймфреймов
        for i, tf1 in enumerate(timeframe_list):
            for tf2 in timeframe_list[i+1:]:
                
                if self._check_convergence(valid_signals[tf1], valid_signals[tf2]):
                    matched_timeframes.update([tf1, tf2])
                    logger.debug(f"Convergence found: {tf1} + {tf2} for {self.ticker}")
        
        if matched_timeframes and len(matched_timeframes) >= 2:
            logger.info(f"🎯 Convergence detected for {self.ticker}: {sorted(matched_timeframes)}")
            return matched_timeframes
        else:
            logger.info(f"No convergence found for {self.ticker}")
            return None

    def _check_convergence(self, signal1: Dict, signal2: Dict) -> bool:
        """
        Проверяет схождение между двумя сигналами
        
        Args:
            signal1, signal2: Данные сигналов для сравнения
            
        Returns:
            bool: True если сигналы схожи
        """
        # Проверяем одинаковое направление
        same_direction = signal1['signal'] == signal2['signal']
        
        # Проверяем близость цен входа
        price_proximity = self._check_price_proximity(
            signal1['entry_price'], 
            signal2['entry_price']
        )
        
        convergent = same_direction and price_proximity
        
        if convergent:
            logger.info(
                f"✅ Convergence detected: {signal1['signal']} | "
                f"Prices: {signal1['entry_price']:.6f} vs {signal2['entry_price']:.6f} | "
                f"Diff: {abs(signal1['entry_price'] - signal2['entry_price']):.6f}"
            )
        else:
            logger.debug(
                f"❌ No convergence: Direction match: {same_direction} | "
                f"Price proximity: {price_proximity} | "
                f"Prices: {signal1['entry_price']:.6f} vs {signal2['entry_price']:.6f}"
            )
            
        return convergent

    def _check_price_proximity(self, price1: float, price2: float) -> bool:
        """
        Проверяет близость двух цен в пределах threshold
        
        Args:
            price1, price2: Цены для сравнения
            
        Returns:
            bool: True если цены достаточно близки
        """
        if not price1 or not price2:
            return False
            
        # Вычисляем относительную разность
        avg_price = (price1 + price2) / 2
        price_diff = abs(price1 - price2)
        relative_diff = price_diff / avg_price
        
        is_close = relative_diff <= self.price_threshold
        
        logger.debug(
            f"Price comparison: {price1:.6f} vs {price2:.6f} | "
            f"Relative diff: {relative_diff:.4f} | "
            f"Threshold: {self.price_threshold} | "
            f"Within range: {is_close}"
        )
            
        return is_close

    def create_signal_data(self, matched_timeframes: Set[str], signals: Mapping[str, Optional[Dict]]) -> Dict:
        """
        Создает консолидированные данные сигнала из совпадающих таймфреймов
        
        Args:
            matched_timeframes: Множество совпадающих таймфреймов
            signals: Все сигналы по таймфреймам (могут содержать None)
            
        Returns:
            Dict: Консолидированный сигнал
        """
        if not matched_timeframes or len(matched_timeframes) < 2:
            raise ValueError("Need at least 2 matching timeframes")
        
        # Фильтруем только валидные сигналы для совпадающих таймфреймов
        valid_matched_signals: Dict[str, Dict] = {}
        for tf in matched_timeframes:
            if tf in signals and signals[tf] is not None:
                valid_matched_signals[tf] = signals[tf]  # type: ignore
        
        if len(valid_matched_signals) < 2:
            raise ValueError("Not enough valid signals in matched timeframes")
            
        logger.info(f"📋 Creating signal data for {self.ticker} with timeframes: {sorted(valid_matched_signals.keys())}")
        
        # Берем первый таймфрейм как базу - теперь гарантированно не None
        first_tf = next(iter(valid_matched_signals.keys()))
        base_signal = valid_matched_signals[first_tf]
        
        # Логируем данные по каждому таймфрейму
        for tf, signal in valid_matched_signals.items():
            logger.info(
                f"  📊 {tf}: {signal['signal']} | "
                f"Entry: {signal['entry_price']:.6f} | "
                f"Stop: {signal['stop_loss']:.6f} | "
                f"Target: {signal['take_profit']:.6f} | "
                f"Confidence: {signal['confidence']:.3f}"
            )
        
        # Вычисляем средние значения
        avg_entry = self._calculate_average([valid_matched_signals[tf]['entry_price'] for tf in valid_matched_signals])
        avg_stop = self._calculate_average([valid_matched_signals[tf]['stop_loss'] for tf in valid_matched_signals])
        avg_take_profit = self._calculate_average([valid_matched_signals[tf]['take_profit'] for tf in valid_matched_signals])
        avg_confidence = self._calculate_average([valid_matched_signals[tf]['confidence'] for tf in valid_matched_signals])
        
        logger.info(
            f"📈 Averaged values for {self.ticker}: "
            f"Entry: {avg_entry:.6f} | Stop: {avg_stop:.6f} | "
            f"Target: {avg_take_profit:.6f} | Confidence: {avg_confidence:.3f}"
        )
        
        # Создаем консолидированный сигнал
        consolidated_signal = {
            'ticker': self.ticker,
            'matched_timeframes': sorted(valid_matched_signals.keys()),
            'timeframes_str': ', '.join(sorted(valid_matched_signals.keys())),
            'signal': base_signal['signal'],
            'current_price': base_signal['current_price'],
            'entry_price': avg_entry,
            'stop_loss': avg_stop,
            'take_profit': avg_take_profit,
            'confidence': avg_confidence,
            'dominance_change_percent': self._calculate_average([
                valid_matched_signals[tf].get('dominance_change_percent', 0) for tf in valid_matched_signals
            ]),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'raw_signals': valid_matched_signals  # Сохраняем только валидные исходные данные
        }
        
        logger.info(
            f"📈 Signal data created for {self.ticker}: "
            f"{consolidated_signal['signal']} at {consolidated_signal['entry_price']:.6f}"
        )
        
        return consolidated_signal

    def _calculate_average(self, values: List[float]) -> float:
        """Вычисляет среднее значение, игнорируя None и 0"""
        valid_values = [v for v in values if v and v != 0]
        return sum(valid_values) / len(valid_values) if valid_values else 0.0

    def _validate_signal_data(self, signal: Dict) -> bool:
        """
        Валидирует полученные данные сигнала
        
        Args:
            signal: Данные сигнала для проверки
            
        Returns:
            bool: True если данные корректны
        """
        required_fields = ['signal', 'current_price', 'entry_price', 'stop_loss', 'take_profit']
        
        # Проверяем наличие обязательных полей
        for field in required_fields:
            if field not in signal or signal[field] is None:
                logger.warning(f"Missing required field: {field}")
                return False
                
        # Проверяем корректность значений
        if signal['signal'] not in ['LONG', 'SHORT']:
            logger.warning(f"Invalid signal direction: {signal['signal']}")
            return False
            
        # Проверяем что цены положительные
        price_fields = ['current_price', 'entry_price', 'stop_loss', 'take_profit']
        for field in price_fields:
            if signal[field] <= 0:
                logger.warning(f"Invalid price value for {field}: {signal[field]}")
                return False
                
        return True

    def analyze_ticker(self, stop_event=None) -> Optional[Dict]:
        """
        Полный анализ тикера: получение сигналов + поиск схождений
        
        Args:
            stop_event: Event для прерывания процесса
            
        Returns:
            Optional[Dict]: Консолидированный сигнал или None
        """
        logger.info(f"🔍 Starting analysis for {self.ticker}")
        
        try:
            # 1. Получаем сигналы по всем таймфреймам
            signals = self.fetch_all_signals(stop_event)
            
            if not signals:
                logger.info(f"No signals received for {self.ticker}")
                return None
                
            # 2. Ищем схождения
            matched_timeframes = self.analyze_convergence(signals)
            
            if not matched_timeframes:
                logger.info(f"No convergence found for {self.ticker}")
                return None
                
            # 3. Создаем консолидированный сигнал
            signal_data = self.create_signal_data(matched_timeframes, signals)
            
            logger.info(f"✅ Analysis completed successfully for {self.ticker}")
            return signal_data
            
        except Exception as e:
            logger.error(f"Analysis failed for {self.ticker}: {str(e)}", exc_info=True)
            return None


# Utility function for external use
def analyze_ticker_signals(ticker: str, stop_event=None) -> Optional[Dict]:
    """
    Convenience function для анализа одного тикера
    
    Args:
        ticker: Торговая пара для анализа
        stop_event: Event для прерывания
        
    Returns:
        Optional[Dict]: Результат анализа или None
    """
    analyzer = SignalAnalyzer(ticker)
    return analyzer.analyze_ticker(stop_event)


if __name__ == "__main__":
    '''
    Пример использования - анализ сигнала для LTCUSDT
    В реальном приложении этот код должен быть в отдельном файле или функции
    '''
    import logging
    logging.basicConfig(level=logging.INFO)
    
    test_ticker = "NKNUSDT"
    result = analyze_ticker_signals(test_ticker)
    
    if result:
        print(f"✅ Signal found for {test_ticker}:")
        print(f"Direction: {result['signal']}")
        print(f"Entry: {result['entry_price']}")
        print(f"Timeframes: {result['timeframes_str']}")
    else:
        print(f"❌ No signal for {test_ticker}")