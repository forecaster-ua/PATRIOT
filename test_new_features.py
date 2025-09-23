#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрые проверочные тесты без бинанса:
1) MAX_CONCURRENT_ORDERS по FILLED позициям (+ pending в анти-гонку)
2) Проверка лучшей цены LONG/SHORT
3) Трейлинг 80/80/50 (одноразовый триггер)
Выход с кодом 1 при любой ошибке.
"""
import os, sys
from dataclasses import dataclass, asdict
from typing import List, Optional

# ---- Фейковые сущности для изоляции от реального кода ----
@dataclass
class FakeOrder:
    symbol: str
    side: str           # BUY/SELL
    position_side: str  # LONG/SHORT
    price: float
    status: str         # NEW/FILLED/CANCELED

@dataclass
class FakePosition:
    symbol: str
    position_side: str
    entry_price: float
    qty: float

@dataclass
class FakeTrade:
    symbol: str
    side: str           # LONG/SHORT логика
    entry: float
    tp: float
    sl: float
    qty: float
    trailing_triggered: bool = False
    partially_taken: bool = False

class FakeRegistry:
    """Мини-реестр для подсчётов"""
    def __init__(self, positions: List[FakePosition], open_orders: List[FakeOrder]):
        self.positions = positions
        self.open_orders = open_orders

    def count_open_trades(self) -> int:
        # считаем только позиции с ненулевым объёмом (эмулируем FILLED)
        return sum(1 for p in self.positions if abs(p.qty) > 1e-12)

    def count_pending_orders(self) -> int:
        return sum(1 for o in self.open_orders if o.status == "NEW")

    def best_existing_price(self, symbol: str, side: str, position_side: str) -> Optional[float]:
        prices = []
        for o in self.open_orders:
            if o.symbol == symbol and o.position_side == position_side and o.status == "NEW":
                prices.append(o.price)
        for p in self.positions:
            if p.symbol == symbol and p.position_side == position_side and abs(p.qty) > 1e-12:
                prices.append(p.entry_price)
        return min(prices) if side == "BUY" else (max(prices) if prices else None) if side == "SELL" else (min(prices) if prices else None)

# ---- Проверяемая логика (должна совпадать с твоей реальной) ----
def can_place_new_order(reg: FakeRegistry, max_concurrent: int) -> bool:
    # лимит по реально открытым сделкам (positions FILLED)
    open_trades = reg.count_open_trades()
    pending = reg.count_pending_orders()
    # анти-гонка: не позволяем «переразогнаться», если суммарно уже достигли
    return (open_trades + pending) < max_concurrent

def is_price_improved(reg: FakeRegistry, symbol: str, side: str, position_side: str, new_price: float) -> bool:
    """
    LONG(BUY): новая цена должна быть ниже лучшей существующей
    SHORT(SELL): новая цена должна быть выше лучшей существующей
    Если нет существующих — True.
    """
    be = reg.best_existing_price(symbol, "BUY" if position_side == "LONG" else "SELL", position_side)
    if be is None:
        return True
    if position_side == "LONG":   # покупаем лучше — дешевле
        return new_price < be
    else:                         # SHORT — продаём лучше — дороже
        return new_price > be

def maybe_apply_trailing(trade: FakeTrade, last_price: float) -> Optional[dict]:
    if trade.trailing_triggered:
        return None
    if trade.side == "LONG":
        path = trade.tp - trade.entry
        if path <= 0: 
            return None
        progress = (last_price - trade.entry) / path
        if progress >= 0.8:
            trade.trailing_triggered = True
            trade.partially_taken = True
            new_sl = trade.entry + 0.5 * path
            close_qty = trade.qty * 0.8
            return {"close_qty": close_qty, "new_stop": new_sl}
    else:  # SHORT
        path = trade.entry - trade.tp
        if path <= 0:
            return None
        progress = (trade.entry - last_price) / path
        if progress >= 0.8:
            trade.trailing_triggered = True
            trade.partially_taken = True
            new_sl = trade.entry - 0.5 * path
            close_qty = trade.qty * 0.8
            return {"close_qty": close_qty, "new_stop": new_sl}
    return None

# ---- Тесты ----
def t_assert(cond, msg):
    if not cond:
        print("❌", msg)
        sys.exit(1)
    else:
        print("✅", msg)

def test_max_concurrent_orders():
    print("\n🔍 Тест 1: MAX_CONCURRENT_ORDERS логика")
    positions = [FakePosition("BTCUSDT", "LONG", 45000, 0.001)]
    open_orders = [FakeOrder("BTCUSDT", "BUY", "LONG", 44900, "NEW")]
    reg = FakeRegistry(positions, open_orders)

    t_assert(can_place_new_order(reg, 3) is True, "MAX=3 → можно (1 FILLED + 1 NEW < 3)")
    t_assert(can_place_new_order(reg, 2) is False, "MAX=2 → нельзя (1 FILLED + 1 NEW == 2) — анти-гонка")
    t_assert(can_place_new_order(reg, 1) is False, "MAX=1 → нельзя (уже есть FILLED)")

def test_price_quality():
    print("\n🔍 Тест 2: Проверка цены LONG/SHORT")
    positions = [FakePosition("BTCUSDT", "LONG", 45000, 0.002)]
    open_orders = [FakeOrder("BTCUSDT", "BUY", "LONG", 44950, "NEW")]
    reg = FakeRegistry(positions, open_orders)

    t_assert(is_price_improved(reg, "BTCUSDT", "BUY", "LONG", 44800) is True,  "LONG: 44800 лучше (ниже) → OK")
    t_assert(is_price_improved(reg, "BTCUSDT", "BUY", "LONG", 45200) is False, "LONG: 45200 хуже (выше) → Block")

    # SHORT
    positions2 = [FakePosition("ETHUSDT", "SHORT", 2600, 0.5)]
    open_orders2 = [FakeOrder("ETHUSDT", "SELL", "SHORT", 2610, "NEW")]
    reg2 = FakeRegistry(positions2, open_orders2)

    t_assert(is_price_improved(reg2, "ETHUSDT", "SELL", "SHORT", 2625) is True,  "SHORT: 2625 лучше (выше) → OK")
    t_assert(is_price_improved(reg2, "ETHUSDT", "SELL", "SHORT", 2580) is False, "SHORT: 2580 хуже (ниже) → Block")

def test_trailing():
    print("\n🔍 Тест 3: Трейлинг 80/80/50")
    # LONG: entry=100, tp=120 → 80% пути = 116 → SL должен стать 110, закрыть 80%
    t = FakeTrade("BTCUSDT", "LONG", entry=100, tp=120, sl=90, qty=1.0)
    act = maybe_apply_trailing(t, last_price=116)
    t_assert(act is not None, "LONG: трейлинг сработал на 80%")
    t_assert(abs(act["new_stop"] - 110) < 1e-9, "LONG: новый SL = 110 (entry + 50% пути)")
    t_assert(abs(act["close_qty"] - 0.8) < 1e-9, "LONG: закрыть 80% позиции")
    # повторное срабатывание не должно быть
    act2 = maybe_apply_trailing(t, last_price=118)
    t_assert(act2 is None, "LONG: повторно не срабатывает")

    # SHORT: entry=100, tp=80 → 80% пути = 84 → SL=90
    s = FakeTrade("BTCUSDT", "SHORT", entry=100, tp=80, sl=110, qty=2.0)
    act = maybe_apply_trailing(s, last_price=84)
    t_assert(act is not None, "SHORT: трейлинг сработал на 80%")
    t_assert(abs(act["new_stop"] - 90) < 1e-9, "SHORT: новый SL = 90 (entry - 50% пути)")
    t_assert(abs(act["close_qty"] - 1.6) < 1e-9, "SHORT: закрыть 80% позиции")
    act2 = maybe_apply_trailing(s, last_price=83)
    t_assert(act2 is None, "SHORT: повторно не срабатывает")

def test_capacity_frees_on_close():
    print("\n🔍 Тест 4: Слот освобождается после закрытия сделки")
    # Старт: 1 FILLED позиция + 1 NEW ордер → при MAX=2 новые заявки должны блокироваться
    positions = [FakePosition("BTCUSDT", "LONG", 45000, 0.002)]
    open_orders = [FakeOrder("BTCUSDT", "BUY", "LONG", 44950, "NEW")]
    reg = FakeRegistry(positions, open_orders)
    t_assert(can_place_new_order(reg, 2) is False, "До закрытия: (1 FILLED + 1 NEW) == 2 → нельзя")

    # Имитация закрытия сделки (позиция обнулилась; pending ордер исполнился/отменён)
    positions[0].qty = 0.0
    open_orders[0].status = "FILLED"  # или "CANCELED" — в обоих случаях не должен считаться pending

    # Теперь места должно хватать
    t_assert(can_place_new_order(reg, 2) is True, "После закрытия: (0 FILLED + 0 NEW) < 2 → можно")
    

def main():
    print("🧪 PATRIOT quick tests (MVP)\n" + "="*60)
    test_max_concurrent_orders()
    test_price_quality()
    test_trailing()
    test_capacity_frees_on_close()
    print("\n" + "="*60)
    print("✅ Все проверки пройдены")

if __name__ == "__main__":
    main()
