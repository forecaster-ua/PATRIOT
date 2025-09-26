# PATRIOT Trading System - Individual Service APIs

## 📋 Service API Directory

This directory contains detailed API specifications for each microservice in the PATRIOT trading system.

### Command Services (CQRS Write Operations)
- **[User Command Service API](USER-COMMAND-SERVICE-API.md)** - User registration, profile management, account linking
- **[Order Command Service API](ORDER-COMMAND-SERVICE-API.md)** - Order creation, modification, cancellation

### Query Services (CQRS Read Operations)  
- **[User Query Service API](USER-QUERY-SERVICE-API.md)** - User profile queries, account information, activity history
- **[Portfolio Query Service API](PORTFOLIO-QUERY-SERVICE-API.md)** - Portfolio overview, position queries, performance metrics

### Domain Services (Business Logic)
- **[Strategy Engine API](STRATEGY-ENGINE-API.md)** - Strategy management, signal generation, performance tracking
- **[Risk Engine API](RISK-ENGINE-API.md)** - Risk assessment, portfolio risk, violation monitoring
- **[Trading Engine API](TRADING-ENGINE-API.md)** - Trade execution, signal processing, position management
- **[Order Lifecycle Service API](ORDER-LIFECYCLE-SERVICE-API.md)** - Order monitoring, status tracking, administrative controls

### Data Services (External Integration)
- **[Market Data Service API](MARKET-DATA-SERVICE-API.md)** - Market data queries, WebSocket subscriptions, historical data
- **[Account Data Service API](ACCOUNT-DATA-SERVICE-API.md)** - Account synchronization, balance updates, position tracking
- **[Exchange Adapters API](EXCHANGE-ADAPTERS-API.md)** - Unified exchange interface, rate limiting, error handling

### Infrastructure Services
- **[Authentication Service API](AUTHENTICATION-SERVICE-API.md)** - Authentication endpoints, token management, role management

### Common Resources
- **[Common API Patterns](COMMON-PATTERNS.md)** - Shared patterns, standards, and conventions used across all APIs

---

## 📖 Navigation

**[← Back to API Overview](../ANNEX-E-API-OVERVIEW.md)** | **[System Architecture](../../02-SYSTEM-ARCHITECTURE.md)** | **[Component Specs](../../03-COMPONENT-SPECIFICATIONS.md)**

---

> **💡 Usage Tip**: Each service API document follows the same structure for consistency. Start with the service you need, then refer to Common Patterns for implementation details.
