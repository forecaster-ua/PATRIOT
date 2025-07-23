import requests
from typing import Dict, Optional
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from utils import logger

class TelegramBot:
    def __init__(self):
        # Initialize the Telegram bot with the API base URL
        self.base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
        logger.info("Telegram bot initialized")

    def _send_request(self, payload: Dict) -> bool:
        """Core request handler with retry logic"""
        try:
            # Send a POST request to the Telegram API to send a message
            response = requests.post(
                f"{self.base_url}/sendMessage",
                json=payload,
                timeout=10
            )
            response.raise_for_status()  # Raise exception for HTTP errors
            return True
        except Exception as e:
            # Log any errors that occur during the request
            logger.error(f"Telegram send failed: {str(e)}")
            return False

    def send_signal(self, signal: Dict) -> None:
        """Format and send trading signal"""
        # Format the signal into a message
        message = self._format_message(signal)
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
            "disable_notification": False
        }
        
        # Attempt to send the message and log the result
        if self._send_request(payload):
            logger.info(f"Sent Telegram alert: {signal.get('pair', signal.get('ticker', 'N/A'))} {signal.get('timeframe', 'N/A')}")
        else:
            logger.warning(f"Failed to send: {signal.get('pair', signal.get('ticker', 'N/A'))}")
    
    def send_error(self, error_message: str, signal_data: Dict) -> None:
        """🚨 НОВЫЙ МЕТОД: Отправка уведомления об ошибке"""
        message = f"""🚨 *ОШИБКА ОРДЕРА* 🚨

📊 *Символ:* {signal_data.get('ticker', 'N/A')}
🎯 *Сигнал:* {signal_data.get('signal', 'N/A')}
💰 *Цена входа:* {signal_data.get('entry_price', 'N/A')}

❌ *Ошибка:* {error_message}

⏰ *Время:* {signal_data.get('timestamp', 'N/A')}"""
        
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
            "disable_notification": False
        }
        
        if self._send_request(payload):
            logger.info(f"✅ Уведомление об ошибке отправлено в Telegram")
        else:
            logger.error(f"❌ Не удалось отправить ошибку в Telegram")

    def send_message(self, message: str, parse_mode: str = "HTML") -> None:
        """Универсальный метод отправки сообщений"""
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": parse_mode,
            "disable_notification": False
        }
        
        if self._send_request(payload):
            logger.info("✅ Сообщение отправлено в Telegram")
        else:
            logger.error("❌ Не удалось отправить сообщение в Telegram")

    @staticmethod
    def _format_message(signal: Dict) -> str:
        """Формирует подробное сообщение о сигнале с информацией о капитале"""
        # Базовая информация о сигнале
        message = (
            f"🚀 *{signal.get('pair', signal.get('ticker', 'N/A'))} {signal.get('timeframe', 'N/A')}*\n"
            f"📍 Direction: {signal['signal']}\n"
            f"💰 Price: `{signal.get('current_price', signal.get('entry_price', 0))}`\n"
        )
        
        # Информация о позиции и капитале (если доступна)
        if 'quantity' in signal:
            message += f"📦 Position: `{signal['quantity']:.6f}`\n"
        if 'leverage' in signal:
            message += f"⚡ Leverage: `{signal['leverage']}x`\n"
        if 'capital_at_risk' in signal:
            message += f"💸 Capital at Risk: `{signal['capital_at_risk']}`\n"
        if 'position_value' in signal:
            message += f"📊 Position Value: `{signal['position_value']:.2f} USDT`\n"
        if 'total_balance' in signal:
            message += f"💳 Total Balance: `{signal['total_balance']:.2f} USDT`\n"
        
        # Дополнительная информация
        if 'confidence' in signal:
            message += f"📈 Confidence: {signal['confidence']*100:.1f}%\n"
        if 'order_type' in signal:
            message += f"📋 Order Type: `{signal['order_type']}`\n"
        if 'order_id' in signal:
            message += f"🆔 Order ID: `{signal['order_id']}`\n"
        if 'stop_order_id' in signal and signal['stop_order_id'] != 'FAILED':
            message += f"🛑 Stop Order ID: `{signal['stop_order_id']}`\n"
        if 'tp_order_id' in signal and signal['tp_order_id'] != 'FAILED':
            message += f"🎯 TP Order ID: `{signal['tp_order_id']}`\n"
        
        # Информация о stop/take (для совместимости)
        if signal.get('stop_loss', 0) > 0:
            message += f"🛑 Stop: `{signal['stop_loss']}`\n"
        if signal.get('take_profit', 0) > 0:
            message += f"🎯 Target: `{signal['take_profit']}`\n"
        
        # Временная метка
        if 'timestamp' in signal:
            from datetime import datetime
            try:
                if isinstance(signal['timestamp'], (int, float)):
                    dt = datetime.fromtimestamp(signal['timestamp'])
                    message += f"⏱️ {dt.strftime('%H:%M:%S')}"
                else:
                    message += f"⏱️ {signal['timestamp']}"
            except:
                message += f"⏱️ {signal.get('timestamp', 'N/A')}"
        
        # Добавляем остальные поля для совместимости с базовой версией
        if 'dominance_change_percent' in signal:
            message += f"\n🔍 Dominance Change: {signal.get('dominance_change_percent', 0):.2f}%"
        
        return message

# Singleton instance of the TelegramBot class for use throughout the project
telegram_bot = TelegramBot()
