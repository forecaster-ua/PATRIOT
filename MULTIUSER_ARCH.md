# This is a multi-user architecture for a trading bot system.

```mermaid
erDiagram
    %% Пользователи и их роли (Admin, Manager, Trader)
    USERS {
        UUID id PK
        String username
        String email
        String full_name
        String role
        String status
        DateTime created_at
        DateTime updated_at
    }

    EXCHANGES {
        UUID id PK
        String name
        String api_base_url
        DateTime created_at
    }

    USER_ACCOUNTS {
        UUID id PK
        UUID user_id FK
        UUID exchange_id FK
        String account_name
        String status
        DateTime created_at
    }

    API_KEYS {
        UUID id PK
        UUID account_id FK
        String api_key_encrypted
        String secret_encrypted
        String status
        DateTime created_at
    }

    USER_SETTINGS {
        UUID id PK
        UUID user_id FK
        Float risk_per_trade
        Int min_leverage
        Int max_leverage
        DateTime created_at
    }

    TELEGRAM_ACCOUNTS {
        UUID id PK
        UUID user_id FK
        String chat_id
        Boolean is_active
        DateTime created_at
    }

    SIGNALS {
        UUID id PK
        UUID user_id FK
        String source
        String symbol
        String timeframe
        JSON   payload
        DateTime created_at
    }

    ORDERS {
        UUID id PK
        UUID user_id FK
        UUID account_id FK
        UUID signal_id FK
        String exchange_order_id
        String client_order_id
        String symbol
        String side
        String type
        Float quantity
        Float price
        Float stop_loss
        Float take_profit
        String status
        DateTime created_at
        DateTime updated_at
    }

    POSITIONS {
        UUID id PK
        UUID user_id FK
        UUID account_id FK
        String symbol
        Float entry_price
        Float quantity
        Int leverage
        String margin_type
        String status
        DateTime open_time
        DateTime close_time
    }

    AUDIT_LOGS {
        UUID id PK
        UUID user_id FK
        String action
        String entity
        UUID   entity_id
        String description
        DateTime timestamp
    }

    SYNC_LOGS {
        UUID id PK
        UUID user_id FK
        UUID account_id FK
        String action
        String entity
        JSON   details
        DateTime timestamp
    }

    %% Связи %%
    USERS ||--o{ USER_ACCOUNTS : has
    EXCHANGES ||--o{ USER_ACCOUNTS : provides
    USER_ACCOUNTS ||--o{ API_KEYS : owns
    USERS ||--o{ USER_SETTINGS : configures
    USERS ||--o{ TELEGRAM_ACCOUNTS : uses
    USERS ||--o{ SIGNALS : generates
    USERS ||--o{ ORDERS : places
    USER_ACCOUNTS ||--o{ ORDERS : executes
    SIGNALS ||--o{ ORDERS : triggers
    USERS ||--o{ POSITIONS : holds
    USER_ACCOUNTS ||--o{ POSITIONS : holds
    USERS ||--o{ AUDIT_LOGS : logs
    USERS ||--o{ SYNC_LOGS : logs
