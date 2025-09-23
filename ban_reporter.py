#!/usr/bin/env python3
"""
Ban Reporter - Проверка статуса торговых ограничений Binance API
==============================================================

Проверяет статус API Trading Ban через endpoint /fapi/v1/apiTradingStatus
Использует конфигурацию из config.py для выбора MAINNET/TESTNET

Author: HEDGER
Version: 1.0
"""

import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from config import BINANCE_API_KEY, BINANCE_API_SECRET, NETWORK_MODE

# URL для Binance Futures
BASE_URL = "https://fapi.binance.com"
ENDPOINT = "/fapi/v1/apiTradingStatus"

def get_signed_params(secret: str, params: dict) -> dict:
    """
    Создает подпись HMAC SHA256 для запроса к Binance API
    
    Args:
        secret: API Secret ключ
        params: Параметры запроса
        
    Returns:
        dict: Параметры с добавленной подписью
    """
    query_string = urlencode(params)
    signature = hmac.new(
        secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    params['signature'] = signature
    return params


def check_api_trading_status() -> dict:
    """
    Проверяет статус торговых ограничений API
    
    Returns:
        dict: Результат проверки статуса
    """
    # Проверяем наличие API ключей
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        print(f"❌ Error: Binance {NETWORK_MODE} API keys not configured!")
        print(f"Please set BINANCE_{NETWORK_MODE}_API_KEY and BINANCE_{NETWORK_MODE}_API_SECRET in .env")
        return {"error": "API keys not configured"}
    
    # Подготавливаем параметры запроса
    timestamp = int(time.time() * 1000)
    params = {"timestamp": timestamp}
    signed_params = get_signed_params(BINANCE_API_SECRET, params)
    
    # Заголовки запроса
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY}
    
    # Выполняем запрос
    url = BASE_URL + ENDPOINT
    
    try:
        print(f"🔍 Checking API trading status for {NETWORK_MODE}...")
        print(f"📡 Request URL: {url}")
        print(f"🔑 API Key: {BINANCE_API_KEY[:10]}...{BINANCE_API_KEY[-10:]}")
        
        response = requests.get(url, headers=headers, params=signed_params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        print("\n" + "="*60)
        print("📊 API TRADING STATUS REPORT")
        print("="*60)
        print(f"Network Mode: {NETWORK_MODE}")
        print(f"Request Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print()
        
        # Проверяем статус блокировки
        is_banned = data.get('isApiTradingBanned', False)
        ban_reason = data.get('apiTradingBannedReason', 'N/A')
        ban_expire_time = data.get('apiTradingBannedExpireTime', 0)
        
        if is_banned:
            print("🚫 API TRADING STATUS: BANNED")
            print(f"📝 Ban Reason: {ban_reason}")
            
            if ban_expire_time > 0:
                expire_date = time.strftime('%Y-%m-%d %H:%M:%S UTC', 
                                          time.gmtime(ban_expire_time / 1000))
                print(f"⏰ Ban Expires: {expire_date}")
                
                # Рассчитываем оставшееся время
                current_time = int(time.time() * 1000)
                remaining_ms = ban_expire_time - current_time
                if remaining_ms > 0:
                    remaining_hours = remaining_ms // (1000 * 60 * 60)
                    remaining_minutes = (remaining_ms // (1000 * 60)) % 60
                    print(f"⌛ Time Remaining: {remaining_hours}h {remaining_minutes}m")
            else:
                print("⏰ Ban Expires: Permanent or unknown")
                
        else:
            print("✅ API TRADING STATUS: ACTIVE")
            print("🎯 Trading operations are allowed")
        
        print("="*60)
        
        return {
            "is_banned": is_banned,
            "ban_reason": ban_reason,
            "ban_expire_time": ban_expire_time,
            "network_mode": NETWORK_MODE,
            "success": True
        }
        
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP Error {e.response.status_code}: {e.response.reason}"
        
        if e.response.status_code == 400:
            error_msg += "\n💡 Possible causes:"
            error_msg += "\n   • Invalid API keys"
            error_msg += "\n   • Incorrect timestamp"
            error_msg += "\n   • Missing signature"
        elif e.response.status_code == 401:
            error_msg += "\n💡 Authentication failed - check API keys"
        elif e.response.status_code == 403:
            error_msg += "\n💡 Access forbidden - check API permissions"
        
        print(f"❌ {error_msg}")
        
        try:
            error_data = e.response.json()
            print(f"📝 Server response: {error_data}")
        except:
            pass
            
        return {"error": error_msg, "success": False}
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Request failed: {e}"
        print(f"❌ {error_msg}")
        return {"error": error_msg, "success": False}
        
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(f"❌ {error_msg}")
        return {"error": error_msg, "success": False}


def main():
    """Главная функция для CLI использования"""
    try:
        result = check_api_trading_status()
        
        if result.get("success"):
            exit_code = 1 if result.get("is_banned") else 0
        else:
            exit_code = 2
            
        exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n👋 Interrupted by user")
        exit(3)


if __name__ == "__main__":
    main()