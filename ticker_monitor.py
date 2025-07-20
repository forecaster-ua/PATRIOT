"""
Ticker Monitor - Оркестратор торговой системы (Production Ready)
================================================================

Полностью совместимый с архитектурой проекта PATRIOT:
- Использует существующие модули: signal_analyzer, order_generator
- Загружает тикеры из COIN_SYMBOLS в tickers.txt
- Интегрируется с utils.logger и config
- Graceful shutdown и система recovery

Author: HEDGER
Version: 4.0 - Production Ready
"""

import time
import schedule
import signal
import sys
import threading
import traceback
from datetime import datetime
from queue import Queue, Empty
from pathlib import Path
from typing import List, Optional, Dict, Any, Set
import gc
from config import (
    TIMEFRAMES, TICKER_DELAY, MAX_WORKERS, PROCESSING_TIMEOUT,
    SCHEDULE_INTERVAL_MINUTES, SCHEDULE_AT_SECOND, 
    DEFAULT_TICKERS_FILE, BATCH_LOG_FREQUENCY
)

# Импорты существующих модулей проекта
import logging

# Сначала пытаемся импортировать logger из utils
try:
    from signal_analyzer import SignalAnalyzer
    from order_executor import execute_trading_signal
    from utils import logger
    from config import TIMEFRAMES
    logger.info("✅ Successfully imported project modules")
except ImportError as e:
    # Если импорт не удался, создаем базовый logger
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s'
        )
    
    logger.error(f"❌ Import error: {e}")
    logger.warning("⚠️ Running in standalone mode with mock implementations")
    
    # Mock реализации для автономной работы
    import random
    
    class MockSignalAnalyzer:
        def __init__(self, ticker: str):
            self.ticker = ticker
            
        def analyze_ticker(self, stop_event) -> Optional[Dict]:
            # Имитация анализа с 30% вероятностью найти сигнал
            if random.random() < 0.3:
                return {
                    'ticker': self.ticker,
                    'signal': random.choice(['LONG', 'SHORT']),
                    'timeframes': ['1H', '4H'],
                    'entry_price': random.uniform(0.1, 1000),
                    'confidence': random.uniform(0.7, 1.0)
                }
            return None
    
    def process_trading_signal(signal_data: Dict) -> bool:
        logger.info(f"📱 MOCK: Processing signal for {signal_data['ticker']}")
        return True
    
    execute_trading_signal = process_trading_signal
    SignalAnalyzer = MockSignalAnalyzer
    TIMEFRAMES = ['1H', '4H', '1D']


class TickerLoader:
    """
    Загрузчик тикеров из файла tickers.txt
    Поддерживает формат COIN_SYMBOLS = [...]
    """
    
    def __init__(self, file_path: str = 'tickers.txt'):
        self.file_path = Path(file_path)
        
    def load_tickers(self) -> List[str]:
        """Загружает тикеры из файла"""
        try:
            if not self.file_path.exists():
                logger.error(f"❌ Ticker file not found: {self.file_path}")
                return self._get_fallback_tickers()
            
            content = self.file_path.read_text(encoding='utf-8').strip()
            if not content:
                logger.warning("⚠️ Ticker file is empty")
                return self._get_fallback_tickers()
            
            logger.debug(f"📄 File content preview: {content[:200]}...")
            
            # Пытаемся выполнить Python код из файла
            return self._extract_coin_symbols(content)
            
        except Exception as e:
            logger.error(f"❌ Error loading tickers: {e}")
            return self._get_fallback_tickers()
    
    def _extract_coin_symbols(self, content: str) -> List[str]:
        """Извлекает COIN_SYMBOLS из содержимого файла"""
        try:
            # Безопасное выполнение кода
            local_vars = {}
            exec(content, {"__builtins__": {}}, local_vars)
            
            if 'COIN_SYMBOLS' in local_vars:
                tickers = local_vars['COIN_SYMBOLS']
                logger.info(f"📋 Loaded {len(tickers)} tickers from COIN_SYMBOLS")
                return self._validate_tickers(tickers)
            else:
                logger.warning("⚠️ COIN_SYMBOLS not found, trying regex extraction")
                return self._extract_with_regex(content)
                
        except Exception as e:
            logger.error(f"❌ Failed to execute file content: {e}")
            return self._extract_with_regex(content)
    
    def _extract_with_regex(self, content: str) -> List[str]:
        """Извлекает тикеры с помощью регулярных выражений"""
        import re
        import ast
        
        try:
            # Ищем COIN_SYMBOLS = [...]
            pattern = r'COIN_SYMBOLS\s*=\s*\[(.*?)\]'
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                list_content = '[' + match.group(1) + ']'
                tickers = ast.literal_eval(list_content)
                logger.info(f"📋 Extracted {len(tickers)} tickers via regex")
                return self._validate_tickers(tickers)
            else:
                logger.error("❌ Could not find COIN_SYMBOLS pattern")
                return self._get_fallback_tickers()
                
        except Exception as e:
            logger.error(f"❌ Regex extraction failed: {e}")
            return self._get_fallback_tickers()
    
    def _validate_tickers(self, tickers: List) -> List[str]:
        """Валидирует список тикеров"""
        valid_tickers = []
        
        for ticker in tickers:
            if isinstance(ticker, str) and ticker.strip():
                clean_ticker = ticker.strip().upper()
                
                # Проверяем формат криптовалютной пары
                if len(clean_ticker) >= 6 and clean_ticker.endswith('USDT'):
                    valid_tickers.append(clean_ticker)
                    logger.debug(f"✅ Valid ticker: {clean_ticker}")
                else:
                    logger.debug(f"⚠️ Skipping ticker: {ticker}")
            else:
                logger.warning(f"⚠️ Invalid ticker format: {ticker}")
        
        if not valid_tickers:
            logger.error("❌ No valid tickers found")
            return self._get_fallback_tickers()
        
        logger.info(f"📊 Validated {len(valid_tickers)} tickers")
        return valid_tickers
    
    def _get_fallback_tickers(self) -> List[str]:
        """Возвращает базовый набор тикеров для работы"""
        fallback = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
        logger.info(f"🔄 Using fallback tickers: {fallback}")
        return fallback


class WorkerStats:
    """Thread-safe статистика для мониторинга работы"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self.processed = 0
        self.signals_found = 0
        self.orders_created = 0
        self.errors = 0
        self.start_time: Optional[datetime] = None
        self.reset()
    
    def reset(self):
        """Сброс статистики"""
        with self._lock:
            self.processed = 0
            self.signals_found = 0
            self.orders_created = 0
            self.errors = 0
            self.start_time = None
    
    def update(self, processed: int = 0, signals: int = 0, orders: int = 0, errors: int = 0):
        """Обновление статистики"""
        with self._lock:
            self.processed += processed
            self.signals_found += signals
            self.orders_created += orders
            self.errors += errors
    
    def get_summary(self) -> Dict[str, Any]:
        """Получение итоговой статистики"""
        with self._lock:
            duration = 0
            if self.start_time:
                duration = (datetime.now() - self.start_time).total_seconds()
            
            success_rate = (self.signals_found / self.processed * 100) if self.processed > 0 else 0
            conversion_rate = (self.orders_created / self.signals_found * 100) if self.signals_found > 0 else 0
            
            return {
                'processed': self.processed,
                'signals_found': self.signals_found,
                'orders_created': self.orders_created,
                'errors': self.errors,
                'duration_seconds': round(duration, 1),
                'success_rate': round(success_rate, 1),
                'conversion_rate': round(conversion_rate, 1)
            }


class TickerMonitor:
    """
    Главный оркестратор торговой системы
    Координирует работу всех компонентов согласно архитектуре проекта
    """
    
    def __init__(self, tickers_file: str = DEFAULT_TICKERS_FILE, max_workers: int = MAX_WORKERS, ticker_delay: float = TICKER_DELAY):
        self.tickers_file = tickers_file
        self.max_workers = max_workers
        self.ticker_delay = ticker_delay  # Задержка между тикерами
        
        # Управление потоками и очередями
        self.ticker_queue: Queue[Optional[str]] = Queue()
        self.stop_event = threading.Event()
        self.worker_threads: List[threading.Thread] = []
        
        # Статистика и мониторинг
        self.stats = WorkerStats()
        self.current_batch_start: Optional[datetime] = None
        
        # Инициализация компонентов
        self.ticker_loader = TickerLoader(tickers_file)
        self.tickers = self.ticker_loader.load_tickers()
        
        # Настройка обработчиков сигналов
        self._setup_signal_handlers()
        
        logger.info(f"🎼 TickerMonitor initialized: {len(self.tickers)} tickers, {self.max_workers} workers, {self.ticker_delay}s delay")
    
    def _setup_signal_handlers(self) -> None:
        """Настройка graceful shutdown"""
        def signal_handler(signum: int, frame: Any) -> None:
            signal_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
            logger.info(f"🛑 Received {signal_name} - initiating graceful shutdown...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def shutdown(self) -> None:
        """Graceful shutdown всей системы"""
        logger.info("� Starting graceful shutdown...")
        self.stop_event.set()
        
        # Ждем завершения всех worker'ов
        active_workers = [t for t in self.worker_threads if t.is_alive()]
        if active_workers:
            logger.info(f"⏳ Waiting for {len(active_workers)} workers to complete...")
            for thread in active_workers:
                thread.join(timeout=10)
                if thread.is_alive():
                    logger.warning(f"⚠️ Thread {thread.name} did not terminate gracefully")
        
        # Очищаем очередь
        while not self.ticker_queue.empty():
            try:
                self.ticker_queue.get_nowait()
            except Empty:
                break
        
        logger.info("✅ Graceful shutdown completed")
        sys.exit(0)
    
    def _fill_queue(self) -> None:
        """Заполняет очередь тикерами для обработки"""
        if self.stop_event.is_set():
            return
        
        for ticker in self.tickers:
            if self.stop_event.is_set():
                break
            self.ticker_queue.put(ticker)
        
        # Убрали избыточное логирование - информация видна из других логов
    
    def _worker(self) -> None:
        """
        Рабочий поток для обработки тикеров
        Использует SignalAnalyzer и OrderGenerator согласно архитектуре
        """
        worker_id = threading.current_thread().name
        processed_count = 0
        
        while not self.stop_event.is_set():
            try:
                # Получаем тикер из очереди
                ticker = self.ticker_queue.get(timeout=1)
                
                if ticker is None or self.stop_event.is_set():
                    break
                
                processed_count += 1
                remaining = self.ticker_queue.qsize()
                
                # Логируем только каждые 20 тикеров или важные события
                if processed_count % 20 == 0 or remaining <= 10:
                    logger.info(f"🔍 [{worker_id}] Progress: {processed_count} processed, {remaining} remaining")
                
                try:
                    # 1. Анализируем сигналы через SignalAnalyzer
                    analyzer = SignalAnalyzer(ticker)
                    signal_data = analyzer.analyze_ticker(self.stop_event)
                    
                    self.stats.update(processed=1)
                    
                    # 2. Если найдено схождение - передаем в OrderGenerator
                    if signal_data:
                        logger.info(f"🎯 SIGNAL FOUND: {ticker} - {signal_data.get('signal', 'UNKNOWN')}")
                        self.stats.update(signals=1)
                        
                        # Передаем в OrderExecutor для создания ордера
                        if execute_trading_signal(signal_data):
                            self.stats.update(orders=1)
                            logger.info(f"✅ ORDER CREATED: {ticker}")
                        else:
                            logger.error(f"❌ ORDER FAILED: {ticker}")
                            self.stats.update(errors=1)
                
                except Exception as e:
                    logger.error(f"❌ Error processing {ticker}: {e}")
                    self.stats.update(errors=1)
                
                finally:
                    self.ticker_queue.task_done()
                    
                    # Контролируемая пауза между обработкой тикеров
                    if not self.stop_event.is_set():
                        time.sleep(self.ticker_delay)
            
            except Empty:
                # Таймаут очереди - нормальная ситуация
                continue
            except Exception as e:
                logger.error(f"❌ Worker {worker_id} critical error: {e}")
                self.stats.update(errors=1)
                continue
        
        logger.info(f"🏁 Worker {worker_id} completed: {processed_count} tickers processed")
    
    def _start_workers(self, num_workers: int = 1) -> None:
        """Запускает рабочие потоки"""
        self.worker_threads = []
        actual_workers = min(num_workers, self.max_workers, len(self.tickers))
        
        for i in range(actual_workers):
            worker = threading.Thread(
                target=self._worker,
                name=f"Worker-{i+1}",
                daemon=True
            )
            worker.start()
            self.worker_threads.append(worker)
        
        logger.info(f"🚀 Started {actual_workers} worker thread(s)")
    
    def _wait_for_completion(self) -> None:
        """Ожидает завершения обработки всех тикеров"""
        logger.info("⏳ Waiting for processing to complete...")
        
        # Более агрессивная проверка завершения
        max_wait_time = PROCESSING_TIMEOUT  # 5 минут максимум
        start_wait = time.time()
        last_log_time = 0
        
        while not self.ticker_queue.empty() and not self.stop_event.is_set():
            remaining = self.ticker_queue.qsize()
            elapsed = time.time() - start_wait
            
            # Логируем только каждые 30 секунд или при малом количестве тикеров
            if elapsed - last_log_time > 30 or remaining <= 5:
                logger.info(f"📊 Progress: {remaining} tickers remaining (elapsed: {elapsed:.1f}s)")
                last_log_time = elapsed
            
            # Проверяем таймаут
            if elapsed > max_wait_time:
                logger.warning(f"⚠️ Processing timeout after {max_wait_time}s, forcing shutdown...")
                self.stop_event.set()
                break
                
            time.sleep(2)
        
        # Принудительно завершаем все потоки
        active_threads = [t for t in self.worker_threads if t.is_alive()]
        if active_threads:
            logger.info(f"🔄 Shutting down {len(active_threads)} worker threads...")
            for worker in active_threads:
                worker.join(timeout=15)
                if worker.is_alive():
                    logger.warning(f"⚠️ Thread {worker.name} still alive after timeout")
        
        # Очищаем оставшиеся элементы в очереди
        cleared_count = 0
        while not self.ticker_queue.empty():
            try:
                self.ticker_queue.get_nowait()
                cleared_count += 1
            except Empty:
                break
        
        if cleared_count > 0:
            logger.warning(f"⚠️ Cleared {cleared_count} unprocessed items from queue")
        
        logger.info("✅ All workers completed")
    
    def _log_batch_summary(self) -> None:
        """Выводит итоговую статистику обработки"""
        summary = self.stats.get_summary()
        
        logger.info("=" * 60)
        logger.info("BATCH PROCESSING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Duration: {summary['duration_seconds']}s")
        logger.info(f"Tickers processed: {summary['processed']}/{len(self.tickers)}")
        logger.info(f"Signals found: {summary['signals_found']} ({summary['success_rate']}%)")
        logger.info(f"Orders/Alerts created: {summary['orders_created']} ({summary['conversion_rate']}%)")
        logger.info(f"Errors: {summary['errors']}")
        logger.info(f"Completed at: {datetime.now().strftime('%H:%M:%S')}")
        logger.info(f"Active threads: {threading.active_count()}")
        logger.info("=" * 60)
        
        # Принудительная очистка памяти
        gc.collect()
        
        # Дополнительная очистка переменных
        try:
            # Очищаем статистику для освобождения памяти
            self.stats.reset()
        except Exception as e:
            logger.debug(f"Warning during cleanup: {e}")
    
    def process_tickers(self) -> None:
        """
        Основной метод обработки всех тикеров
        Выполняет полный цикл: анализ -> генерация ордеров -> статистика
        """
        if self.stop_event.is_set():
            logger.info("🛑 Processing skipped - shutdown in progress")
            return
        
        if not self.tickers:
            logger.warning("⚠️ No tickers to process")
            return
        
        # Инициализация батча
        self.current_batch_start = datetime.now()
        self.stats.reset()
        self.stats.start_time = self.current_batch_start
        
        logger.info("🚀 STARTING TICKER PROCESSING BATCH")
        logger.info(f"📅 {self.current_batch_start.strftime('%H:%M:%S')} | {len(self.tickers)} tickers | {', '.join(TIMEFRAMES)} timeframes")
        
        try:
            # 1. Заполняем очередь тикерами
            self._fill_queue()
            
            # 2. Запускаем worker потоки
            self._start_workers(num_workers=self.max_workers)
            
            # 3. Ждем завершения обработки
            self._wait_for_completion()
            
        except Exception as e:
            logger.error(f"❌ Critical error during ticker processing: {e}")
        finally:
            # 4. Выводим итоговую статистику
            self._log_batch_summary()
    
    def run(self) -> None:
        """
        Главный цикл работы оркестратора
        Включает планировщик и обработку команд
        """
        logger.info("🎼 Ticker Monitor Orchestra started!")
        
        try:
            # Запускаем первичную обработку для проверки системы
            logger.info("🎬 Running initial processing...")
            self.process_tickers()
            
            # Настраиваем расписание - каждые 15 минут
            schedule.every().hour.at("00:00").do(self.process_tickers)
            schedule.every().hour.at("15:00").do(self.process_tickers) 
            schedule.every().hour.at("30:00").do(self.process_tickers)
            schedule.every().hour.at("45:00").do(self.process_tickers)

            logger.info("⏰ Scheduled processing at 00, 15, 30, 45 minutes of each hour")
            logger.info("🎵 Waiting for next scheduled processing... Press Ctrl+C to stop")
            
            # Главный цикл планировщика
            while not self.stop_event.is_set():
                try:
                    schedule.run_pending()
                    time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("⌨️ Keyboard interrupt received")
                    break
                except Exception as e:
                    logger.error(f"❌ Scheduler error: {e}")
                    time.sleep(5)  # Пауза перед продолжением
        
        except Exception as e:
            logger.error(f"💥 Fatal error in orchestrator: {e}")
            logger.debug(f"Stack trace: {traceback.format_exc()}")
        finally:
            self.shutdown()
    
    def get_status(self) -> Dict[str, Any]:
        """Возвращает текущий статус оркестратора"""
        return {
            'tickers_loaded': len(self.tickers),
            'queue_size': self.ticker_queue.qsize(),
            'active_workers': len([t for t in self.worker_threads if t.is_alive()]),
            'is_running': not self.stop_event.is_set(),
            'last_batch_start': self.current_batch_start.isoformat() if self.current_batch_start else None,
            'stats': self.stats.get_summary()
        }


def main():
    """
    Точка входа в приложение
    Инициализирует и запускает главный оркестратор
    """
    try:
        logger.info("🚀 Starting PATRIOT Ticker Monitor...")
        
        # Создаем и запускаем оркестратор
        monitor = TickerMonitor(
            max_workers=MAX_WORKERS,
            ticker_delay=TICKER_DELAY
        )
        monitor.run()
        
    except KeyboardInterrupt:
        logger.info("👋 Graceful shutdown requested by user")
    except Exception as e:
        logger.error(f"💥 Application failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()