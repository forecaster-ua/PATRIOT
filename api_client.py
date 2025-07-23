import requests
from datetime import datetime, timezone
from typing import Optional, Dict
from urllib.parse import urljoin
from utils import logger
import time
from tenacity import retry, stop_after_attempt, retry_if_exception, wait_fixed

# Circuit Breaker Configuration
CIRCUIT_BREAKER_THRESHOLD = 5  # Max consecutive 500 errors before pausing
CIRCUIT_BREAKER_TIMEOUT = 60   # Seconds to pause after threshold

def is_500_error(e):
    """Check if exception is a 500 error"""
    return isinstance(e, (requests.HTTPError, requests.ConnectionError)) and getattr(e.response, 'status_code', None) == 500

class APIClient:
    """Handles all API communications with signal provider"""
    
    def __init__(self):
        self.base_url = "https://5ca35593a63d.ngrok-free.app/"  # Base URL for the API
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": "Bearer my_secret_9876_maxa",
            "Content-Type": "application/json"
        })
        self._consecutive_500s = 0
        self._circuit_tripped_until = 0
        logger.info("API Client initialized")

    def _check_circuit_breaker(self):
        """Returns True if requests should be blocked"""
        if time.time() < self._circuit_tripped_until:
            remaining = self._circuit_tripped_until - time.time()
            logger.warning(f"Circuit breaker active (cooldown: {remaining:.1f}s)")
            return True
        return False

    def _trip_circuit_breaker(self):
        """Activate the circuit breaker"""
        self._circuit_tripped_until = time.time() + CIRCUIT_BREAKER_TIMEOUT
        self._consecutive_500s = 0  # Reset counter after tripping
        logger.error(f"🚨 Circuit breaker triggered! Pausing for {CIRCUIT_BREAKER_TIMEOUT}s")

    @retry(
        stop=stop_after_attempt(3),
        retry=retry_if_exception(is_500_error),
        wait=wait_fixed(1),
        before_sleep=lambda _: logger.warning("Retrying after 500 error...")
    )
    def get_signal(self, pair: str, timeframe: str, timeout: int = 10) -> Optional[Dict]:
        """
        Fetch trading signal for specified pair and timeframe
        with comprehensive error handling and logging.
        """
        if self._check_circuit_breaker():
            return None

        endpoint = f"signal?pair={pair}&timeframe={timeframe}"
        url = urljoin(self.base_url, endpoint)
        
        try:
            start_time = datetime.now(timezone.utc)
            response = self.session.get(url, timeout=timeout)
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()

            if response.status_code == 500:
                self._consecutive_500s += 1
                if self._consecutive_500s >= CIRCUIT_BREAKER_THRESHOLD:
                    self._trip_circuit_breaker()
                response.raise_for_status()  # Trigger retry

            if not response.ok:
                self._log_error(response, pair, timeframe, elapsed)
                return None

            data = response.json()
             # Remove debug print for production
            # print("API raw response:", data)
            direction = data.get('signal')  # Changed from 'direction' to 'signal'
            current = float(data.get('current_price', 0))
            confidence = float(data.get('confidence', 0)) * 100

            # Reset 500 counter on successful request
            self._consecutive_500s = 0

            logger.info(
                f"Signal received | {pair} {timeframe} | "
                f"Entry: {data.get('entry_price')} | "
                f"Current: {current} | "
                f"Signal: {direction} | "
                f"Confidence: {confidence:.1f}% | "
                f"Latency: {elapsed:.3f}s"
            )

            return {
                'pair': data.get('pair'),
                'timeframe': data.get('timeframe'),
                'signal': data.get('signal'),
                'current_price': float(data.get('current_price', 0)),
                'entry_price': float(data.get('entry_price', 0)),   
                'take_profit': float(data.get('take_profit', 0)),
                'stop_loss': float(data.get('stop_loss', 0)),
                'confidence': float(data.get('confidence', 0)),
                'dominance': float(data.get('dominance', 0)),
                'dominance_change_percent': float(data.get('dominance_change_percent', 0)),
                'dominant_timeframe': data.get('dominant_timeframe', ''),
                'description': data.get('description', ''),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code != 500:  # Already handled 500s
                logger.error(f"HTTP Error | {pair} {timeframe} | Status: {e.response.status_code}")
            return None
        except (ValueError, KeyError) as e:
            logger.error(f"Data parsing failed | {pair} {timeframe} | Error: {type(e).__name__}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error | {pair} {timeframe} | Error: {type(e).__name__}")
            return None

    def _log_error(self, response: requests.Response, pair: str, timeframe: str, elapsed: float) -> None:
        """Log API error responses"""
        error_msg = response.text.strip()[:200]
        logger.error(
            f"API Error | {pair} {timeframe} | "
            f"Status: {response.status_code} | "
            f"Latency: {elapsed:.3f}s | "
            f"Response: {error_msg}"
        )

# Singleton instance
api_client = APIClient()