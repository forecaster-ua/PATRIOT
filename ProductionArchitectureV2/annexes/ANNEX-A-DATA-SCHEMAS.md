# PATRIOT Trading System - Data Schemas and API Contracts

## 📋 Document Information

**Document ID**: ANNEX-A-DATA-SCHEMAS  
**Version**: 2.0  
**Date**: September 2025  
**Authors**: Solution Architecture Team  
**Status**: Draft  

> **Cross-References:**  
> - System Architecture: [../02-SYSTEM-ARCHITECTURE.md](../02-SYSTEM-ARCHITECTURE.md#event-streaming)  
> - Component Specifications: [../03-COMPONENT-SPECIFICATIONS.md](../03-COMPONENT-SPECIFICATIONS.md)  
> - Infrastructure: [../04-INFRASTRUCTURE.md](../04-INFRASTRUCTURE.md#kafka-cluster-configuration)

---

## 🎯 Overview

This annex provides comprehensive schemas for all data contracts used in the PATRIOT trading system, including Kafka event schemas, REST API contracts, database models, and inter-service communication formats.

### Schema Categories

**Event Schemas**: Kafka topic message formats for event-driven communication  
**API Contracts**: REST API request/response schemas for external interfaces  
**Database Models**: Data structure definitions for persistence layers  
**WebSocket Messages**: Real-time data format specifications

---

## 📨 Kafka Event Schemas

### User Management Events

#### user.registered
**Topic**: `user-events`  
**Partition Key**: `user_id`  
**Schema Version**: v1.0  

```json
{
  "schema": {
    "type": "object",
    "required": ["event_id", "event_type", "stream_id", "occurred_at", "data"],
    "properties": {
      "event_id": {
        "type": "string",
        "format": "uuid",
        "description": "Unique event identifier"
      },
      "event_type": {
        "type": "string",
        "enum": ["user.registered"],
        "description": "Event type identifier"
      },
      "stream_id": {
        "type": "string", 
        "format": "uuid",
        "description": "User ID (aggregate identifier)"
      },
      "event_version": {
        "type": "integer",
        "minimum": 1,
        "description": "Event version in stream"
      },
      "correlation_id": {
        "type": "string",
        "format": "uuid", 
        "description": "Request correlation identifier"
      },
      "occurred_at": {
        "type": "string",
        "format": "date-time",
        "description": "Event occurrence timestamp"
      },
      "data": {
        "type": "object",
        "required": ["user_id", "telegram_id", "username", "risk_profile"],
        "properties": {
          "user_id": {
            "type": "string",
            "format": "uuid"
          },
          "telegram_id": {
            "type": "integer",
            "minimum": 1
          },
          "username": {
            "type": "string",
            "minLength": 3,
            "maxLength": 50
          },
          "email": {
            "type": "string",
            "format": "email",
            "nullable": true
          },
          "risk_profile": {
            "type": "string",
            "enum": ["LOW", "MEDIUM", "HIGH"]
          },
          "created_at": {
            "type": "string",
            "format": "date-time"
          }
        }
      }
    }
  },
  "example": {
    "event_id": "550e8400-e29b-41d4-a716-446655440001",
    "event_type": "user.registered",
    "stream_id": "550e8400-e29b-41d4-a716-446655440000",
    "event_version": 1,
    "correlation_id": "550e8400-e29b-41d4-a716-446655440002",
    "occurred_at": "2025-09-24T20:30:00Z",
    "data": {
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "telegram_id": 123456789,
      "username": "trader_john",
      "email": "john@example.com",
      "risk_profile": "MEDIUM",
      "created_at": "2025-09-24T20:30:00Z"
    }
  }
}
```

#### account.linked
**Topic**: `user-events`  
**Partition Key**: `user_id`  
**Schema Version**: v1.0  

```json
{
  "schema": {
    "type": "object", 
    "required": ["event_id", "event_type", "stream_id", "occurred_at", "data"],
    "properties": {
      "event_id": {"type": "string", "format": "uuid"},
      "event_type": {"type": "string", "enum": ["account.linked"]},
      "stream_id": {"type": "string", "format": "uuid"},
      "event_version": {"type": "integer", "minimum": 1},
      "correlation_id": {"type": "string", "format": "uuid"},
      "occurred_at": {"type": "string", "format": "date-time"},
      "data": {
        "type": "object",
        "required": ["user_id", "account_id", "exchange", "account_name"],
        "properties": {
          "user_id": {"type": "string", "format": "uuid"},
          "account_id": {"type": "string", "format": "uuid"},
          "exchange": {
            "type": "string",
            "enum": ["BINANCE", "BYBIT"]
          },
          "account_name": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100
          },
          "linked_at": {"type": "string", "format": "date-time"}
        }
      }
    }
  },
  "example": {
    "event_id": "550e8400-e29b-41d4-a716-446655440003",
    "event_type": "account.linked",
    "stream_id": "550e8400-e29b-41d4-a716-446655440000",
    "event_version": 2,
    "correlation_id": "550e8400-e29b-41d4-a716-446655440004",
    "occurred_at": "2025-09-24T20:35:00Z",
    "data": {
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "account_id": "550e8400-e29b-41d4-a716-446655440005",
      "exchange": "BINANCE",
      "account_name": "Main Trading Account",
      "linked_at": "2025-09-24T20:35:00Z"
    }
  }
}
```

### Trading Events

#### order.created
**Topic**: `trading-events`  
**Partition Key**: `user_id`  
**Schema Version**: v1.0  

```json
{
  "schema": {
    "type": "object",
    "required": ["event_id", "event_type", "stream_id", "occurred_at", "data"],
    "properties": {
      "event_id": {"type": "string", "format": "uuid"},
      "event_type": {"type": "string", "enum": ["order.created"]},
      "stream_id": {"type": "string", "format": "uuid"},
      "event_version": {"type": "integer", "minimum": 1},
      "correlation_id": {"type": "string", "format": "uuid"},
      "occurred_at": {"type": "string", "format": "date-time"},
      "data": {
        "type": "object",
        "required": ["order_id", "user_id", "account_id", "symbol", "side", "type", "quantity", "status"],
        "properties": {
          "order_id": {"type": "string", "format": "uuid"},
          "user_id": {"type": "string", "format": "uuid"},
          "account_id": {"type": "string", "format": "uuid"},
          "strategy_id": {"type": "string", "format": "uuid", "nullable": true},
          "symbol": {
            "type": "string",
            "pattern": "^[A-Z]{3,10}USDT$"
          },
          "side": {
            "type": "string", 
            "enum": ["BUY", "SELL"]
          },
          "position_side": {
            "type": "string",
            "enum": ["LONG", "SHORT", "BOTH"],
            "nullable": true
          },
          "type": {
            "type": "string",
            "enum": ["MARKET", "LIMIT", "STOP_MARKET", "STOP_LIMIT", "TAKE_PROFIT"]
          },
          "quantity": {
            "type": "string",
            "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"
          },
          "price": {
            "type": "string",
            "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$",
            "nullable": true
          },
          "stop_price": {
            "type": "string", 
            "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$",
            "nullable": true
          },
          "time_in_force": {
            "type": "string",
            "enum": ["GTC", "IOC", "FOK"],
            "default": "GTC"
          },
          "status": {
            "type": "string",
            "enum": ["PENDING", "NEW", "PARTIALLY_FILLED", "FILLED", "CANCELLED", "REJECTED"]
          },
          "reduce_only": {
            "type": "boolean",
            "default": false
          },
          "created_at": {"type": "string", "format": "date-time"}
        }
      }
    }
  },
  "example": {
    "event_id": "550e8400-e29b-41d4-a716-446655440010",
    "event_type": "order.created", 
    "stream_id": "550e8400-e29b-41d4-a716-446655440011",
    "event_version": 1,
    "correlation_id": "550e8400-e29b-41d4-a716-446655440012",
    "occurred_at": "2025-09-24T20:40:00Z",
    "data": {
      "order_id": "550e8400-e29b-41d4-a716-446655440011",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "account_id": "550e8400-e29b-41d4-a716-446655440005",
      "strategy_id": "550e8400-e29b-41d4-a716-446655440020",
      "symbol": "BTCUSDT",
      "side": "BUY",
      "position_side": "LONG",
      "type": "LIMIT",
      "quantity": "0.001",
      "price": "65000.00",
      "stop_price": null,
      "time_in_force": "GTC",
      "status": "PENDING",
      "reduce_only": false,
      "created_at": "2025-09-24T20:40:00Z"
    }
  }
}
```

#### order.filled
**Topic**: `trading-events`  
**Partition Key**: `user_id`  
**Schema Version**: v1.0  

```json
{
  "schema": {
    "type": "object",
    "required": ["event_id", "event_type", "stream_id", "occurred_at", "data"],
    "properties": {
      "event_id": {"type": "string", "format": "uuid"},
      "event_type": {"type": "string", "enum": ["order.filled"]},
      "stream_id": {"type": "string", "format": "uuid"},
      "event_version": {"type": "integer", "minimum": 1},
      "correlation_id": {"type": "string", "format": "uuid"},
      "occurred_at": {"type": "string", "format": "date-time"},
      "data": {
        "type": "object",
        "required": ["order_id", "fill_id", "filled_quantity", "fill_price", "commission"],
        "properties": {
          "order_id": {"type": "string", "format": "uuid"},
          "fill_id": {"type": "string", "format": "uuid"},
          "exchange_order_id": {"type": "string"},
          "exchange_fill_id": {"type": "string"},
          "filled_quantity": {
            "type": "string",
            "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"
          },
          "fill_price": {
            "type": "string", 
            "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"
          },
          "commission": {
            "type": "string",
            "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"
          },
          "commission_asset": {"type": "string"},
          "is_partial": {"type": "boolean"},
          "cumulative_filled": {
            "type": "string",
            "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"
          },
          "remaining_quantity": {
            "type": "string",
            "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"
          },
          "avg_fill_price": {
            "type": "string",
            "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"
          },
          "filled_at": {"type": "string", "format": "date-time"}
        }
      }
    }
  }
}
```

### Market Data Events

#### market.data.price_update  
**Topic**: `market-data-prices`  
**Partition Key**: `symbol`  
**Schema Version**: v1.0  

```json
{
  "schema": {
    "type": "object",
    "required": ["exchange", "symbol", "price", "timestamp"],
    "properties": {
      "exchange": {
        "type": "string",
        "enum": ["BINANCE", "BYBIT"]
      },
      "symbol": {
        "type": "string",
        "pattern": "^[A-Z]{3,10}USDT$"
      },
      "price": {
        "type": "number",
        "minimum": 0
      },
      "quantity": {
        "type": "number", 
        "minimum": 0
      },
      "bid_price": {
        "type": "number",
        "minimum": 0,
        "nullable": true
      },
      "ask_price": {
        "type": "number",
        "minimum": 0,
        "nullable": true
      },
      "volume_24h": {
        "type": "number",
        "minimum": 0,
        "nullable": true
      },
      "price_change_24h": {
        "type": "number",
        "nullable": true
      },
      "price_change_percent_24h": {
        "type": "number",
        "nullable": true
      },
      "timestamp": {
        "type": "integer",
        "minimum": 0,
        "description": "Unix timestamp in milliseconds"
      }
    }
  },
  "example": {
    "exchange": "BINANCE",
    "symbol": "BTCUSDT", 
    "price": 65234.50,
    "quantity": 0.025,
    "bid_price": 65234.00,
    "ask_price": 65235.00,
    "volume_24h": 45678.123,
    "price_change_24h": 1234.50,
    "price_change_percent_24h": 1.93,
    "timestamp": 1727206800000
  }
}
```

### Risk Management Events

#### risk.violation
**Topic**: `risk-events`  
**Partition Key**: `user_id`  
**Schema Version**: v1.0  

```json
{
  "schema": {
    "type": "object",
    "required": ["event_id", "event_type", "occurred_at", "data"],
    "properties": {
      "event_id": {"type": "string", "format": "uuid"},
      "event_type": {"type": "string", "enum": ["risk.violation"]},
      "correlation_id": {"type": "string", "format": "uuid"},
      "occurred_at": {"type": "string", "format": "date-time"},
      "data": {
        "type": "object",
        "required": ["user_id", "violation_type", "severity", "current_value", "limit_value"],
        "properties": {
          "user_id": {"type": "string", "format": "uuid"},
          "account_id": {"type": "string", "format": "uuid", "nullable": true},
          "violation_type": {
            "type": "string",
            "enum": ["POSITION_SIZE", "DAILY_LOSS", "MAX_DRAWDOWN", "LEVERAGE", "VAR_LIMIT", "CORRELATION"]
          },
          "severity": {
            "type": "string",
            "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
          },
          "current_value": {"type": "number"},
          "limit_value": {"type": "number"},
          "description": {"type": "string"},
          "affected_positions": {
            "type": "array",
            "items": {"type": "string"}
          },
          "suggested_actions": {
            "type": "array",
            "items": {"type": "string"}
          },
          "auto_action_taken": {
            "type": "string",
            "enum": ["NONE", "POSITION_REDUCTION", "STRATEGY_PAUSE", "EMERGENCY_STOP"],
            "nullable": true
          }
        }
      }
    }
  }
}
```

---

## 🔌 REST API Schemas

### User Management API

#### POST /api/v1/users/register
**Request Schema**:
```json
{
  "type": "object",
  "required": ["telegram_id", "username"],
  "properties": {
    "telegram_id": {
      "type": "integer",
      "minimum": 1,
      "description": "Telegram user ID"
    },
    "username": {
      "type": "string", 
      "minLength": 3,
      "maxLength": 50,
      "pattern": "^[a-zA-Z0-9_]+$"
    },
    "email": {
      "type": "string",
      "format": "email",
      "nullable": true
    },
    "risk_profile": {
      "type": "string",
      "enum": ["LOW", "MEDIUM", "HIGH"],
      "default": "MEDIUM"
    }
  }
}
```

**Response Schema**:
```json
{
  "type": "object",
  "required": ["user_id", "status", "created_at"],
  "properties": {
    "user_id": {
      "type": "string",
      "format": "uuid"
    },
    "status": {
      "type": "string",
      "enum": ["registered"]
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

#### POST /api/v1/users/{user_id}/accounts/link
**Request Schema**:
```json
{
  "type": "object",
  "required": ["exchange", "account_name", "api_key", "api_secret"],
  "properties": {
    "exchange": {
      "type": "string",
      "enum": ["BINANCE", "BYBIT"]
    },
    "account_name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100
    },
    "api_key": {
      "type": "string",
      "minLength": 10,
      "maxLength": 200
    },
    "api_secret": {
      "type": "string",
      "minLength": 10,
      "maxLength": 200
    },
    "passphrase": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100,
      "nullable": true,
      "description": "Required for some exchanges"
    },
    "test_mode": {
      "type": "boolean",
      "default": false,
      "description": "Use testnet/sandbox environment"
    }
  }
}
```

### Order Management API

#### POST /api/v1/orders
**Request Schema**:
```json
{
  "type": "object",
  "required": ["account_id", "symbol", "side", "type", "quantity"],
  "properties": {
    "account_id": {
      "type": "string",
      "format": "uuid"
    },
    "strategy_id": {
      "type": "string", 
      "format": "uuid",
      "nullable": true
    },
    "symbol": {
      "type": "string",
      "pattern": "^[A-Z]{3,10}USDT$"
    },
    "side": {
      "type": "string",
      "enum": ["BUY", "SELL"]
    },
    "position_side": {
      "type": "string",
      "enum": ["LONG", "SHORT", "BOTH"],
      "nullable": true,
      "description": "Required for hedge mode"
    },
    "type": {
      "type": "string",
      "enum": ["MARKET", "LIMIT", "STOP_MARKET", "STOP_LIMIT", "TAKE_PROFIT"]
    },
    "quantity": {
      "type": "string",
      "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$",
      "description": "Order quantity as string to preserve precision"
    },
    "price": {
      "type": "string", 
      "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$",
      "nullable": true,
      "description": "Required for LIMIT and STOP_LIMIT orders"
    },
    "stop_price": {
      "type": "string",
      "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$", 
      "nullable": true,
      "description": "Required for STOP orders"
    },
    "time_in_force": {
      "type": "string",
      "enum": ["GTC", "IOC", "FOK"],
      "default": "GTC"
    },
    "reduce_only": {
      "type": "boolean",
      "default": false,
      "description": "Reduce position only"
    }
  }
}
```

**Response Schema**:
```json
{
  "type": "object", 
  "required": ["order_id", "status", "created_at"],
  "properties": {
    "order_id": {
      "type": "string",
      "format": "uuid"
    },
    "client_order_id": {
      "type": "string",
      "nullable": true
    },
    "status": {
      "type": "string",
      "enum": ["PENDING", "NEW", "PARTIALLY_FILLED", "FILLED", "CANCELLED", "REJECTED"]
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "estimated_fill_time": {
      "type": "string",
      "format": "date-time",
      "nullable": true,
      "description": "Estimated execution time for market orders"
    }
  }
}
```

#### GET /api/v1/orders/{order_id}
**Response Schema**:
```json
{
  "type": "object",
  "required": ["order_id", "user_id", "account_id", "symbol", "side", "type", "quantity", "status", "created_at"],
  "properties": {
    "order_id": {"type": "string", "format": "uuid"},
    "user_id": {"type": "string", "format": "uuid"},
    "account_id": {"type": "string", "format": "uuid"},
    "strategy_id": {"type": "string", "format": "uuid", "nullable": true},
    "exchange_order_id": {"type": "string", "nullable": true},
    "client_order_id": {"type": "string", "nullable": true},
    "symbol": {"type": "string"},
    "side": {"type": "string", "enum": ["BUY", "SELL"]},
    "position_side": {"type": "string", "enum": ["LONG", "SHORT", "BOTH"], "nullable": true},
    "type": {"type": "string", "enum": ["MARKET", "LIMIT", "STOP_MARKET", "STOP_LIMIT", "TAKE_PROFIT"]},
    "quantity": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"},
    "price": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$", "nullable": true},
    "stop_price": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$", "nullable": true},
    "filled_quantity": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$", "default": "0"},
    "remaining_quantity": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"},
    "avg_fill_price": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$", "nullable": true},
    "commission": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$", "default": "0"},
    "commission_asset": {"type": "string", "nullable": true},
    "status": {"type": "string", "enum": ["PENDING", "NEW", "PARTIALLY_FILLED", "FILLED", "CANCELLED", "REJECTED"]},
    "time_in_force": {"type": "string", "enum": ["GTC", "IOC", "FOK"]},
    "reduce_only": {"type": "boolean"},
    "created_at": {"type": "string", "format": "date-time"},
    "updated_at": {"type": "string", "format": "date-time"},
    "filled_at": {"type": "string", "format": "date-time", "nullable": true},
    "fills": {
      "type": "array",
      "items": {
        "type": "object", 
        "properties": {
          "fill_id": {"type": "string", "format": "uuid"},
          "quantity": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"},
          "price": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"},
          "commission": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"},
          "timestamp": {"type": "string", "format": "date-time"}
        }
      }
    }
  }
}
```

### Portfolio Query API

#### GET /api/v1/portfolio/{user_id}
**Response Schema**:
```json
{
  "type": "object",
  "required": ["user_id", "total_balance_usd", "available_balance_usd", "positions", "summary", "updated_at"],
  "properties": {
    "user_id": {"type": "string", "format": "uuid"},
    "total_balance_usd": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"},
    "available_balance_usd": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"},
    "unrealized_pnl_usd": {"type": "string", "pattern": "^-?\\\\d+\\\\.?\\\\d{0,8}$"},
    "realized_pnl_usd": {"type": "string", "pattern": "^-?\\\\d+\\\\.?\\\\d{0,8}$"},
    "margin_balance_usd": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"},
    "maintenance_margin_usd": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"},
    "positions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["symbol", "side", "size", "entry_price", "mark_price", "unrealized_pnl"],
        "properties": {
          "symbol": {"type": "string"},
          "side": {"type": "string", "enum": ["LONG", "SHORT"]},
          "size": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"},
          "entry_price": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"},
          "mark_price": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"},
          "unrealized_pnl": {"type": "string", "pattern": "^-?\\\\d+\\\\.?\\\\d{0,8}$"},
          "unrealized_pnl_percent": {"type": "number"},
          "leverage": {"type": "number", "minimum": 1, "maximum": 125},
          "margin": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"},
          "liquidation_price": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$", "nullable": true}
        }
      }
    },
    "summary": {
      "type": "object",
      "properties": {
        "total_positions": {"type": "integer", "minimum": 0},
        "total_margin_used": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"},
        "margin_ratio": {"type": "number", "minimum": 0, "maximum": 1},
        "daily_pnl": {"type": "string", "pattern": "^-?\\\\d+\\\\.?\\\\d{0,8}$"},
        "daily_pnl_percent": {"type": "number"},
        "total_trading_volume_24h": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"}
      }
    },
    "accounts": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "account_id": {"type": "string", "format": "uuid"},
          "exchange": {"type": "string", "enum": ["BINANCE", "BYBIT"]},
          "account_name": {"type": "string"},
          "balance_usd": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"},
          "unrealized_pnl_usd": {"type": "string", "pattern": "^-?\\\\d+\\\\.?\\\\d{0,8}$"},
          "margin_ratio": {"type": "number"},
          "last_sync_at": {"type": "string", "format": "date-time"}
        }
      }
    },
    "updated_at": {"type": "string", "format": "date-time"}
  }
}
```

### Risk Management API

#### GET /api/v1/risk/metrics/{user_id}
**Response Schema**:
```json
{
  "type": "object",
  "required": ["user_id", "risk_score", "metrics", "violations", "calculated_at"],
  "properties": {
    "user_id": {"type": "string", "format": "uuid"},
    "risk_score": {
      "type": "number",
      "minimum": 0,
      "maximum": 100,
      "description": "Composite risk score (0=low risk, 100=high risk)"
    },
    "metrics": {
      "type": "object",
      "required": ["total_exposure", "leverage_ratio", "var_95", "max_drawdown"],
      "properties": {
        "total_exposure": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"},
        "leverage_ratio": {"type": "number", "minimum": 0},
        "var_95": {
          "type": "string",
          "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$",
          "description": "Value at Risk 95% confidence"
        },
        "max_drawdown": {
          "type": "string", 
          "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$",
          "description": "Maximum drawdown from peak"
        },
        "correlation_risk": {
          "type": "number",
          "minimum": -1,
          "maximum": 1,
          "description": "Portfolio correlation risk metric"
        },
        "margin_ratio": {
          "type": "number",
          "minimum": 0,
          "maximum": 1
        },
        "concentration_risk": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "Position concentration risk (0=diversified, 1=concentrated)"
        }
      }
    },
    "limits": {
      "type": "object",
      "properties": {
        "max_position_size": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"},
        "max_daily_loss": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"},
        "max_drawdown_percent": {"type": "number", "minimum": 0, "maximum": 100},
        "max_leverage": {"type": "number", "minimum": 1, "maximum": 125},
        "max_correlation": {"type": "number", "minimum": 0, "maximum": 1},
        "var_limit": {"type": "string", "pattern": "^\\\\d+\\\\.?\\\\d{0,8}$"}
      }
    },
    "violations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "violation_type": {"type": "string"},
          "severity": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
          "current_value": {"type": "number"},
          "limit_value": {"type": "number"},
          "detected_at": {"type": "string", "format": "date-time"}
        }
      }
    },
    "calculated_at": {"type": "string", "format": "date-time"}
  }
}
```

---

## 📡 WebSocket Message Schemas

### Market Data WebSocket

#### Connection URL
```
wss://api.patriot-trading.com/ws/market-data
```

#### Authentication Message
```json
{
  "type": "auth",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "timestamp": 1727206800000
}
```

#### Subscription Message
```json
{
  "type": "subscribe",
  "channels": [
    {
      "channel": "price_updates",
      "symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
    },
    {
      "channel": "orderbook", 
      "symbols": ["BTCUSDT"],
      "depth": 20
    }
  ]
}
```

#### Price Update Message (Server → Client)
```json
{
  "type": "price_update",
  "channel": "price_updates",
  "data": {
    "symbol": "BTCUSDT",
    "price": 65234.50,
    "bid": 65234.00,
    "ask": 65235.00,
    "volume_24h": 45678.123,
    "change_24h": 1.93,
    "timestamp": 1727206800000
  }
}
```

#### Order Book Update Message (Server → Client)
```json
{
  "type": "orderbook_update",
  "channel": "orderbook",
  "data": {
    "symbol": "BTCUSDT",
    "bids": [
      ["65234.00", "0.150"],
      ["65233.50", "0.250"],
      ["65233.00", "0.100"]
    ],
    "asks": [
      ["65235.00", "0.175"],
      ["65235.50", "0.200"],
      ["65236.00", "0.300"]
    ],
    "timestamp": 1727206800000
  }
}
```

### Account Data WebSocket

#### Connection URL (Authenticated)
```
wss://api.patriot-trading.com/ws/account/{user_id}
```

#### Portfolio Update Message (Server → Client)
```json
{
  "type": "portfolio_update",
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "account_id": "550e8400-e29b-41d4-a716-446655440005",
    "balance_change": {
      "total_balance_usd": "15750.25",
      "available_balance_usd": "12500.00",
      "unrealized_pnl_usd": "250.75"
    },
    "position_updates": [
      {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "size": "0.025",
        "entry_price": "64800.00",
        "mark_price": "65234.50",
        "unrealized_pnl": "10.86",
        "unrealized_pnl_percent": 0.67
      }
    ],
    "timestamp": 1727206800000
  }
}
```

#### Order Update Message (Server → Client)
```json
{
  "type": "order_update",
  "data": {
    "order_id": "550e8400-e29b-41d4-a716-446655440011",
    "status": "FILLED",
    "filled_quantity": "0.001",
    "avg_fill_price": "65000.00",
    "commission": "0.065",
    "commission_asset": "USDT",
    "updated_at": "2025-09-24T20:45:30Z"
  }
}
```

#### Risk Alert Message (Server → Client)
```json
{
  "type": "risk_alert",
  "data": {
    "alert_id": "550e8400-e29b-41d4-a716-446655440050",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "severity": "HIGH",
    "violation_type": "MAX_DRAWDOWN",
    "message": "Portfolio drawdown has exceeded 15% threshold",
    "current_value": 16.5,
    "limit_value": 15.0,
    "suggested_actions": [
      "Consider reducing position sizes",
      "Review stop-loss orders",
      "Contact risk management team"
    ],
    "timestamp": 1727206800000
  }
}
```

---

## 🗄️ Database Schema Definitions

### Core Tables

#### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(255),
    status user_status_enum DEFAULT 'ACTIVE' NOT NULL,
    risk_profile risk_profile_enum DEFAULT 'MEDIUM' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    -- Constraints
    CONSTRAINT users_telegram_id_positive CHECK (telegram_id > 0),
    CONSTRAINT users_username_length CHECK (char_length(username) >= 3),
    CONSTRAINT users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$' OR email IS NULL)
);

-- Indexes
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_created_at ON users(created_at);

-- Enums
CREATE TYPE user_status_enum AS ENUM ('ACTIVE', 'SUSPENDED', 'CLOSED');
CREATE TYPE risk_profile_enum AS ENUM ('LOW', 'MEDIUM', 'HIGH');
```

#### User Accounts Table
```sql
CREATE TABLE user_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    exchange exchange_enum NOT NULL,
    account_name VARCHAR(100) NOT NULL,
    encrypted_api_key TEXT NOT NULL,
    encrypted_api_secret TEXT NOT NULL,
    encrypted_passphrase TEXT,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_testnet BOOLEAN DEFAULT FALSE NOT NULL,
    last_sync_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    
    -- Constraints
    CONSTRAINT user_accounts_unique_name_per_user UNIQUE (user_id, account_name),
    CONSTRAINT user_accounts_api_key_not_empty CHECK (char_length(encrypted_api_key) > 0),
    CONSTRAINT user_accounts_api_secret_not_empty CHECK (char_length(encrypted_api_secret) > 0)
);

-- Indexes
CREATE INDEX idx_user_accounts_user_id ON user_accounts(user_id);
CREATE INDEX idx_user_accounts_exchange ON user_accounts(exchange);
CREATE INDEX idx_user_accounts_active ON user_accounts(is_active) WHERE is_active = TRUE;

-- Enums
CREATE TYPE exchange_enum AS ENUM ('BINANCE', 'BYBIT');
```

#### Orders Table
```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    account_id UUID REFERENCES user_accounts(id) ON DELETE CASCADE NOT NULL,
    strategy_id UUID REFERENCES strategies(id) ON DELETE SET NULL,
    exchange_order_id VARCHAR(255),
    client_order_id VARCHAR(255),
    symbol VARCHAR(20) NOT NULL,
    side order_side_enum NOT NULL,
    position_side position_side_enum,
    order_type order_type_enum NOT NULL,
    quantity DECIMAL(18,8) NOT NULL,
    price DECIMAL(18,8),
    stop_price DECIMAL(18,8),
    filled_quantity DECIMAL(18,8) DEFAULT 0 NOT NULL,
    avg_fill_price DECIMAL(18,8),
    commission DECIMAL(18,8) DEFAULT 0 NOT NULL,
    commission_asset VARCHAR(10),
    status order_status_enum DEFAULT 'PENDING' NOT NULL,
    time_in_force time_in_force_enum DEFAULT 'GTC' NOT NULL,
    reduce_only BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    filled_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT orders_quantity_positive CHECK (quantity > 0),
    CONSTRAINT orders_price_positive CHECK (price IS NULL OR price > 0),
    CONSTRAINT orders_stop_price_positive CHECK (stop_price IS NULL OR stop_price > 0),
    CONSTRAINT orders_filled_quantity_valid CHECK (filled_quantity >= 0 AND filled_quantity <= quantity),
    CONSTRAINT orders_avg_fill_price_positive CHECK (avg_fill_price IS NULL OR avg_fill_price > 0),
    CONSTRAINT orders_commission_non_negative CHECK (commission >= 0),
    CONSTRAINT orders_price_required_for_limit CHECK (
        (order_type IN ('LIMIT', 'STOP_LIMIT') AND price IS NOT NULL) OR 
        (order_type NOT IN ('LIMIT', 'STOP_LIMIT'))
    ),
    CONSTRAINT orders_stop_price_required_for_stop CHECK (
        (order_type IN ('STOP_MARKET', 'STOP_LIMIT', 'TAKE_PROFIT') AND stop_price IS NOT NULL) OR 
        (order_type NOT IN ('STOP_MARKET', 'STOP_LIMIT', 'TAKE_PROFIT'))
    )
);

-- Indexes
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_account_id ON orders(account_id);
CREATE INDEX idx_orders_strategy_id ON orders(strategy_id) WHERE strategy_id IS NOT NULL;
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_orders_exchange_order_id ON orders(exchange_order_id) WHERE exchange_order_id IS NOT NULL;

-- Composite indexes for common queries
CREATE INDEX idx_orders_user_status_created ON orders(user_id, status, created_at DESC);
CREATE INDEX idx_orders_account_symbol ON orders(account_id, symbol);

-- Enums
CREATE TYPE order_side_enum AS ENUM ('BUY', 'SELL');
CREATE TYPE position_side_enum AS ENUM ('LONG', 'SHORT', 'BOTH');
CREATE TYPE order_type_enum AS ENUM ('MARKET', 'LIMIT', 'STOP_MARKET', 'STOP_LIMIT', 'TAKE_PROFIT');
CREATE TYPE order_status_enum AS ENUM ('PENDING', 'NEW', 'PARTIALLY_FILLED', 'FILLED', 'CANCELLED', 'REJECTED');
CREATE TYPE time_in_force_enum AS ENUM ('GTC', 'IOC', 'FOK');
```

#### Event Store Table
```sql
CREATE TABLE event_store (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_id UUID NOT NULL,
    stream_type VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_version INTEGER NOT NULL,
    event_data JSONB NOT NULL,
    metadata JSONB DEFAULT '{}' NOT NULL,
    correlation_id UUID,
    causation_id UUID,
    occurred_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    processed_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT event_store_version_positive CHECK (event_version > 0),
    CONSTRAINT event_store_unique_stream_version UNIQUE (stream_id, event_version),
    CONSTRAINT event_store_event_data_not_empty CHECK (jsonb_typeof(event_data) = 'object')
);

-- Indexes
CREATE INDEX idx_event_store_stream_id ON event_store(stream_id);
CREATE INDEX idx_event_store_stream_type ON event_store(stream_type);
CREATE INDEX idx_event_store_event_type ON event_store(event_type);
CREATE INDEX idx_event_store_occurred_at ON event_store(occurred_at);
CREATE INDEX idx_event_store_correlation_id ON event_store(correlation_id) WHERE correlation_id IS NOT NULL;

-- Composite indexes for event replay
CREATE INDEX idx_event_store_stream_version ON event_store(stream_id, event_version);
CREATE INDEX idx_event_store_type_occurred ON event_store(stream_type, occurred_at);
```

### Time-Series Tables (TimescaleDB Hypertables)

#### Portfolio Snapshots
```sql
CREATE TABLE portfolio_snapshots (
    id UUID DEFAULT gen_random_uuid(),
    time TIMESTAMPTZ NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    account_id UUID REFERENCES user_accounts(id) ON DELETE CASCADE NOT NULL,
    total_balance_usd DECIMAL(18,2) NOT NULL,
    available_balance_usd DECIMAL(18,2) NOT NULL,
    unrealized_pnl_usd DECIMAL(18,2) DEFAULT 0 NOT NULL,
    realized_pnl_usd DECIMAL(18,2) DEFAULT 0 NOT NULL,
    margin_balance_usd DECIMAL(18,2) DEFAULT 0 NOT NULL,
    maintenance_margin_usd DECIMAL(18,2) DEFAULT 0 NOT NULL,
    position_count INTEGER DEFAULT 0 NOT NULL,
    total_position_value_usd DECIMAL(18,2) DEFAULT 0 NOT NULL,
    
    -- Constraints
    CONSTRAINT portfolio_snapshots_balances_non_negative CHECK (
        total_balance_usd >= 0 AND 
        available_balance_usd >= 0 AND 
        margin_balance_usd >= 0 AND 
        maintenance_margin_usd >= 0
    ),
    CONSTRAINT portfolio_snapshots_position_count_non_negative CHECK (position_count >= 0)
);

-- Convert to hypertable (partitioned by time and user_id)
SELECT create_hypertable('portfolio_snapshots', 'time', 'user_id', 4);

-- Indexes on hypertable
CREATE INDEX idx_portfolio_snapshots_user_time ON portfolio_snapshots(user_id, time DESC);
CREATE INDEX idx_portfolio_snapshots_account_time ON portfolio_snapshots(account_id, time DESC);

-- Compression policy for old data (compress data older than 7 days)
ALTER TABLE portfolio_snapshots SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'user_id,account_id'
);

SELECT add_compression_policy('portfolio_snapshots', INTERVAL '7 days');

-- Retention policy (keep data for 2 years)
SELECT add_retention_policy('portfolio_snapshots', INTERVAL '2 years');
```

#### Performance Metrics
```sql
CREATE TABLE performance_metrics (
    id UUID DEFAULT gen_random_uuid(),
    time TIMESTAMPTZ NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
    account_id UUID REFERENCES user_accounts(id) ON DELETE CASCADE NOT NULL,
    period_type period_type_enum NOT NULL,
    total_trades INTEGER DEFAULT 0 NOT NULL,
    winning_trades INTEGER DEFAULT 0 NOT NULL,
    losing_trades INTEGER DEFAULT 0 NOT NULL,
    total_pnl_usd DECIMAL(18,2) DEFAULT 0 NOT NULL,
    win_rate DECIMAL(5,4),
    profit_factor DECIMAL(10,4),
    max_drawdown_usd DECIMAL(18,2),
    max_drawdown_percent DECIMAL(5,4),
    sharpe_ratio DECIMAL(10,6),
    sortino_ratio DECIMAL(10,6),
    calmar_ratio DECIMAL(10,6),
    allocated_balance_usd DECIMAL(18,2),
    
    -- Constraints
    CONSTRAINT performance_metrics_trades_valid CHECK (
        total_trades >= 0 AND 
        winning_trades >= 0 AND 
        losing_trades >= 0 AND
        winning_trades + losing_trades <= total_trades
    ),
    CONSTRAINT performance_metrics_win_rate_valid CHECK (
        win_rate IS NULL OR (win_rate >= 0 AND win_rate <= 1)
    ),
    CONSTRAINT performance_metrics_drawdown_percent_valid CHECK (
        max_drawdown_percent IS NULL OR (max_drawdown_percent >= 0 AND max_drawdown_percent <= 1)
    )
);

-- Convert to hypertable
SELECT create_hypertable('performance_metrics', 'time', 'user_id', 4);

-- Indexes
CREATE INDEX idx_performance_metrics_user_time ON performance_metrics(user_id, time DESC);
CREATE INDEX idx_performance_metrics_strategy_time ON performance_metrics(strategy_id, time DESC) WHERE strategy_id IS NOT NULL;

-- Enums
CREATE TYPE period_type_enum AS ENUM ('HOURLY', 'DAILY', 'WEEKLY', 'MONTHLY');
```

#### Risk Metrics History
```sql
CREATE TABLE risk_metrics_history (
    id UUID DEFAULT gen_random_uuid(),
    time TIMESTAMPTZ NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    account_id UUID REFERENCES user_accounts(id) ON DELETE CASCADE NOT NULL,
    total_exposure_usd DECIMAL(18,2) NOT NULL,
    leverage_ratio DECIMAL(10,4) DEFAULT 1 NOT NULL,
    var_95_usd DECIMAL(18,2),
    var_99_usd DECIMAL(18,2),
    max_drawdown_usd DECIMAL(18,2),
    correlation_risk DECIMAL(6,4),
    concentration_risk DECIMAL(6,4),
    margin_ratio DECIMAL(6,4),
    risk_score DECIMAL(5,2),
    
    -- Constraints
    CONSTRAINT risk_metrics_exposure_non_negative CHECK (total_exposure_usd >= 0),
    CONSTRAINT risk_metrics_leverage_positive CHECK (leverage_ratio >= 1),
    CONSTRAINT risk_metrics_correlation_valid CHECK (
        correlation_risk IS NULL OR (correlation_risk >= -1 AND correlation_risk <= 1)
    ),
    CONSTRAINT risk_metrics_concentration_valid CHECK (
        concentration_risk IS NULL OR (concentration_risk >= 0 AND concentration_risk <= 1)
    ),
    CONSTRAINT risk_metrics_margin_ratio_valid CHECK (
        margin_ratio IS NULL OR (margin_ratio >= 0 AND margin_ratio <= 1)
    ),
    CONSTRAINT risk_metrics_score_valid CHECK (
        risk_score IS NULL OR (risk_score >= 0 AND risk_score <= 100)
    )
);

-- Convert to hypertable
SELECT create_hypertable('risk_metrics_history', 'time', 'user_id', 4);

-- Indexes
CREATE INDEX idx_risk_metrics_history_user_time ON risk_metrics_history(user_id, time DESC);
CREATE INDEX idx_risk_metrics_history_account_time ON risk_metrics_history(account_id, time DESC);
```

---

## 🔗 Schema Validation and Versioning

### Schema Versioning Strategy

#### Version Format
**Pattern**: `v{major}.{minor}`  
**Example**: `v1.0`, `v1.1`, `v2.0`  

#### Versioning Rules
- **Major version bump**: Breaking changes to existing schemas
- **Minor version bump**: Backward-compatible additions
- **Schema evolution**: Gradual migration with backward compatibility

#### Schema Registry Configuration
```yaml
# Kafka Schema Registry configuration
schema_registry:
  url: "http://schema-registry:8081"
  subjects:
    user-events-value:
      compatibility: "BACKWARD"
      version_strategy: "SEQUENTIAL"
    trading-events-value:
      compatibility: "BACKWARD" 
      version_strategy: "SEQUENTIAL"
    market-data-prices-value:
      compatibility: "FORWARD"
      version_strategy: "SEQUENTIAL"
```

### Data Validation Examples

#### Python Validation (Pydantic)
```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from enum import Enum

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    STOP_LIMIT = "STOP_LIMIT"

class OrderCreatedEventData(BaseModel):
    order_id: str = Field(..., regex=r'^[0-9a-f-]{36}$')
    user_id: str = Field(..., regex=r'^[0-9a-f-]{36}$')
    account_id: str = Field(..., regex=r'^[0-9a-f-]{36}$')
    strategy_id: Optional[str] = Field(None, regex=r'^[0-9a-f-]{36}$')
    symbol: str = Field(..., regex=r'^[A-Z]{3,10}USDT$')
    side: OrderSide
    type: OrderType
    quantity: Decimal = Field(..., gt=0, decimal_places=8)
    price: Optional[Decimal] = Field(None, gt=0, decimal_places=8)
    stop_price: Optional[Decimal] = Field(None, gt=0, decimal_places=8)
    status: str = Field(..., regex=r'^(PENDING|NEW|PARTIALLY_FILLED|FILLED|CANCELLED|REJECTED)$')
    created_at: datetime
    
    @validator('price')
    def price_required_for_limit_orders(cls, v, values):
        if values.get('type') in ['LIMIT', 'STOP_LIMIT'] and v is None:
            raise ValueError('Price required for LIMIT and STOP_LIMIT orders')
        return v
    
    @validator('stop_price')
    def stop_price_required_for_stop_orders(cls, v, values):
        if values.get('type') in ['STOP_MARKET', 'STOP_LIMIT'] and v is None:
            raise ValueError('Stop price required for STOP orders')
        return v

class OrderCreatedEvent(BaseModel):
    event_id: str = Field(..., regex=r'^[0-9a-f-]{36}$')
    event_type: str = Field("order.created", const=True)
    stream_id: str = Field(..., regex=r'^[0-9a-f-]{36}$')
    event_version: int = Field(..., ge=1)
    correlation_id: Optional[str] = Field(None, regex=r'^[0-9a-f-]{36}$')
    occurred_at: datetime
    data: OrderCreatedEventData
```

#### JSON Schema Validation (Node.js)
```javascript
const Ajv = require('ajv');
const addFormats = require('ajv-formats');

const ajv = new Ajv();
addFormats(ajv);

const orderCreatedSchema = {
  type: "object",
  required: ["event_id", "event_type", "stream_id", "occurred_at", "data"],
  properties: {
    event_id: { type: "string", format: "uuid" },
    event_type: { type: "string", enum: ["order.created"] },
    stream_id: { type: "string", format: "uuid" },
    event_version: { type: "integer", minimum: 1 },
    correlation_id: { type: "string", format: "uuid" },
    occurred_at: { type: "string", format: "date-time" },
    data: {
      type: "object",
      required: ["order_id", "user_id", "account_id", "symbol", "side", "type", "quantity", "status"],
      properties: {
        order_id: { type: "string", format: "uuid" },
        user_id: { type: "string", format: "uuid" },
        account_id: { type: "string", format: "uuid" },
        strategy_id: { type: "string", format: "uuid" },
        symbol: { type: "string", pattern: "^[A-Z]{3,10}USDT$" },
        side: { type: "string", enum: ["BUY", "SELL"] },
        type: { type: "string", enum: ["MARKET", "LIMIT", "STOP_MARKET", "STOP_LIMIT"] },
        quantity: { type: "string", pattern: "^\\\\d+\\\\.?\\\\d{0,8}$" },
        price: { type: "string", pattern: "^\\\\d+\\\\.?\\\\d{0,8}$" },
        status: { type: "string", pattern: "^(PENDING|NEW|PARTIALLY_FILLED|FILLED|CANCELLED|REJECTED)$" },
        created_at: { type: "string", format: "date-time" }
      }
    }
  }
};

const validateOrderCreated = ajv.compile(orderCreatedSchema);

// Usage example
function validateAndProcessOrderEvent(eventData) {
  const isValid = validateOrderCreated(eventData);
  
  if (!isValid) {
    console.error('Schema validation failed:', validateOrderCreated.errors);
    throw new Error('Invalid order created event schema');
  }
  
  // Process validated event
  return processOrderCreatedEvent(eventData);
}
```

---

## 📋 Error Response Schemas

### Standard Error Response
```json
{
  "type": "object",
  "required": ["error", "message", "timestamp"],
  "properties": {
    "error": {
      "type": "object",
      "required": ["code", "type"],
      "properties": {
        "code": {
          "type": "string",
          "description": "Machine-readable error code"
        },
        "type": {
          "type": "string",
          "enum": ["ValidationError", "BusinessLogicError", "SystemError", "ExternalServiceError"],
          "description": "Error category"
        },
        "details": {
          "type": "object",
          "description": "Additional error-specific information"
        }
      }
    },
    "message": {
      "type": "string",
      "description": "Human-readable error message"
    },
    "request_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique request identifier for debugging"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "Error occurrence timestamp"
    }
  }
}
```

### Validation Error Response
```json
{
  "type": "object",
  "allOf": [{"$ref": "#/components/schemas/ErrorResponse"}],
  "properties": {
    "error": {
      "type": "object",
      "properties": {
        "code": {"type": "string", "enum": ["VALIDATION_ERROR"]},
        "type": {"type": "string", "enum": ["ValidationError"]},
        "details": {
          "type": "object",
          "properties": {
            "field_errors": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "field": {"type": "string"},
                  "message": {"type": "string"},
                  "invalid_value": {"type": "string"},
                  "constraint": {"type": "string"}
                }
              }
            }
          }
        }
      }
    }
  },
  "example": {
    "error": {
      "code": "VALIDATION_ERROR",
      "type": "ValidationError",
      "details": {
        "field_errors": [
          {
            "field": "quantity",
            "message": "Quantity must be greater than 0",
            "invalid_value": "-0.001",
            "constraint": "gt=0"
          },
          {
            "field": "symbol",
            "message": "Symbol must match pattern ^[A-Z]{3,10}USDT$",
            "invalid_value": "btcusdt",
            "constraint": "pattern"
          }
        ]
      }
    },
    "message": "Request validation failed",
    "request_id": "550e8400-e29b-41d4-a716-446655440999",
    "timestamp": "2025-09-24T20:50:00Z"
  }
}
```

### Business Logic Error Response
```json
{
  "example": {
    "error": {
      "code": "INSUFFICIENT_BALANCE",
      "type": "BusinessLogicError",
      "details": {
        "required_balance": "1000.00",
        "available_balance": "750.50",
        "currency": "USDT"
      }
    },
    "message": "Insufficient balance to place order",
    "request_id": "550e8400-e29b-41d4-a716-446655440999",
    "timestamp": "2025-09-24T20:50:00Z"
  }
}
```

---

## 🧪 Schema Testing Examples

### Unit Test for Schema Validation
```python
import pytest
from pydantic import ValidationError
from decimal import Decimal
from datetime import datetime
from schemas.events import OrderCreatedEvent, OrderCreatedEventData

def test_order_created_event_valid():
    """Test valid order created event schema"""
    event_data = {
        "event_id": "550e8400-e29b-41d4-a716-446655440010",
        "event_type": "order.created",
        "stream_id": "550e8400-e29b-41d4-a716-446655440011", 
        "event_version": 1,
        "correlation_id": "550e8400-e29b-41d4-a716-446655440012",
        "occurred_at": datetime.utcnow(),
        "data": {
            "order_id": "550e8400-e29b-41d4-a716-446655440011",
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "account_id": "550e8400-e29b-41d4-a716-446655440005",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "LIMIT",
            "quantity": Decimal("0.001"),
            "price": Decimal("65000.00"),
            "status": "PENDING",
            "created_at": datetime.utcnow()
        }
    }
    
    # Should not raise validation error
    event = OrderCreatedEvent(**event_data)
    assert event.event_type == "order.created"
    assert event.data.quantity == Decimal("0.001")

def test_order_created_event_invalid_symbol():
    """Test order created event with invalid symbol"""
    event_data = {
        "event_id": "550e8400-e29b-41d4-a716-446655440010",
        "event_type": "order.created",
        "stream_id": "550e8400-e29b-41d4-a716-446655440011",
        "event_version": 1,
        "occurred_at": datetime.utcnow(),
        "data": {
            "order_id": "550e8400-e29b-41d4-a716-446655440011",
            "user_id": "550e8400-e29b-41d4-a716-446655440000", 
            "account_id": "550e8400-e29b-41d4-a716-446655440005",
            "symbol": "btcusdt",  # Invalid: lowercase
            "side": "BUY",
            "type": "LIMIT", 
            "quantity": Decimal("0.001"),
            "price": Decimal("65000.00"),
            "status": "PENDING",
            "created_at": datetime.utcnow()
        }
    }
    
    with pytest.raises(ValidationError) as exc_info:
        OrderCreatedEvent(**event_data)
    
    assert "symbol" in str(exc_info.value)

def test_order_created_event_missing_price_for_limit():
    """Test limit order without required price"""
    event_data = {
        "event_id": "550e8400-e29b-41d4-a716-446655440010",
        "event_type": "order.created", 
        "stream_id": "550e8400-e29b-41d4-a716-446655440011",
        "event_version": 1,
        "occurred_at": datetime.utcnow(),
        "data": {
            "order_id": "550e8400-e29b-41d4-a716-446655440011",
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "account_id": "550e8400-e29b-41d4-a716-446655440005",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "LIMIT",
            "quantity": Decimal("0.001"),
            # price missing for LIMIT order
            "status": "PENDING",
            "created_at": datetime.utcnow()
        }
    }
    
    with pytest.raises(ValidationError) as exc_info:
        OrderCreatedEvent(**event_data)
    
    assert "Price required for LIMIT" in str(exc_info.value)
```

### Integration Test for Kafka Schema Registry
```python
import pytest
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.json_schema import JSONSerializer
import json

@pytest.fixture
def schema_registry_client():
    return SchemaRegistryClient({'url': 'http://localhost:8081'})

@pytest.fixture  
def order_created_serializer(schema_registry_client):
    with open('schemas/order_created_event.json', 'r') as f:
        schema_str = f.read()
    
    return JSONSerializer(
        schema_str,
        schema_registry_client,
        to_dict=lambda obj, ctx: obj if isinstance(obj, dict) else obj.__dict__
    )

def test_kafka_schema_registry_serialization(order_created_serializer):
    """Test serialization with Kafka Schema Registry"""
    
    event_data = {
        "event_id": "550e8400-e29b-41d4-a716-446655440010",
        "event_type": "order.created",
        "stream_id": "550e8400-e29b-41d4-a716-446655440011",
        "event_version": 1,
        "occurred_at": "2025-09-24T20:40:00Z",
        "data": {
            "order_id": "550e8400-e29b-41d4-a716-446655440011",
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "account_id": "550e8400-e29b-41d4-a716-446655440005",
            "symbol": "BTCUSDT",
            "side": "BUY", 
            "type": "LIMIT",
            "quantity": "0.001",
            "price": "65000.00",
            "status": "PENDING",
            "created_at": "2025-09-24T20:40:00Z"
        }
    }
    
    # Should serialize without error
    serialized_data = order_created_serializer(event_data, None)
    assert serialized_data is not None
    assert len(serialized_data) > 0
```

---

## 📖 Schema Documentation Standards

### Schema Documentation Template
```yaml
# Template for documenting new schemas
schema_name: "order.created"
version: "v1.0"
category: "trading-events"
description: "Event published when a new trading order is created by a user"

fields:
  event_id:
    type: "string (UUID)"
    required: true
    description: "Unique identifier for this event instance"
    example: "550e8400-e29b-41d4-a716-446655440010"
    
  data.symbol:
    type: "string"
    required: true
    pattern: "^[A-Z]{3,10}USDT$"
    description: "Trading pair symbol (must end with USDT)"
    example: "BTCUSDT"
    validation_rules:
      - "Must be uppercase"
      - "Must end with USDT"
      - "Base currency 3-10 characters"

usage_examples:
  - name: "Basic limit order"
    description: "Standard limit order creation"
    example: |
      {
        "event_id": "550e8400-e29b-41d4-a716-446655440010",
        "event_type": "order.created",
        "data": {
          "symbol": "BTCUSDT",
          "side": "BUY", 
          "type": "LIMIT",
          "quantity": "0.001",
          "price": "65000.00"
        }
      }

compatibility:
  backward_compatible: true
  forward_compatible: false
  breaking_changes: []

related_schemas:
  - "order.filled"
  - "order.cancelled" 
  - "order.modified"

producers:
  - "Order Command Service"
  
consumers:
  - "Order Lifecycle Service"
  - "Portfolio Query Service"
  - "Risk Engine"
  - "Analytics Service"
```

### Change Log Format
```yaml
# Schema change log example
schema: "order.created"

versions:
  v1.1:
    date: "2025-10-15"
    changes:
      - type: "addition"
        field: "data.client_order_id"
        description: "Added optional client-provided order ID"
        backward_compatible: true
      - type: "addition"
        field: "data.reduce_only"
        description: "Added reduce-only flag for position management"
        backward_compatible: true
        
  v1.0:
    date: "2025-09-24"
    changes:
      - type: "initial"
        description: "Initial schema definition for order created events"

migration_notes:
  v1.0_to_v1.1:
    - "New fields are optional and have default values"
    - "Existing consumers will continue to work without changes"
    - "New consumers should handle new fields appropriately"
```

---

## ✅ Schema Validation Checklist

### Pre-deployment Validation
```yaml
Schema Review Checklist:
  Documentation:
    - [ ] Schema purpose and usage clearly documented
    - [ ] All required fields documented with examples
    - [ ] Validation rules and constraints specified
    - [ ] Breaking changes identified and documented
    
  Technical Validation:
    - [ ] Schema syntax validated with JSON Schema validator
    - [ ] All examples validate against schema
    - [ ] Backward compatibility verified
    - [ ] Performance impact assessed
    
  Integration Testing:
    - [ ] Producer integration tested
    - [ ] Consumer integration tested  
    - [ ] Schema registry integration verified
    - [ ] Error handling scenarios tested
    
  Business Validation:
    - [ ] Business requirements satisfied
    - [ ] Edge cases identified and handled
    - [ ] Data privacy requirements met
    - [ ] Audit requirements satisfied
```

### Post-deployment Monitoring
```yaml
Schema Health Metrics:
  - Schema validation success rate (target: >99.9%)
  - Schema evolution compatibility (no breaking changes)
  - Consumer lag due to schema processing
  - Error rates by schema version
  
Alerting Rules:
  - Alert if validation failure rate >0.1%
  - Alert on incompatible schema changes
  - Alert on consumer processing delays
  - Alert on schema registry connectivity issues
```

---

> **Schema Management Best Practices:**
> 1. **Version Control**: All schemas stored in Git with proper versioning
> 2. **Testing**: Comprehensive unit and integration testing for all schemas
> 3. **Documentation**: Clear documentation with examples and usage guidelines  
> 4. **Backward Compatibility**: Maintain backward compatibility for minor versions
> 5. **Monitoring**: Continuous monitoring of schema usage and validation metrics

> **Next Steps:**
> 1. Implement schema validation in all services
> 2. Set up Kafka Schema Registry for production
> 3. Create automated schema testing pipeline
> 4. Establish schema governance processes
> 5. Train development team on schema best practices
