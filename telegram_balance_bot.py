"""
Telegram Balance Bot
--------------------

Инструкция по запуску и остановке:
==================================

1. Требования:
   - Python 3.10+
   - Установленные зависимости из requirements.txt (pip install -r requirements.txt)
   - Переменные окружения:
       - TELEGRAM_TOKEN — токен Telegram-бота
       - BINANCE_MAINNET_API_KEY — API ключ Binance
       - BINANCE_MAINNET_API_SECRET — секретный ключ Binance

2. Запуск:
   - Через терминал:
       $ python telegram_balance_bot.py
   - Либо в фоне (например, через nohup или systemd):
       $ nohup python telegram_balance_bot.py &
   - Для Docker: создайте Dockerfile, добавьте переменные окружения и запустите контейнер.

3. Остановка:
   - Если запущено в терминале: нажмите Ctrl+C
   - Если запущено в фоне: найдите PID процесса и завершите его:
       $ ps aux | grep telegram_balance_bot.py
       $ kill <PID>
   - Для Docker: остановите контейнер командой
       $ docker stop <container_name>

4. Логи:
   - Логи выводятся в консоль. Для сохранения логов используйте перенаправление:
       $ python telegram_balance_bot.py > bot.log 2>&1

5. Проверка работы:
   - Отправьте сообщение "Balance" в Telegram-группу с ботом. Бот ответит отчетом по балансу, позициям и ордерам.

Реагирует на сообщение "Balance" в группе, возвращает отчет по балансу, позициям и ордерам.
"""

import os
from dotenv import load_dotenv
load_dotenv()

import logging
from io import StringIO
import contextlib
from telegram.ext import Application, MessageHandler, filters
from telegram.constants import ParseMode
from utils import logger
from get_account_summary_fut import FuturesMonitor

MAX_MSG_LEN = 4000

# Настроим python-telegram-bot логгер
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def get_full_report():
    # MAINNET credentials from environment only
    if not os.environ.get("BINANCE_MAINNET_API_KEY") or not os.environ.get("BINANCE_MAINNET_API_SECRET"):
        logger.error("MAINNET API keys not set in environment!")
        return "❌ MAINNET API keys not set!"
    monitor = FuturesMonitor()
    monitor.get_account_info()
    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        monitor.print_balance_summary()
        # monitor.print_positions_summary()
        # monitor.print_orders_summary()
    text = buf.getvalue()
    if len(text) > MAX_MSG_LEN:
        text = text[:MAX_MSG_LEN] + "... (truncated)"
    return f"<pre>{text}</pre>"


async def handle_balance(update, context):
    try:
        chat_id = update.effective_chat.id
        user = update.effective_user
        logger.info(f"Balance request from {user.username or user.id} in chat {chat_id}")
        report = get_full_report()
        await context.bot.send_message(
            chat_id=chat_id,
            text=report,
            parse_mode=ParseMode.HTML,
            disable_notification=False,
            protect_content=True
        )
    except Exception as e:
        logger.error(f"Telegram balance bot error: {e}")
        await update.message.reply_text("❌ Ошибка получения баланса")


def main():
    from telegram.ext import Application, MessageHandler, filters

    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_TOKEN not set in environment!")
        return
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    # Фильтр на точное текстовое сообщение "balance"
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^Balance$'), handle_balance))
    application.run_polling()
    logger.info("Telegram Balance Bot started!")


if __name__ == "__main__":
    main()
