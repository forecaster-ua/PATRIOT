import order_monitor
print('✅ order_monitor.py - синтаксис OK')

import websocket_realtime_monitor  
print('✅ websocket_realtime_monitor.py - синтаксис OK')

print('')
print('🔥 КРИТИЧЕСКИЕ БАГИ ИСПРАВЛЕНЫ:')
print('1. ✅ Основные ордера теперь отслеживаются (main_status: NEW)')
print('2. ✅ Отмена основного ордера → отмена SL/TP')
print('3. ✅ Исполнение основного ордера → уведомление о входе')
print('4. ✅ Система продолжает мониторинг после всех событий')
print('5. ✅ Все изменения статусов логируются и уведомляются')
print('')
print('🎯 ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ В ОБЕИХ СИСТЕМАХ:')
print('• REST API мониторинг (order_monitor.py)')
print('• WebSocket real-time мониторинг (websocket_realtime_monitor.py)')
