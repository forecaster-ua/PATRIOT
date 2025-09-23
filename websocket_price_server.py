#!/usr/bin/env python3
"""
WebSocket сервер для мониторинга цен криптовалют
Получает данные через Binance WebSocket и передает их в браузер
"""

import asyncio
import websockets
import json
import aiohttp
import logging
from datetime import datetime
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CryptoPriceServer:
    def __init__(self):
        self.clients = set()
        self.binance_ws = None
        self.is_running = False
        
        # Список тикеров из файла tickers.txt
        self.tickers = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 
            'ADAUSDT', 'ALGOUSDT', 'APTUSDT', 'AVAXUSDT',
            'SOLUSDT', 'CRVUSDT', 'BCHUSDT',
            'WIFUSDT', 'XLMUSDT', 'XRPUSDT', 'XTZUSDT'
        ]
        
        logger.info(f"Initialized server for {len(self.tickers)} tickers")

    async def register_client(self, websocket):
        """Регистрация нового клиента"""
        self.clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address}")
        
        try:
            # Отправляем список тикеров новому клиенту
            await websocket.send(json.dumps({
                'type': 'tickers',
                'data': self.tickers
            }))
            
            # Ожидаем сообщения от клиента
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_client_message(websocket, data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from client: {message}")
                except Exception as e:
                    logger.error(f"Error handling client message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {websocket.remote_address}")
        finally:
            self.clients.discard(websocket)

    async def handle_client_message(self, websocket, data):
        """Обработка сообщений от клиента"""
        message_type = data.get('type')
        
        if message_type == 'start':
            logger.info("Client requested to start monitoring")
            if not self.is_running:
                await self.start_binance_stream()
            await websocket.send(json.dumps({
                'type': 'status',
                'status': 'connected'
            }))
            
        elif message_type == 'stop':
            logger.info("Client requested to stop monitoring")
            await self.stop_binance_stream()
            await websocket.send(json.dumps({
                'type': 'status',
                'status': 'disconnected'
            }))

    async def start_binance_stream(self):
        """Запуск подключения к Binance WebSocket"""
        if self.is_running:
            return
            
        try:
            # Создаем поток для всех тикеров
            streams = [f"{ticker.lower()}@ticker" for ticker in self.tickers]
            stream_name = '/'.join(streams)
            
            url = f"wss://stream.binance.com:9443/ws/{stream_name}"
            logger.info(f"Connecting to Binance WebSocket: {url}")
            
            self.binance_ws = await websockets.connect(url)
            self.is_running = True
            
            # Запускаем задачу для получения данных
            asyncio.create_task(self.process_binance_data())
            
            logger.info("Successfully connected to Binance WebSocket")
            
        except Exception as e:
            logger.error(f"Failed to connect to Binance: {e}")
            self.is_running = False

    async def stop_binance_stream(self):
        """Остановка подключения к Binance WebSocket"""
        self.is_running = False
        if self.binance_ws:
            await self.binance_ws.close()
            self.binance_ws = None
            logger.info("Binance WebSocket connection closed")

    async def process_binance_data(self):
        """Обработка данных от Binance WebSocket"""
        try:
            if self.binance_ws is None:
                logger.error("Binance WebSocket is not connected")
                return
                
            async for message in self.binance_ws:
                if not self.is_running:
                    break
                    
                try:
                    data = json.loads(message)
                    await self.broadcast_price_update(data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from Binance: {message}")
                except Exception as e:
                    logger.error(f"Error processing Binance data: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Binance WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error in Binance data processing: {e}")
        finally:
            self.is_running = False

    async def broadcast_price_update(self, data):
        """Отправка обновления цены всем подключенным клиентам"""
        if not self.clients:
            return
            
        # Форматируем данные для клиентов
        update = {
            'type': 'price_update',
            'symbol': data.get('s'),
            'price': float(data.get('c', 0)),
            'change_24h': float(data.get('P', 0)),
            'volume': float(data.get('v', 0)),
            'timestamp': datetime.now().isoformat()
        }
        
        message = json.dumps(update)
        
        # Отправляем всем клиентам
        disconnected_clients = set()
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected_clients.add(client)
        
        # Удаляем отключенных клиентов
        self.clients -= disconnected_clients

async def main():
    """Основная функция"""
    server = CryptoPriceServer()
    
    print("=" * 60)
    print("🚀 PATRIOT WebSocket Price Server")
    print("=" * 60)
    print("📡 Starting WebSocket server on localhost:8765")
    print("🔗 Connect from browser to: ws://localhost:8765")
    print("💰 Monitoring tickers:", ", ".join(server.tickers))
    print("=" * 60)
    print("💡 Press Ctrl+C to stop the server")
    print()
    
    try:
        # Запуск WebSocket сервера
        async with websockets.serve(server.register_client, "localhost", 8765):
            await asyncio.Future()  # run forever
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")

def run_server():
    """Запуск сервера"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")

if __name__ == "__main__":
    run_server()
