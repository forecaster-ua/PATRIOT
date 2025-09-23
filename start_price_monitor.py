#!/usr/bin/env python3
"""
Простой веб-сервер для запуска Price Monitor UI
"""

import http.server
import socketserver
import webbrowser
import os
import sys
from pathlib import Path

def start_server(port=8080):
    """
    Запускает простой HTTP сервер для обслуживания HTML файлов
    """
    # Переходим в директорию с HTML файлом
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    try:
        # Создаем HTTP сервер
        handler = http.server.SimpleHTTPRequestHandler
        
        with socketserver.TCPServer(("", port), handler) as httpd:
            print("=" * 60)
            print("🚀 PATRIOT Price Monitor Server")
            print("=" * 60)
            print(f"📡 Server running on: http://localhost:{port}")
            print(f"📊 Monitor page: http://localhost:{port}/price_monitor.html")
            print("=" * 60)
            print("💡 Press Ctrl+C to stop the server")
            print()
            
            # Автоматически открываем браузер
            url = f"http://localhost:{port}/price_monitor.html"
            print(f"🌐 Opening browser: {url}")
            webbrowser.open(url)
            
            # Запускаем сервер
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
        sys.exit(0)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} is already in use!")
            print(f"💡 Try a different port: python3 {sys.argv[0]} [port]")
            sys.exit(1)
        else:
            print(f"❌ Error starting server: {e}")
            sys.exit(1)

def main():
    """Основная функция"""
    # Получаем порт из аргументов командной строки
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("❌ Invalid port number. Using default port 8080")
            port = 8080
    
    # Проверяем существование HTML файла
    html_file = Path(__file__).parent / "price_monitor.html"
    if not html_file.exists():
        print("❌ price_monitor.html not found!")
        print("📁 Make sure the HTML file is in the same directory as this script")
        sys.exit(1)
    
    start_server(port)

if __name__ == "__main__":
    main()
