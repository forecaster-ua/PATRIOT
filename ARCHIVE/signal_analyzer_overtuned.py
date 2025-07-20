"""
Signal Analyzer - Анализ торговых сигналов (Fixed Version)
=========================================================

Модуль для получения и анализа торговых сигналов с нескольких таймфреймов.
Основная задача - найти схождения между таймфреймами по направлению и цене.

ИСПРАВЛЕНИЯ v2.0:
- Добавлены таймауты для всех операций
- Защита от зацикливания retry логики
- Ограничение времени обработки одного тикера
- Улучшенная обработка ошибок и логирование
- Принудительная очистка ресурсов

Author: HEDGER
Version: 2.0 - Fixed
"""

import time
import threading
from typing import Dict, List, Set, Optional, Tuple, Mapping
from datetime import datetime, timezone
from contextlib import contextmanager

# Local imports
from api_client import api_client
from config import TIMEFRAMES, MAX_API_RETRIES, RETRY_DELAY_SEC
from utils import logger

# Новые константы для контроля времени
MAX_TICKER_PROCESSING_TIME = 120  # Максимум 2 минуты на тикер
MAX_TIMEFRAME_PROCESSING_TIME = 45  # Максимум 45 секунд на таймфрейм
API_TIMEOUT_SEC = 30  # Таймаут для одного API запроса
MIN_RETRY_DELAY = 1  # Минимальная задержка между retry
MAX_RETRY_DELAY = 5  # Максимальная задержка между retry


class TimeoutError(Exception):
    """Исключение для превышения времени обработки"""
    pass


class ProcessingInterrupted(Exception):
    """Исключение для прерывания обработки"""
    pass


class TimeoutManager:
    """Кроссплатформенный менеджер таймаутов"""
    
    def __init__(self, seconds: int, operation_name: str):
        self.seconds = seconds
        self.operation_name = operation_name
        self.timer = None
        self.timed_out = False
        
    def _timeout_handler(self):
        """Обработчик таймаута"""
        self.timed_out = True
        logger.warning(f"⏰ Timeout triggered for {self.operation_name} after {self.seconds}s")
        
    def start(self):
        """Запуск таймера"""
        self.timer = threading.Timer(self.seconds, self._timeout_handler)
        self.timer.start()
        
    def stop(self):
        """Остановка таймера"""
        if self.timer:
            self.timer.cancel()
            
    def check_timeout(self):
        """Проверка таймаута и выброс исключения если необходимо"""
        if self.timed_out:
            raise TimeoutError(f"Timeout after {self.seconds}s during {self.operation_name}")


@contextmanager
def timeout_context(seconds: int, operation_name: str):
    """
    Кроссплатформенный контекстный менеджер для установки таймаута
    
    Args:
        seconds: Количество секунд для таймаута
        operation_name: Название операции для логирования
    """
    timeout_manager = TimeoutManager(seconds, operation_name)
    timeout_manager.start()
    
    try:
        yield timeout_manager
    finally:
        timeout_manager.stop()


class SignalAnalyzer:
    """
    Анализатор торговых сигналов с защитой от таймаутов
    
    Основные функции:
    1. Получение сигналов с нескольких таймфреймов с таймаутами
    2. Анализ схождений по направлению и цене
    3. Валидация качества сигналов
    4. Защита от зависания и зацикливания
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
        
        # Контроль времени
        self.start_time = None
        self.processing_interrupted = False
        
        logger.debug(f"Initialized SignalAnalyzer for {ticker}")

    def fetch_all_signals(self, stop_event=None) -> Dict[str, Optional[Dict]]:
        """
        Получает сигналы для всех таймфреймов с контролем времени
        
        Args:
            stop_event: Event для прерывания процесса
            
        Returns:
            Dict[str, Optional[Dict]]: Словарь сигналов по таймфреймам
        """
        logger.info(f"🔍 Starting signal fetch for {self.ticker}")
        self.start_time = time.time()
        signals = {}
        
        try:
            with timeout_context(MAX_TICKER_PROCESSING_TIME, f"fetching signals for {self.ticker}") as timeout_mgr:
                for i, timeframe in enumerate(self.timeframes):
                    # Проверяем таймаут
                    timeout_mgr.check_timeout()
                    
                    # Проверяем прерывание
                    if stop_event and stop_event.is_set():
                        logger.info(f"🛑 Signal fetching interrupted for {self.ticker}")
                        self.processing_interrupted = True
                        break
                    
                    # Проверяем общее время обработки
                    elapsed = time.time() - self.start_time
                    if elapsed > MAX_TICKER_PROCESSING_TIME:
                        logger.warning(f"⏰ Ticker processing timeout for {self.ticker} after {elapsed:.1f}s")
                        break
                    
                    logger.info(f"📡 Fetching signal: {self.ticker} {timeframe} ({i+1}/{len(self.timeframes)})")
                    
                    # Получаем сигнал с таймаутом
                    signal = self._fetch_single_signal_with_timeout(timeframe, stop_event)
                    
                    if signal:
                        signals[timeframe] = signal
                        logger.info(f"✅ Signal received: {self.ticker} {timeframe}")
                    else:
                        logger.warning(f"❌ No signal: {self.ticker} {timeframe}")
                        signals[timeframe] = None
                    
                    # Небольшая пауза между запросами к API
                    if not stop_event or not stop_event.is_set():
                        time.sleep(0.5)
                        
        except TimeoutError as e:
            logger.error(f"⏰ Timeout during signal fetching for {self.ticker}: {e}")
            self.processing_interrupted = True
        except Exception as e:
            logger.error(f"❌ Unexpected error during signal fetching for {self.ticker}: {e}")
            self.processing_interrupted = True
        
        finally:
            total_elapsed = time.time() - self.start_time if self.start_time else 0
            logger.info(
                f"📊 Signals summary for {self.ticker}: "
                f"{len([s for s in signals.values() if s])}/{len(self.timeframes)} received "
                f"in {total_elapsed:.1f}s"
            )
        
        return signals

    def _fetch_single_signal_with_timeout(self, timeframe: str, stop_event=None) -> Optional[Dict]:
        """
        Получает сигнал для одного таймфрейма с полным контролем таймаутов
        
        Args:
            timeframe: Таймфрейм для запроса
            stop_event: Event для прерывания
            
        Returns:
            Optional[Dict]: Данные сигнала или None
        """
        try:
            with timeout_context(MAX_TIMEFRAME_PROCESSING_TIME, f"{self.ticker} {timeframe}") as timeout_mgr:
                return self._fetch_single_signal(timeframe, stop_event, timeout_mgr)
        except TimeoutError as e:
            logger.error(f"⏰ Timeframe timeout: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error in timeframe processing: {e}")
            return None

    def _fetch_single_signal(self, timeframe: str, stop_event=None, timeout_mgr=None) -> Optional[Dict]:
        """
        Получает сигнал для одного таймфрейма с улучшенной retry логикой
        
        Args:
            timeframe: Таймфрейм для запроса
            stop_event: Event для прерывания
            timeout_mgr: Менеджер таймаутов
            
        Returns:
            Optional[Dict]: Данные сигнала или None
        """
        retry_delay = MIN_RETRY_DELAY
        
        for attempt in range(1, MAX_API_RETRIES + 1):
            # Проверяем таймаут
            if timeout_mgr:
                timeout_mgr.check_timeout()
                
            # Проверяем прерывание на каждой попытке
            if stop_event and stop_event.is_set():
                logger.info(f"🛑 Retry interrupted for {self.ticker} {timeframe}")
                break
                
            try:
                logger.debug(f"🔄 Attempt {attempt}/{MAX_API_RETRIES}: {self.ticker} {timeframe}")
                
                # Запрос к API с таймаутом
                signal = self._api_call_with_timeout(timeframe, timeout_mgr)
                
                if signal and self._validate_signal_data(signal):
                    logger.debug(f"✅ Valid signal received on attempt {attempt}")
                    return signal
                else:
                    logger.warning(f"⚠️ Invalid/empty signal data: {self.ticker} {timeframe} (attempt {attempt})")
                    
            except TimeoutError as e:
                logger.error(f"⏰ API timeout on attempt {attempt}: {self.ticker} {timeframe}")
            except Exception as e:
                logger.error(f"❌ API error attempt {attempt}: {self.ticker} {timeframe} - {str(e)}")
                
            # Если это не последняя попытка, ждем с прогрессивной задержкой
            if attempt < MAX_API_RETRIES:
                if stop_event and stop_event.is_set():
                    break
                    
                logger.debug(f"⏳ Waiting {retry_delay}s before retry...")
                time.sleep(retry_delay)
                
                # Увеличиваем задержку для следующей попытки (exponential backoff)
                retry_delay = min(retry_delay * 1.5, MAX_RETRY_DELAY)
            else:
                logger.error(f"❌ All {MAX_API_RETRIES} attempts failed for {self.ticker} {timeframe}")
                    
        return None

    def _api_call_with_timeout(self, timeframe: str, timeout_mgr=None) -> Optional[Dict]:
        """
        Вызов API с принудительным таймаутом
        
        Args:
            timeframe: Таймфрейм для запроса
            timeout_mgr: Менеджер таймаутов
            
        Returns:
            Optional[Dict]: Результат API или None
        """
        try:
            with timeout_context(API_TIMEOUT_SEC, f"API call {self.ticker} {timeframe}") as api_timeout_mgr:
                start_time = time.time()
                
                # Проверяем общий таймаут
                if timeout_mgr:
                    timeout_mgr.check_timeout()
                    
                result = api_client.get_signal(self.ticker, timeframe)
                
                elapsed = time.time() - start_time
                logger.debug(f"📡 API call completed in {elapsed:.2f}s for {self.ticker} {timeframe}")
                
                return result
                
        except TimeoutError:
            logger.error(f"⏰ API call timeout for {self.ticker} {timeframe}")
            raise
        except Exception as e:
            logger.error(f"❌ API call error for {self.ticker} {timeframe}: {e}")
            raise

    def analyze_convergence(self, signals: Mapping[str, Optional[Dict]]) -> Optional[Set[str]]:
        """
        Анализирует схождения между таймфреймами с контролем времени
        
        Args:
            signals: Словарь сигналов по таймфреймам
            
        Returns:
            Optional[Set[str]]: Множество совпадающих таймфреймов или None
        """
        try:
            with timeout_context(10, f"convergence analysis for {self.ticker}") as timeout_mgr:
                return self._analyze_convergence_internal(signals, timeout_mgr)
        except TimeoutError as e:
            logger.error(f"⏰ Convergence analysis timeout: {e}")
            return None

    def _analyze_convergence_internal(self, signals: Mapping[str, Optional[Dict]], timeout_mgr=None) -> Optional[Set[str]]:
        """Внутренний метод анализа схождений"""
        # Проверяем таймаут
        if timeout_mgr:
            timeout_mgr.check_timeout()
            
        # Фильтруем только валидные сигналы
        valid_signals = {tf: signal for tf, signal in signals.items() if signal is not None}
        
        if not valid_signals or len(valid_signals) < 2:
            logger.debug(f"📊 Not enough valid signals for convergence analysis: {len(valid_signals)}")
            return None
            
        matched_timeframes = set()
        timeframe_list = list(valid_signals.keys())
        
        # Сравниваем все пары таймфреймов
        for i, tf1 in enumerate(timeframe_list):
            for tf2 in timeframe_list[i+1:]:
                # Проверяем таймаут
                if timeout_mgr:
                    timeout_mgr.check_timeout()
                
                if self._check_convergence(valid_signals[tf1], valid_signals[tf2]):
                    matched_timeframes.update([tf1, tf2])
                    logger.debug(f"🎯 Convergence found: {tf1} + {tf2} for {self.ticker}")
        
        if matched_timeframes and len(matched_timeframes) >= 2:
            logger.info(f"🎯 Convergence detected for {self.ticker}: {sorted(matched_timeframes)}")
            return matched_timeframes
        else:
            logger.info(f"📊 No convergence found for {self.ticker}")
            return None

    def _check_convergence(self, signal1: Dict, signal2: Dict) -> bool:
        """
        Проверяет схождение между двумя сигналами
        
        Args:
            signal1, signal2: Данные сигналов для сравнения
            
        Returns:
            bool: True если сигналы схожи
        """
        try:
            # Проверяем одинаковое направление
            same_direction = signal1['signal'] == signal2['signal']
            
            # Проверяем близость цен входа
            price_proximity = self._check_price_proximity(
                signal1['entry_price'], 
                signal2['entry_price']
            )
            
            convergent = same_direction and price_proximity
            
            if convergent:
                logger.debug(
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
            
        except Exception as e:
            logger.error(f"❌ Error checking convergence: {e}")
            return False

    def _check_price_proximity(self, price1: float, price2: float) -> bool:
        """
        Проверяет близость двух цен в пределах threshold
        
        Args:
            price1, price2: Цены для сравнения
            
        Returns:
            bool: True если цены достаточно близки
        """
        try:
            if not price1 or not price2 or price1 <= 0 or price2 <= 0:
                return False
                
            # Вычисляем относительную разность
            avg_price = (price1 + price2) / 2
            price_diff = abs(price1 - price2)
            relative_diff = price_diff / avg_price
            
            is_close = relative_diff <= self.price_threshold
            
            logger.debug(
                f"💰 Price comparison: {price1:.6f} vs {price2:.6f} | "
                f"Relative diff: {relative_diff:.4f} | "
                f"Threshold: {self.price_threshold} | "
                f"Within range: {is_close}"
            )
                
            return is_close
            
        except Exception as e:
            logger.error(f"❌ Error in price proximity check: {e}")
            return False

    def create_signal_data(self, matched_timeframes: Set[str], signals: Mapping[str, Optional[Dict]]) -> Optional[Dict]:
        """
        Создает консолидированные данные сигнала с контролем времени
        
        Args:
            matched_timeframes: Множество совпадающих таймфреймов
            signals: Все сигналы по таймфреймам
            
        Returns:
            Optional[Dict]: Консолидированный сигнал или None
        """
        try:
            with timeout_context(15, f"signal data creation for {self.ticker}") as timeout_mgr:
                return self._create_signal_data_internal(matched_timeframes, signals, timeout_mgr)
        except TimeoutError as e:
            logger.error(f"⏰ Signal data creation timeout: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error creating signal data: {e}")
            return None

    def _create_signal_data_internal(self, matched_timeframes: Set[str], signals: Mapping[str, Optional[Dict]], timeout_mgr=None) -> Dict:
        """Внутренний метод создания данных сигнала"""
        # Проверяем таймаут
        if timeout_mgr:
            timeout_mgr.check_timeout()
            
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
        
        # Проверяем таймаут
        if timeout_mgr:
            timeout_mgr.check_timeout()
        
        # Берем первый таймфрейм как базу
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
        
        # Вычисляем средние значения безопасно
        avg_entry = self._safe_calculate_average([valid_matched_signals[tf]['entry_price'] for tf in valid_matched_signals])
        avg_stop = self._safe_calculate_average([valid_matched_signals[tf]['stop_loss'] for tf in valid_matched_signals])
        avg_take_profit = self._safe_calculate_average([valid_matched_signals[tf]['take_profit'] for tf in valid_matched_signals])
        avg_confidence = self._safe_calculate_average([valid_matched_signals[tf]['confidence'] for tf in valid_matched_signals])
        
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
            'dominance_change_percent': self._safe_calculate_average([
                valid_matched_signals[tf].get('dominance_change_percent', 0) for tf in valid_matched_signals
            ]),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'raw_signals': valid_matched_signals,
            'processing_time': time.time() - self.start_time if self.start_time else 0,
            'was_interrupted': self.processing_interrupted
        }
        
        logger.info(
            f"📈 Signal data created for {self.ticker}: "
            f"{consolidated_signal['signal']} at {consolidated_signal['entry_price']:.6f} "
            f"(processed in {consolidated_signal['processing_time']:.1f}s)"
        )
        
        return consolidated_signal

    def _safe_calculate_average(self, values: List[float]) -> float:
        """Безопасно вычисляет среднее значение"""
        try:
            valid_values = [v for v in values if v and v != 0 and not (isinstance(v, float) and (v != v))]  # исключаем NaN
            return sum(valid_values) / len(valid_values) if valid_values else 0.0
        except Exception as e:
            logger.error(f"❌ Error calculating average: {e}")
            return 0.0

    def _validate_signal_data(self, signal: Dict) -> bool:
        """
        Валидирует полученные данные сигнала с улучшенными проверками
        
        Args:
            signal: Данные сигнала для проверки
            
        Returns:
            bool: True если данные корректны
        """
        try:
            if not signal or not isinstance(signal, dict):
                logger.warning("❌ Signal is not a valid dictionary")
                return False
            
            required_fields = ['signal', 'current_price', 'entry_price', 'stop_loss', 'take_profit']
            
            # Проверяем наличие обязательных полей
            for field in required_fields:
                if field not in signal:
                    logger.warning(f"❌ Missing required field: {field}")
                    return False
                    
                if signal[field] is None:
                    logger.warning(f"❌ Field {field} is None")
                    return False
                    
            # Проверяем корректность значений
            if signal['signal'] not in ['LONG', 'SHORT']:
                logger.warning(f"❌ Invalid signal direction: {signal['signal']}")
                return False
                
            # Проверяем что цены положительные и не NaN
            price_fields = ['current_price', 'entry_price', 'stop_loss', 'take_profit']
            for field in price_fields:
                try:
                    value = float(signal[field])
                    if value <= 0 or value != value:  # проверка на NaN
                        logger.warning(f"❌ Invalid price value for {field}: {value}")
                        return False
                except (ValueError, TypeError):
                    logger.warning(f"❌ Price field {field} is not a valid number: {signal[field]}")
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validating signal data: {e}")
            return False

    def analyze_ticker(self, stop_event=None) -> Optional[Dict]:
        """
        Полный анализ тикера с полным контролем времени и ресурсов
        
        Args:
            stop_event: Event для прерывания процесса
            
        Returns:
            Optional[Dict]: Консолидированный сигнал или None
        """
        logger.info(f"🔍 Starting comprehensive analysis for {self.ticker}")
        analysis_start = time.time()
        
        try:
            with timeout_context(MAX_TICKER_PROCESSING_TIME, f"full analysis of {self.ticker}"):
                # 1. Получаем сигналы по всем таймфреймам
                signals = self.fetch_all_signals(stop_event)
                
                if not signals or self.processing_interrupted:
                    logger.info(f"❌ No signals received or processing interrupted for {self.ticker}")
                    return None
                    
                # 2. Ищем схождения
                matched_timeframes = self.analyze_convergence(signals)
                
                if not matched_timeframes:
                    logger.info(f"📊 No convergence found for {self.ticker}")
                    return None
                    
                # 3. Создаем консолидированный сигнал
                signal_data = self.create_signal_data(matched_timeframes, signals)
                
                if signal_data:
                    analysis_time = time.time() - analysis_start
                    logger.info(f"✅ Analysis completed successfully for {self.ticker} in {analysis_time:.1f}s")
                    return signal_data
                else:
                    logger.error(f"❌ Failed to create signal data for {self.ticker}")
                    return None
                
        except TimeoutError as e:
            logger.error(f"⏰ Analysis timeout for {self.ticker}: {e}")
            return None
        except ProcessingInterrupted:
            logger.info(f"🛑 Analysis interrupted for {self.ticker}")
            return None
        except Exception as e:
            logger.error(f"❌ Analysis failed for {self.ticker}: {str(e)}", exc_info=True)
            return None
        finally:
            # Принудительная очистка ресурсов
            self._cleanup_resources()

    def _cleanup_resources(self):
        """Очистка ресурсов после завершения анализа"""
        try:
            # Сбрасываем состояние
            self.processing_interrupted = False
            self.start_time = None
            
            # Принудительная сборка мусора для этого анализатора
            import gc
            gc.collect()
            
        except Exception as e:
            logger.debug(f"⚠️ Warning during resource cleanup: {e}")

    def __del__(self):
        """Деструктор для окончательной очистки"""
        try:
            self._cleanup_resources()
        except:
            pass


# Utility function for external use
def analyze_ticker_signals(ticker: str, stop_event=None) -> Optional[Dict]:
    """
    Convenience function для анализа одного тикера с таймаутом
    
    Args:
        ticker: Торговая пара для анализа
        stop_event: Event для прерывания
        
    Returns:
        Optional[Dict]: Результат анализа или None
    """
    analyzer = None
    try:
        analyzer = SignalAnalyzer(ticker)
        return analyzer.analyze_ticker(stop_event)
    except Exception as e:
        logger.error(f"❌ Error in analyze_ticker_signals for {ticker}: {e}")
        return None
    finally:
        # Принудительная очистка
        if analyzer:
            try:
                analyzer._cleanup_resources()
            except:
                pass
        del analyzer


if __name__ == "__main__":
    '''
    Пример использования с таймаутами - анализ сигнала для LTCUSDT
    '''
    import logging
    logging.basicConfig(level=logging.INFO)
    
    test_ticker = "LTCUSDT"
    logger.info(f"🧪 Testing signal analysis for {test_ticker}")
    
    result = analyze_ticker_signals(test_ticker)
    
    if result:
        print(f"✅ Signal found for {test_ticker}:")
        print(f"Direction: {result['signal']}")
        print(f"Entry: {result['entry_price']}")
        print(f"Timeframes: {result['timeframes_str']}")
        print(f"Processing time: {result.get('processing_time', 0):.1f}s")
        print(f"Was interrupted: {result.get('was_interrupted', False)}")
    else:
        print(f"❌ No signal for {test_ticker}")