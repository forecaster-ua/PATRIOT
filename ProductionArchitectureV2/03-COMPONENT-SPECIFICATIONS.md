# PATRIOT Trading System - Component Specifications

## 📋 Document Information

**Document ID**: 03-COMPONENT-SPECIFICATIONS  
**Version**: 2.0  
**Date**: September 2025  
**Authors**: Solution Architecture Team  
**Status**: Draft  

> **Cross-References:**  
> - System Requirements: [01-SYSTEM-REQUIREMENTS.md](01-SYSTEM-REQUIREMENTS.md)  
> - System Architecture: [02-SYSTEM-ARCHITECTURE.md](02-SYSTEM-ARCHITECTURE.md)  
> - Database Design: [annexes/ANNEX-B-DATABASE-DESIGN.md](annexes/ANNEX-B-DATABASE-DESIGN.md)  
> - Data Schemas: [annexes/ANNEX-A-DATA-SCHEMAS.md](annexes/ANNEX-A-DATA-SCHEMAS.md)  
> - **API Documentation**: [annexes/ANNEX-E-API-OVERVIEW.md](annexes/ANNEX-E-API-OVERVIEW.md) | [Service APIs](annexes/api/)

---

## 🏗️ Component Overview

This document provides detailed specifications for all system components, including their responsibilities, interfaces, dependencies, and implementation requirements. Components are organized by domain following Domain-Driven Design principles.

### Component Categories

**Command Services (CQRS Write Side)**:
- User Command Service
- Account Command Service  
- Order Command Service
- Strategy Command Service

**Query Services (CQRS Read Side)**:
- User Query Service
- Portfolio Query Service
- Risk Query Service
- Analytics Query Service

**Domain Services**:
- Trading Engine
- Risk Engine
- Strategy Engine
- Order Lifecycle Service

**Data Services**:
- Market Data Service
- Account Data Service
- Exchange Adapters

**Infrastructure Services**:
- Authentication Service
- Event Store Service
- Audit Service

---

## 👤 User Management Domain

### User Command Service

#### Service Overview
**Component ID**: COMP-001  
**Service Type**: Command Service (CQRS Write)  
**Deployment**: Stateless, horizontally scalable  
**Primary Port**: 8001  

**Primary Responsibilities**:
- User registration and profile management
- Telegram account linking and verification
- Account status management (active, suspended, closed)
- Authentication credential management
- User preference and setting management

#### API Specifications

**REST API Endpoints**:
```yaml
POST /api/v1/users/register:
  summary: "Register new user account"
  request_body:
    telegram_id: integer
    username: string
    email: string (optional)
    risk_profile: enum [LOW, MEDIUM, HIGH]
  responses:
    201:
      user_id: UUID
      status: string
    400: "Validation errors"
    409: "User already exists"

PUT /api/v1/users/{user_id}/profile:
  summary: "Update user profile information"
  parameters:
    user_id: UUID (path)
  request_body:
    username: string (optional)
    email: string (optional)
    risk_profile: enum (optional)
  responses:
    200: "Profile updated"
    404: "User not found"

POST /api/v1/users/{user_id}/accounts/link:
  summary: "Link exchange account to user"
  parameters:
    user_id: UUID (path)
  request_body:
    exchange: enum [BINANCE, BYBIT]
    account_name: string
    api_key: string
    api_secret: string
    passphrase: string (optional)
  responses:
    201:
      account_id: UUID
      status: string
    400: "Invalid credentials"
```

#### Event Production

**Events Published**:
```yaml
user.registered:
  topic: "user-events"
  partition_key: user_id
  data:
    user_id: UUID
    telegram_id: integer
    username: string
    email: string
    risk_profile: string
    created_at: datetime

user.updated:
  topic: "user-events"  
  partition_key: user_id
  data:
    user_id: UUID
    changes: object
    updated_at: datetime

user.status_changed:
  topic: "user-events"
  partition_key: user_id
  data:
    user_id: UUID
    previous_status: string
    new_status: string
    reason: string
    changed_at: datetime

account.linked:
  topic: "user-events"
  partition_key: user_id
  data:
    user_id: UUID
    account_id: UUID
    exchange: string
    account_name: string
    linked_at: datetime
```

#### Business Rules

**User Registration Rules**:
- Telegram ID must be unique across the system
- Username must be between 3-50 characters
- Email must be valid format if provided
- Default risk profile is MEDIUM if not specified

**Account Linking Rules**:
- API credentials must be validated before storage
- Maximum 5 exchange accounts per user
- API keys encrypted with AES-256 before database storage
- Account names must be unique per user

#### Dependencies

**External Services**:
- **Authentication Service**: JWT token validation
- **Encryption Service**: API key encryption/decryption
- **Telegram API**: User verification and bot integration
- **Exchange APIs**: Credential validation

**Database Access**:
- **Write Database**: PostgreSQL primary for user data
- **Event Store**: Event persistence for audit trail

**Infrastructure Dependencies**:
- **Kafka Producer**: Event publication
- **Redis**: Session storage and caching
- **Logging Service**: Structured logging

#### Error Handling

**Error Categories**:
```python
class UserCommandErrors:
    VALIDATION_ERROR = "USER_VALIDATION_ERROR"
    DUPLICATE_USER = "USER_ALREADY_EXISTS"
    INVALID_CREDENTIALS = "INVALID_API_CREDENTIALS"
    ENCRYPTION_FAILURE = "CREDENTIAL_ENCRYPTION_FAILED"
    TELEGRAM_VERIFICATION_FAILED = "TELEGRAM_VERIFICATION_FAILED"
```

**Retry Policies**:
- Database operations: 3 retries with exponential backoff
- External API calls: 5 retries with jitter
- Event publishing: Infinite retries with dead letter queue

#### Performance Requirements

**Response Time Targets**:
- User registration: < 500ms (95th percentile)
- Profile updates: < 200ms (95th percentile)  
- Account linking: < 1000ms (95th percentile)

**Throughput Targets**:
- 100 user registrations per minute
- 1000 profile updates per minute
- 50 account linking operations per minute

---

### User Query Service

#### Service Overview
**Component ID**: COMP-002  
**Service Type**: Query Service (CQRS Read)  
**Deployment**: Stateless, horizontally scalable  
**Primary Port**: 8002

**Primary Responsibilities**:
- User profile information retrieval
- Account listing and status queries
- User activity history and audit trail
- Authentication status validation
- User preference and setting queries

#### API Specifications

**REST API Endpoints**:
```yaml
GET /api/v1/users/{user_id}/profile:
  summary: "Get user profile information"
  parameters:
    user_id: UUID (path)
  responses:
    200:
      user_id: UUID
      telegram_id: integer
      username: string
      email: string
      risk_profile: string
      status: string
      created_at: datetime
      last_login_at: datetime
    404: "User not found"

GET /api/v1/users/{user_id}/accounts:
  summary: "List user's exchange accounts"
  parameters:
    user_id: UUID (path)
    status: string (query, optional)
    exchange: string (query, optional)
  responses:
    200:
      accounts:
        - account_id: UUID
          account_name: string
          exchange: string
          status: string
          last_sync_at: datetime
          created_at: datetime
    404: "User not found"

GET /api/v1/users/{user_id}/activity:
  summary: "Get user activity history"
  parameters:
    user_id: UUID (path)
    limit: integer (query, default: 50)
    offset: integer (query, default: 0)
    activity_type: string (query, optional)
  responses:
    200:
      activities:
        - activity_id: UUID
          activity_type: string
          description: string
          metadata: object
          occurred_at: datetime
      total_count: integer
      has_more: boolean

GET /api/v1/users/search:
  summary: "Search users (admin only)"
  parameters:
    query: string (query)
    status: string (query, optional)
    limit: integer (query, default: 20)
  responses:
    200:
      users:
        - user_id: UUID
          username: string
          telegram_id: integer
          status: string
          created_at: datetime
      total_count: integer
```

#### Event Consumption

**Events Consumed**:
```yaml
user.registered:
  action: "Create user read model"
  handler: "create_user_projection"

user.updated:
  action: "Update user read model"
  handler: "update_user_projection"

user.status_changed:
  action: "Update user status in read model"
  handler: "update_user_status_projection"

account.linked:
  action: "Add account to user's account list"
  handler: "create_account_projection"

account.unlinked:
  action: "Remove account from user's account list"
  handler: "remove_account_projection"
```

#### Data Sources

**Primary Data Sources**:
- **PostgreSQL Read Replicas**: User profile and account data
- **Redis Cache**: Frequently accessed user data and sessions
- **Event Store**: Historical activity and audit trail
- **TimescaleDB**: User activity metrics and analytics

**Caching Strategy**:
```python
class UserQueryCaching:
    """User query service caching strategy"""
    
    USER_PROFILE_TTL = 300      # 5 minutes
    USER_ACCOUNTS_TTL = 60      # 1 minute
    USER_ACTIVITY_TTL = 180     # 3 minutes
    SEARCH_RESULTS_TTL = 30     # 30 seconds
    
    @cache(key="user:profile:{user_id}", ttl=USER_PROFILE_TTL)
    async def get_user_profile(self, user_id: UUID):
        """Cached user profile retrieval"""
        pass
```

#### Performance Requirements

**Response Time Targets**:
- Profile queries: < 50ms (95th percentile)
- Account listing: < 100ms (95th percentile)
- Activity history: < 200ms (95th percentile)
- User search: < 150ms (95th percentile)

**Caching Hit Rates**:
- User profiles: > 90% cache hit rate
- Account listings: > 85% cache hit rate

---

## 💼 Account Management Domain

### Account Command Service

#### Service Overview
**Component ID**: COMP-003  
**Service Type**: Command Service (CQRS Write)  
**Deployment**: Stateless, horizontally scalable  
**Primary Port**: 8003

**Primary Responsibilities**:
- Exchange account management and lifecycle
- API credential validation and security
- Account synchronization triggering
- Account status and health monitoring
- Multi-exchange account coordination

#### API Specifications

**REST API Endpoints**:
```yaml
PUT /api/v1/accounts/{account_id}/credentials:
  summary: "Update account API credentials"
  parameters:
    account_id: UUID (path)
  request_body:
    api_key: string
    api_secret: string
    passphrase: string (optional)
  responses:
    200: "Credentials updated"
    400: "Invalid credentials"
    404: "Account not found"

POST /api/v1/accounts/{account_id}/sync:
  summary: "Trigger account synchronization"
  parameters:
    account_id: UUID (path)
  request_body:
    sync_type: enum [FULL, INCREMENTAL]
    force: boolean (default: false)
  responses:
    202: "Synchronization initiated"
    404: "Account not found"
    409: "Sync already in progress"

PUT /api/v1/accounts/{account_id}/status:
  summary: "Update account status"
  parameters:
    account_id: UUID (path)
  request_body:
    status: enum [ACTIVE, SUSPENDED, DISABLED]
    reason: string
  responses:
    200: "Status updated"
    404: "Account not found"

DELETE /api/v1/accounts/{account_id}:
  summary: "Unlink exchange account"
  parameters:
    account_id: UUID (path)
  request_body:
    confirmation_code: string
  responses:
    200: "Account unlinked"
    404: "Account not found"
    409: "Account has active positions"
```

#### Event Production

**Events Published**:
```yaml
account.credentials_updated:
  topic: "account-events"
  partition_key: account_id
  data:
    account_id: UUID
    user_id: UUID
    exchange: string
    updated_at: datetime

account.sync_initiated:
  topic: "account-events"
  partition_key: account_id
  data:
    account_id: UUID
    sync_type: string
    initiated_by: string
    initiated_at: datetime

account.status_changed:
  topic: "account-events"
  partition_key: account_id
  data:
    account_id: UUID
    previous_status: string
    new_status: string
    reason: string
    changed_at: datetime

account.unlinked:
  topic: "account-events"
  partition_key: account_id
  data:
    account_id: UUID
    user_id: UUID
    exchange: string
    reason: string
    unlinked_at: datetime
```

#### Business Rules

**Credential Management Rules**:
- API credentials must pass exchange validation before storage
- Credentials are encrypted using AES-256 with user-specific keys
- Failed credential validation triggers account suspension
- Credential updates require account synchronization

**Account Status Rules**:
- SUSPENDED accounts cannot place new orders but can close positions
- DISABLED accounts have all trading functionality blocked
- Status changes require administrative approval for risk management
- Account unlinking requires zero open positions and pending orders

#### Dependencies

**External Services**:
- **Exchange APIs**: Credential validation and account information
- **Encryption Service**: Secure credential storage and retrieval
- **Account Data Service**: Real-time account synchronization
- **Risk Engine**: Account risk validation

**Database Access**:
- **Write Database**: PostgreSQL for account metadata
- **Event Store**: Account change audit trail

#### Error Handling

**Error Categories**:
```python
class AccountCommandErrors:
    INVALID_CREDENTIALS = "INVALID_API_CREDENTIALS"
    SYNC_IN_PROGRESS = "SYNCHRONIZATION_IN_PROGRESS"  
    ACTIVE_POSITIONS = "ACCOUNT_HAS_ACTIVE_POSITIONS"
    EXCHANGE_UNAVAILABLE = "EXCHANGE_API_UNAVAILABLE"
    ENCRYPTION_FAILURE = "CREDENTIAL_ENCRYPTION_FAILED"
```

---

## 📈 Trading Domain

### Order Command Service

#### Service Overview
**Component ID**: COMP-004  
**Service Type**: Command Service (CQRS Write)  
**Deployment**: Stateless, horizontally scalable  
**Primary Port**: 8004

**Primary Responsibilities**:
- Order creation, modification, and cancellation
- Order validation and risk checking
- Stop-loss and take-profit management
- Emergency order controls and position management
- Order routing to appropriate exchanges

#### API Specifications

**REST API Endpoints**:
```yaml
POST /api/v1/orders:
  summary: "Create new trading order"
  request_body:
    account_id: UUID
    strategy_id: UUID (optional)
    symbol: string
    side: enum [BUY, SELL]
    position_side: enum [LONG, SHORT, BOTH]
    type: enum [MARKET, LIMIT, STOP_MARKET, STOP_LIMIT, TAKE_PROFIT]
    quantity: decimal
    price: decimal (required for LIMIT orders)
    stop_price: decimal (required for STOP orders)
    time_in_force: enum [GTC, IOC, FOK]
    reduce_only: boolean (default: false)
  responses:
    201:
      order_id: UUID
      client_order_id: string
      status: string
    400: "Validation errors"
    403: "Insufficient permissions or risk violation"

PUT /api/v1/orders/{order_id}:
  summary: "Modify existing order"
  parameters:
    order_id: UUID (path)
  request_body:
    quantity: decimal (optional)
    price: decimal (optional)
    stop_price: decimal (optional)
  responses:
    200: "Order modified"
    404: "Order not found"
    409: "Order cannot be modified"

DELETE /api/v1/orders/{order_id}:
  summary: "Cancel order"
  parameters:
    order_id: UUID (path)
  responses:
    200: "Order cancelled"
    404: "Order not found"
    409: "Order cannot be cancelled"

POST /api/v1/orders/{order_id}/emergency-cancel:
  summary: "Emergency order cancellation (admin only)"
  parameters:
    order_id: UUID (path)
  request_body:
    reason: string
    force: boolean (default: false)
  responses:
    200: "Emergency cancellation initiated"
    404: "Order not found"
```

#### Event Production

**Events Published**:
```yaml
order.created:
  topic: "trading-events"
  partition_key: user_id
  data:
    order_id: UUID
    user_id: UUID
    account_id: UUID
    strategy_id: UUID
    symbol: string
    side: string
    type: string
    quantity: decimal
    price: decimal
    status: string
    created_at: datetime

order.modified:
  topic: "trading-events"
  partition_key: user_id
  data:
    order_id: UUID
    changes: object
    previous_values: object
    modified_at: datetime

order.cancelled:
  topic: "trading-events"
  partition_key: user_id
  data:
    order_id: UUID
    cancellation_reason: string
    cancelled_by: string
    cancelled_at: datetime

order.filled:
  topic: "trading-events"
  partition_key: user_id
  data:
    order_id: UUID
    fill_id: UUID
    filled_quantity: decimal
    fill_price: decimal
    commission: decimal
    filled_at: datetime
```

#### Business Rules

**Order Validation Rules**:
- Quantity must be within exchange minimum/maximum limits
- Price precision must match symbol requirements
- Sufficient balance required for order placement
- Risk parameters must be validated before order creation
- Stop-loss orders require position side specification

**Risk Management Integration**:
```python
class OrderRiskValidation:
    """Order risk validation rules"""
    
    async def validate_order_risk(self, order_request: OrderRequest) -> RiskValidationResult:
        """Validate order against all risk parameters"""
        
        # User-level risk checks
        user_risk = await self.validate_user_risk_limits(order_request)
        
        # Portfolio-level risk checks  
        portfolio_risk = await self.validate_portfolio_risk(order_request)
        
        # Strategy-level risk checks
        strategy_risk = await self.validate_strategy_risk(order_request)
        
        # Position size validation
        position_risk = await self.validate_position_limits(order_request)
        
        return RiskValidationResult.combine([
            user_risk, portfolio_risk, strategy_risk, position_risk
        ])
```

#### Dependencies

**External Services**:
- **Risk Engine**: Real-time risk validation
- **Exchange Adapters**: Order execution and status updates
- **Strategy Engine**: Strategy-based order parameters
- **Account Query Service**: Balance and position validation

#### Performance Requirements

**Response Time Targets**:
- Order creation: < 100ms (95th percentile)
- Order modification: < 50ms (95th percentile)
- Order cancellation: < 30ms (95th percentile)

**Throughput Targets**:
- 1000 orders per minute per service instance
- 10,000 concurrent order validations
- 500 emergency operations per minute

---

## 🎯 Strategy Domain

### Strategy Engine

#### Service Overview
**Component ID**: COMP-005  
**Service Type**: Domain Service  
**Deployment**: Stateful, managed scaling  
**Primary Port**: 8005

**Primary Responsibilities**:
- Strategy execution and signal generation
- Multi-user strategy allocation management
- Strategy performance tracking and optimization
- Real-time market analysis and decision making
- Strategy lifecycle and health monitoring

#### Strategy Framework Architecture

**Abstract Strategy Interface**:
```python
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class TradingSignal:
    """Trading signal generated by strategy"""
    strategy_id: UUID
    symbol: str
    action: str  # BUY, SELL, HOLD
    confidence: float  # 0.0 to 1.0
    quantity: Optional[Decimal] = None
    price_target: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    metadata: Dict[str, Any] = None

class BaseStrategy(ABC):
    """Abstract base strategy interface"""
    
    def __init__(self, strategy_id: UUID, config: StrategyConfig):
        self.strategy_id = strategy_id
        self.config = config
        self.performance_tracker = PerformanceTracker(strategy_id)
    
    @abstractmethod
    async def analyze_market_data(self, market_data: MarketDataUpdate) -> List[TradingSignal]:
        """Analyze market data and generate trading signals"""
        pass
    
    @abstractmethod
    async def calculate_position_size(self, signal: TradingSignal, account_balance: Decimal) -> Decimal:
        """Calculate appropriate position size for signal"""
        pass
    
    @abstractmethod  
    async def should_close_position(self, position: Position, current_price: Decimal) -> bool:
        """Determine if position should be closed"""
        pass
    
    async def get_performance_metrics(self) -> StrategyPerformanceMetrics:
        """Get current strategy performance metrics"""
        return await self.performance_tracker.get_current_metrics()
```

**Strategy Implementation Example**:
```python
class ScalpingStrategy(BaseStrategy):
    """High-frequency scalping strategy implementation"""
    
    def __init__(self, strategy_id: UUID, config: ScalpingConfig):
        super().__init__(strategy_id, config)
        self.ema_short = ExponentialMovingAverage(config.ema_short_period)
        self.ema_long = ExponentialMovingAverage(config.ema_long_period)
        self.rsi = RSI(config.rsi_period)
        
    async def analyze_market_data(self, market_data: MarketDataUpdate) -> List[TradingSignal]:
        """Scalping strategy market analysis"""
        signals = []
        
        # Update technical indicators
        self.ema_short.update(market_data.price)
        self.ema_long.update(market_data.price) 
        self.rsi.update(market_data.price)
        
        # Generate signals based on technical analysis
        if self.should_buy(market_data):
            signal = TradingSignal(
                strategy_id=self.strategy_id,
                symbol=market_data.symbol,
                action="BUY",
                confidence=self.calculate_confidence(),
                stop_loss=market_data.price * 0.995,  # 0.5% stop loss
                take_profit=market_data.price * 1.01   # 1% take profit
            )
            signals.append(signal)
            
        elif self.should_sell(market_data):
            signal = TradingSignal(
                strategy_id=self.strategy_id,
                symbol=market_data.symbol,
                action="SELL", 
                confidence=self.calculate_confidence(),
                stop_loss=market_data.price * 1.005,  # 0.5% stop loss
                take_profit=market_data.price * 0.99   # 1% take profit
            )
            signals.append(signal)
            
        return signals
    
    def should_buy(self, market_data: MarketDataUpdate) -> bool:
        """Buy signal logic"""
        return (
            self.ema_short.value > self.ema_long.value and
            self.rsi.value < 30 and
            market_data.volume > self.config.min_volume_threshold
        )
```

#### Event Production and Consumption

**Events Published**:
```yaml
strategy.signal_generated:
  topic: "strategy-events"
  partition_key: strategy_id
  data:
    strategy_id: UUID
    signal_id: UUID
    symbol: string
    action: string
    confidence: decimal
    price_target: decimal
    stop_loss: decimal
    take_profit: decimal
    generated_at: datetime

strategy.performance_updated:
  topic: "strategy-events"
  partition_key: strategy_id
  data:
    strategy_id: UUID
    total_trades: integer
    winning_trades: integer
    total_pnl: decimal
    win_rate: decimal
    sharpe_ratio: decimal
    max_drawdown: decimal
    updated_at: datetime
```

**Events Consumed**:
```yaml
market.data.prices:
  action: "Analyze market data for all active strategies"
  handler: "process_market_data"

order.filled:
  action: "Update strategy performance metrics"
  handler: "update_strategy_performance"

position.closed:
  action: "Calculate strategy trade results"
  handler: "record_strategy_trade"
```

---

## 🎲 Risk Management Domain

### Risk Engine

#### Service Overview
**Component ID**: COMP-006  
**Service Type**: Domain Service  
**Deployment**: Stateful, controlled scaling  
**Primary Port**: 8006

**Primary Responsibilities**:
- Real-time portfolio risk assessment and monitoring
- Multi-level risk limit enforcement (user, account, system)
- Value-at-Risk (VaR) calculations and stress testing
- Margin requirement monitoring and margin call prevention
- Emergency risk controls and automated position management

#### Risk Assessment Framework

**Risk Calculation Engine**:
```python
class RiskCalculationEngine:
    """Comprehensive risk calculation and monitoring"""
    
    def __init__(self, config: RiskEngineConfig):
        self.var_calculator = VaRCalculator(config.var_confidence_level)
        self.correlation_matrix = CorrelationMatrixCalculator()
        self.volatility_estimator = VolatilityEstimator()
        
    async def calculate_portfolio_risk(self, portfolio: Portfolio) -> PortfolioRiskMetrics:
        """Calculate comprehensive portfolio risk metrics"""
        
        # Position-level risk metrics
        position_risks = []
        for position in portfolio.positions:
            position_risk = await self.calculate_position_risk(position)
            position_risks.append(position_risk)
        
        # Portfolio-level aggregation
        total_exposure = sum(pos.market_value for pos in portfolio.positions)
        portfolio_var = await self.calculate_portfolio_var(position_risks)
        correlation_risk = await self.calculate_correlation_risk(position_risks)
        leverage_ratio = total_exposure / portfolio.account_balance
        
        # Stress testing
        stress_test_results = await self.run_stress_tests(portfolio)
        
        return PortfolioRiskMetrics(
            total_exposure=total_exposure,
            portfolio_var_95=portfolio_var,
            correlation_risk=correlation_risk,
            leverage_ratio=leverage_ratio,
            margin_ratio=portfolio.margin_balance / portfolio.maintenance_margin,
            stress_test_results=stress_test_results,
            risk_score=self.calculate_composite_risk_score(portfolio)
        )
    
    async def calculate_position_risk(self, position: Position) -> PositionRiskMetrics:
        """Calculate individual position risk metrics"""
        
        # Historical volatility
        volatility = await self.volatility_estimator.calculate_volatility(
            symbol=position.symbol,
            period_days=30
        )
        
        # Position VaR
        position_var = self.var_calculator.calculate_position_var(
            position_value=position.market_value,
            volatility=volatility
        )
        
        # Maximum potential loss
        max_potential_loss = position.quantity * (position.entry_price - position.stop_loss) \\
                           if position.stop_loss else position.market_value * 0.1
        
        return PositionRiskMetrics(
            symbol=position.symbol,
            position_var=position_var,
            volatility=volatility,
            max_potential_loss=max_potential_loss,
            leverage_factor=position.leverage,
            margin_requirement=position.margin_requirement
        )
```

**Risk Monitoring and Alerts**:
```python
class RealTimeRiskMonitor:
    """Real-time risk monitoring and violation detection"""
    
    def __init__(self, risk_parameters: RiskParameters):
        self.risk_parameters = risk_parameters
        self.violation_detector = RiskViolationDetector()
        self.alert_manager = RiskAlertManager()
    
    async def monitor_portfolio_risk(self, user_id: UUID, portfolio_update: PortfolioUpdate):
        """Monitor portfolio for risk violations"""
        
        # Calculate current risk metrics
        risk_metrics = await self.calculate_portfolio_risk(portfolio_update.portfolio)
        
        # Check for violations
        violations = await self.violation_detector.check_violations(
            user_id=user_id,
            risk_metrics=risk_metrics,
            risk_parameters=self.risk_parameters
        )
        
        # Handle violations
        for violation in violations:
            await self.handle_risk_violation(violation)
    
    async def handle_risk_violation(self, violation: RiskViolation):
        """Handle detected risk violations"""
        
        if violation.severity == RiskSeverity.CRITICAL:
            # Emergency position reduction
            await self.emergency_position_manager.reduce_exposure(
                user_id=violation.user_id,
                reduction_percentage=0.5
            )
            
            # Immediate alert to risk management team
            await self.alert_manager.send_critical_alert(violation)
            
        elif violation.severity == RiskSeverity.HIGH:
            # Strategy pause and warning
            await self.strategy_manager.pause_strategies(violation.user_id)
            await self.alert_manager.send_warning_alert(violation)
            
        elif violation.severity == RiskSeverity.MEDIUM:
            # Risk notification to user
            await self.notification_service.send_risk_warning(
                user_id=violation.user_id,
                violation=violation
            )
```

#### API Specifications

**REST API Endpoints**:
```yaml
GET /api/v1/risk/portfolio/{user_id}:
  summary: "Get current portfolio risk metrics"
  parameters:
    user_id: UUID (path)
  responses:
    200:
      total_exposure: decimal
      portfolio_var_95: decimal
      leverage_ratio: decimal
      margin_ratio: decimal
      risk_score: decimal
      positions:
        - symbol: string
          position_var: decimal
          volatility: decimal
          risk_contribution: decimal

POST /api/v1/risk/stress-test:
  summary: "Run portfolio stress test"
  request_body:
    user_id: UUID
    scenario_type: enum [MARKET_CRASH, VOLATILITY_SPIKE, CORRELATION_BREAKDOWN]
    severity: enum [MILD, MODERATE, SEVERE]
  responses:
    200:
      scenario_name: string
      total_loss: decimal
      affected_positions: array
      survival_probability: decimal

GET /api/v1/risk/violations/{user_id}:
  summary: "Get risk violations history"
  parameters:
    user_id: UUID (path)
    limit: integer (query, default: 50)
    severity: string (query, optional)
  responses:
    200:
      violations:
        - violation_id: UUID
          violation_type: string
          severity: string
          description: string
          action_taken: string
          occurred_at: datetime
```

---

## 📊 Data Services Layer

### Market Data Service

#### Service Overview
**Component ID**: COMP-007  
**Service Type**: Data Service  
**Deployment**: Stateful, high-availability  
**Primary Port**: 8007

**Primary Responsibilities**:
- Shared WebSocket connection management for market data
- Real-time price feed distribution to all system components
- Market data normalization across different exchanges
- Connection health monitoring and automatic reconnection
- Historical market data caching and retrieval

#### WebSocket Architecture

**Shared Connection Management**:
```python
class MarketDataConnectionManager:
    """Manages shared WebSocket connections for market data"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # symbol -> subscriber_services
        self.connection_health: Dict[str, ConnectionHealth] = {}
    
    async def subscribe_to_symbol(self, exchange: str, symbol: str, subscriber_id: str):
        """Subscribe to symbol data with connection sharing"""
        connection_key = f"{exchange}:{symbol}"
        
        # Create connection if doesn't exist
        if connection_key not in self.connections:
            connection = await self.create_websocket_connection(exchange, symbol)
            self.connections[connection_key] = connection
            self.subscriptions[connection_key] = set()
            
            # Start connection monitoring
            asyncio.create_task(self.monitor_connection_health(connection_key))
        
        # Add subscriber
        self.subscriptions[connection_key].add(subscriber_id)
        
        # Start data forwarding if first subscriber
        if len(self.subscriptions[connection_key]) == 1:
            asyncio.create_task(self.forward_market_data(connection_key))
    
    async def forward_market_data(self, connection_key: str):
        """Forward market data to Kafka for distribution"""
        connection = self.connections[connection_key]
        
        async for message in connection:
            try:
                # Normalize market data format
                normalized_data = self.normalize_market_data(connection_key, message)
                
                # Publish to Kafka
                await self.kafka_producer.send(
                    topic="market.data.prices",
                    key=normalized_data.symbol,
                    value=normalized_data.to_dict()
                )
                
                # Update connection health
                self.connection_health[connection_key].last_message_at = datetime.utcnow()
                
            except Exception as e:
                logger.error(f"Error processing market data for {connection_key}: {e}")
                await self.handle_connection_error(connection_key, e)
```

**Data Normalization**:
```python
@dataclass
class NormalizedMarketData:
    """Normalized market data structure"""
    exchange: str
    symbol: str
    price: Decimal
    quantity: Decimal
    timestamp: datetime
    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    volume_24h: Optional[Decimal] = None
    price_change_24h: Optional[Decimal] = None

class MarketDataNormalizer:
    """Normalize market data from different exchanges"""
    
    def normalize_binance_data(self, raw_data: dict) -> NormalizedMarketData:
        """Normalize Binance market data format"""
        return NormalizedMarketData(
            exchange="BINANCE",
            symbol=raw_data["s"],
            price=Decimal(raw_data["c"]),
            quantity=Decimal(raw_data["q"]),
            timestamp=datetime.fromtimestamp(raw_data["E"] / 1000),
            volume_24h=Decimal(raw_data["v"]),
            price_change_24h=Decimal(raw_data["P"])
        )
    
    def normalize_bybit_data(self, raw_data: dict) -> NormalizedMarketData:
        """Normalize Bybit market data format"""
        return NormalizedMarketData(
            exchange="BYBIT",
            symbol=raw_data["topic"].split(".")[-1],
            price=Decimal(raw_data["data"]["price"]),
            quantity=Decimal(raw_data["data"]["size"]),
            timestamp=datetime.fromtimestamp(raw_data["ts"] / 1000),
            bid_price=Decimal(raw_data["data"]["bid"]),
            ask_price=Decimal(raw_data["data"]["ask"])
        )
```

#### Performance Requirements

**Latency Targets**:
- Market data processing: < 5ms
- Data normalization: < 1ms  
- Kafka publishing: < 10ms
- End-to-end latency: < 50ms

**Throughput Targets**:
- 100,000 price updates per second
- 1,000 concurrent symbol subscriptions
- 99.9% connection uptime

---

### Account Data Service

#### Service Overview
**Component ID**: COMP-008  
**Service Type**: Data Service  
**Deployment**: Stateful, user-partitioned  
**Primary Port**: 8008

**Primary Responsibilities**:
- Individual WebSocket connections for private account data
- Real-time balance and position synchronization
- Order status updates and execution reports
- Account-specific event generation and publishing
- Private data security and isolation

#### Individual Connection Management

**Account Connection Manager**:
```python
class AccountDataConnectionManager:
    """Manages individual WebSocket connections per user account"""
    
    def __init__(self):
        self.account_connections: Dict[str, AccountWebSocket] = {}
        self.connection_status: Dict[str, ConnectionStatus] = {}
    
    async def connect_user_account(self, user_id: UUID, account_id: UUID, 
                                 exchange: str, credentials: ExchangeCredentials):
        """Create dedicated WebSocket connection for user account"""
        connection_key = f"{user_id}:{account_id}:{exchange}"
        
        if connection_key not in self.account_connections:
            # Create authenticated WebSocket connection
            websocket = await self.create_authenticated_websocket(
                exchange=exchange,
                credentials=credentials
            )
            
            self.account_connections[connection_key] = AccountWebSocket(
                websocket=websocket,
                user_id=user_id,
                account_id=account_id,
                exchange=exchange
            )
            
            # Start monitoring account updates
            asyncio.create_task(self.monitor_account_updates(connection_key))
            
            # Start connection health monitoring
            asyncio.create_task(self.monitor_connection_health(connection_key))
    
    async def monitor_account_updates(self, connection_key: str):
        """Monitor account-specific updates and publish events"""
        connection = self.account_connections[connection_key]
        
        async for message in connection.websocket:
            try:
                # Parse account update type
                update_type = self.identify_update_type(message)         
                if update_type == "BALANCE_UPDATE":
                    await self.handle_balance_update(connection, message)
                elif update_type == "POSITION_UPDATE":
                    await self.handle_position_update(connection, message)
                elif update_type == "ORDER_UPDATE":
                    await self.handle_order_update(connection, message)
                elif update_type == "EXECUTION_REPORT":
                    await self.handle_execution_report(connection, message)
                
                # Update connection health
                self.connection_status[connection_key].last_update_at = datetime.utcnow()
                
            except Exception as e:
                logger.error(f"Error processing account update for {connection_key}: {e}")
                await self.handle_connection_error(connection_key, e)
    
    async def handle_balance_update(self, connection: AccountWebSocket, message: dict):
        """Handle account balance updates"""
        balance_update = self.parse_balance_update(connection.exchange, message)
        
        # Publish balance update event
        await self.kafka_producer.send(
            topic="account.events",
            key=str(connection.account_id),
            value={
                "event_type": "balance.updated",
                "account_id": str(connection.account_id),
                "user_id": str(connection.user_id),
                "exchange": connection.exchange,
                "balance_data": balance_update,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def handle_position_update(self, connection: AccountWebSocket, message: dict):
        """Handle position updates"""
        position_update = self.parse_position_update(connection.exchange, message)
        
        # Publish position update event
        await self.kafka_producer.send(
            topic="account.events",
            key=str(connection.account_id),
            value={
                "event_type": "position.updated",
                "account_id": str(connection.account_id),
                "user_id": str(connection.user_id),
                "exchange": connection.exchange,
                "position_data": position_update,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
```

### Exchange Adapters

#### Service Overview
**Component ID**: COMP-009  
**Service Type**: Integration Service  
**Deployment**: Stateless, exchange-partitioned  
**Primary Port**: 8009

**Primary Responsibilities**:
- Unified exchange API integration layer
- Order execution and management across different exchanges
- Exchange-specific error handling and retry logic
- Rate limit management and request throttling
- API response normalization and validation

#### Unified Exchange Interface

**Abstract Exchange Adapter**:
```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class ExchangeAdapter(ABC):
    """Abstract base class for exchange integrations"""
    
    def __init__(self, exchange_name: str, credentials: ExchangeCredentials):
        self.exchange_name = exchange_name
        self.credentials = credentials
        self.rate_limiter = RateLimiter(self.get_rate_limits())
        self.client = self.create_client()
    
    @abstractmethod
    async def place_order(self, order_request: PlaceOrderRequest) -> ExchangeOrderResponse:
        """Place order on exchange"""
        pass
    
    @abstractmethod
    async def cancel_order(self, cancel_request: CancelOrderRequest) -> ExchangeOrderResponse:
        """Cancel order on exchange"""
        pass
    
    @abstractmethod
    async def modify_order(self, modify_request: ModifyOrderRequest) -> ExchangeOrderResponse:
        """Modify existing order on exchange"""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> ExchangeOrderStatus:
        """Get current order status"""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> ExchangeAccountInfo:
        """Get account information including balances and positions"""
        pass
    
    @abstractmethod
    async def get_position_info(self, symbol: Optional[str] = None) -> List[ExchangePosition]:
        """Get current positions"""
        pass
    
    @abstractmethod
    def create_websocket_url(self, stream_type: str) -> str:
        """Create WebSocket URL for real-time data"""
        pass
    
    @abstractmethod
    def get_rate_limits(self) -> Dict[str, RateLimit]:
        """Get exchange-specific rate limits"""
        pass

class BinanceAdapter(ExchangeAdapter):
    """Binance Futures API adapter implementation"""
    
    def __init__(self, credentials: ExchangeCredentials):
        super().__init__("BINANCE", credentials)
        self.base_url = "https://fapi.binance.com"
    
    async def place_order(self, order_request: PlaceOrderRequest) -> ExchangeOrderResponse:
        """Place order on Binance Futures"""
        
        # Rate limit check
        await self.rate_limiter.acquire("place_order")
        
        # Prepare Binance-specific parameters
        params = {
            "symbol": order_request.symbol,
            "side": order_request.side,
            "type": self.map_order_type(order_request.type),
            "quantity": str(order_request.quantity),
            "timeInForce": order_request.time_in_force,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }
        
        # Add price for limit orders
        if order_request.type in ["LIMIT", "STOP_LIMIT"]:
            params["price"] = str(order_request.price)
        
        # Add stop price for stop orders
        if order_request.type in ["STOP_MARKET", "STOP_LIMIT"]:
            params["stopPrice"] = str(order_request.stop_price)
        
        # Add position side for hedge mode
        if order_request.position_side:
            params["positionSide"] = order_request.position_side
        
        # Sign request
        params = self.sign_request(params)
        
        try:
            response = await self.client.post("/fapi/v1/order", json=params)
            return self.parse_order_response(response)
            
        except ExchangeAPIError as e:
            return ExchangeOrderResponse(
                success=False,
                error_code=e.error_code,
                error_message=e.error_message,
                exchange_order_id=None
            )
    
    def map_order_type(self, order_type: str) -> str:
        """Map internal order type to Binance format"""
        type_mapping = {
            "MARKET": "MARKET",
            "LIMIT": "LIMIT", 
            "STOP_MARKET": "STOP_MARKET",
            "STOP_LIMIT": "STOP",
            "TAKE_PROFIT": "TAKE_PROFIT_MARKET"
        }
        return type_mapping.get(order_type, order_type)
    
    async def get_account_info(self) -> ExchangeAccountInfo:
        """Get Binance account information"""
        await self.rate_limiter.acquire("account_info")
        
        response = await self.client.get("/fapi/v2/account", params=self.sign_request({}))
        
        return ExchangeAccountInfo(
            total_wallet_balance=Decimal(response["totalWalletBalance"]),
            total_unrealized_pnl=Decimal(response["totalUnrealizedProfit"]),
            total_margin_balance=Decimal(response["totalMarginBalance"]),
            total_maintenance_margin=Decimal(response["totalMaintMargin"]),
            total_initial_margin=Decimal(response["totalInitialMargin"]),
            available_balance=Decimal(response["availableBalance"]),
            max_withdraw_amount=Decimal(response["maxWithdrawAmount"])
        )

class BybitAdapter(ExchangeAdapter):
    """Bybit API adapter implementation"""
    
    def __init__(self, credentials: ExchangeCredentials):
        super().__init__("BYBIT", credentials)
        self.base_url = "https://api.bybit.com"
    
    async def place_order(self, order_request: PlaceOrderRequest) -> ExchangeOrderResponse:
        """Place order on Bybit"""
        
        await self.rate_limiter.acquire("place_order")
        
        # Bybit-specific parameters
        params = {
            "category": "linear",  # Futures trading
            "symbol": order_request.symbol,
            "side": order_request.side,
            "orderType": self.map_order_type(order_request.type),
            "qty": str(order_request.quantity),
            "timeInForce": order_request.time_in_force
        }
        
        # Add price for limit orders
        if order_request.type in ["LIMIT", "STOP_LIMIT"]:
            params["price"] = str(order_request.price)
        
        # Add trigger price for conditional orders
        if order_request.type in ["STOP_MARKET", "STOP_LIMIT"]:
            params["triggerPrice"] = str(order_request.stop_price)
        
        # Sign and send request
        signed_params = self.sign_request(params)
        
        try:
            response = await self.client.post("/v5/order/create", json=signed_params)
            return self.parse_order_response(response)
            
        except ExchangeAPIError as e:
            return ExchangeOrderResponse(
                success=False,
                error_code=e.error_code,
                error_message=e.error_message,
                exchange_order_id=None
            )
```

#### Error Handling and Retry Logic

**Exchange Error Handling**:
```python
class ExchangeErrorHandler:
    """Centralized exchange error handling"""
    
    def __init__(self):
        self.retry_policies = {
            "RATE_LIMIT_EXCEEDED": RetryPolicy(
                max_attempts=5,
                backoff_strategy=ExponentialBackoff(base_delay=1.0, max_delay=60.0)
            ),
            "NETWORK_ERROR": RetryPolicy(
                max_attempts=3,
                backoff_strategy=FixedDelay(delay=2.0)
            ),
            "INSUFFICIENT_BALANCE": RetryPolicy(
                max_attempts=1,
                should_retry=False
            )
        }
    
    async def handle_exchange_error(self, error: ExchangeAPIError, 
                                  operation: Callable) -> Any:
        """Handle exchange errors with appropriate retry logic"""
        
        error_category = self.categorize_error(error)
        retry_policy = self.retry_policies.get(error_category)
        
        if not retry_policy or not retry_policy.should_retry:
            raise error
        
        for attempt in range(retry_policy.max_attempts):
            try:
                await retry_policy.backoff_strategy.wait(attempt)
                return await operation()
                
            except ExchangeAPIError as retry_error:
                if attempt == retry_policy.max_attempts - 1:
                    raise retry_error
                
                # Log retry attempt
                logger.warning(
                    f"Exchange operation failed, retrying... "
                    f"Attempt {attempt + 1}/{retry_policy.max_attempts}",
                    extra={"error": str(retry_error), "operation": operation.__name__}
                )
    
    def categorize_error(self, error: ExchangeAPIError) -> str:
        """Categorize exchange errors for appropriate handling"""
        
        if error.error_code in [-1003, -1015, 429]:  # Rate limit codes
            return "RATE_LIMIT_EXCEEDED"
        elif error.error_code in [-1021, -1022]:  # Timestamp errors
            return "TIMESTAMP_ERROR"
        elif error.error_code in [-2010, -2011]:  # Insufficient balance
            return "INSUFFICIENT_BALANCE"
        elif "network" in error.error_message.lower():
            return "NETWORK_ERROR"
        else:
            return "UNKNOWN_ERROR"
```

---

## 🔒 Infrastructure Services

### Authentication Service

#### Service Overview
**Component ID**: COMP-010  
**Service Type**: Infrastructure Service  
**Deployment**: Stateless, high-availability  
**Primary Port**: 8010

**Primary Responsibilities**:
- JWT token generation and validation
- User session management and security
- Role-based access control (RBAC) enforcement
- Service-to-service authentication
- Security audit logging and monitoring

#### JWT Authentication Implementation

**Token Management**:
```python
class JWTAuthenticationService:
    """JWT-based authentication service"""
    
    def __init__(self, config: AuthConfig):
        self.jwt_secret = config.jwt_secret
        self.jwt_algorithm = "HS256"
        self.access_token_expiry = timedelta(hours=1)
        self.refresh_token_expiry = timedelta(days=7)
        self.redis_client = create_redis_client(config.redis_url)
    
    async def authenticate_user(self, telegram_id: int, username: str) -> AuthenticationResult:
        """Authenticate user and generate tokens"""
        
        # Verify user exists and is active
        user = await self.user_service.get_user_by_telegram_id(telegram_id)
        if not user or user.status != "ACTIVE":
            raise AuthenticationError("User not found or inactive")
        
        # Generate access token
        access_token = self.generate_access_token(user)
        
        # Generate refresh token
        refresh_token = self.generate_refresh_token(user)
        
        # Store refresh token in Redis
        await self.store_refresh_token(user.id, refresh_token)
        
        # Log successful authentication
        await self.audit_logger.log_authentication_success(user.id, telegram_id)
        
        return AuthenticationResult(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(self.access_token_expiry.total_seconds()),
            user_role=user.role
        )
    
    def generate_access_token(self, user: User) -> str:
        """Generate JWT access token"""
        
        payload = {
            "user_id": str(user.id),
            "username": user.username,
            "role": user.role,
            "telegram_id": user.telegram_id,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + self.access_token_expiry,
            "token_type": "access"
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    async def validate_access_token(self, token: str) -> TokenValidationResult:
        """Validate JWT access token"""
        
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Check token type
            if payload.get("token_type") != "access":
                raise InvalidTokenError("Invalid token type")
            
            # Check if user is still active
            user = await self.user_service.get_user_by_id(UUID(payload["user_id"]))
            if not user or user.status != "ACTIVE":
                raise InvalidTokenError("User no longer active")
            
            return TokenValidationResult(
                valid=True,
                user_id=UUID(payload["user_id"]),
                username=payload["username"],
                role=payload["role"],
                telegram_id=payload["telegram_id"]
            )
            
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Access token expired")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}")
```

**Role-Based Access Control**:
```python
class RBACService:
    """Role-based access control implementation"""
    
    ROLE_PERMISSIONS = {
        "user": [
            "portfolio:read",
            "orders:create",
            "orders:read", 
            "orders:cancel_own",
            "strategies:read_assigned"
        ],
        "admin": [
            "users:manage",
            "strategies:manage",
            "system:monitor",
            "orders:cancel_any",
            "risk:manage"
        ],
        "fund_manager": [
            "analytics:read",
            "risk:read",
            "reports:generate",
            "strategies:assign",
            "performance:read"
        ],
        "super_admin": ["*"]  # All permissions
    }
    
    async def check_permission(self, user_role: str, required_permission: str) -> bool:
        """Check if user role has required permission"""
        
        if user_role == "super_admin":
            return True
        
        allowed_permissions = self.ROLE_PERMISSIONS.get(user_role, [])
        
        # Check for wildcard permissions
        if "*" in allowed_permissions:
            return True
        
        # Check for exact permission match
        if required_permission in allowed_permissions:
            return True
        
        # Check for domain-level permissions (e.g., "orders:*")
        permission_domain = required_permission.split(":")[0]
        domain_wildcard = f"{permission_domain}:*"
        
        return domain_wildcard in allowed_permissions
    
    def require_permission(self, required_permission: str):
        """Decorator for API endpoints requiring specific permissions"""
        
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract user context from request
                request = kwargs.get('request') or args[0]
                user_role = getattr(request.state, 'user_role', None)
                
                if not user_role:
                    raise UnauthorizedError("Authentication required")
                
                if not await self.check_permission(user_role, required_permission):
                    raise ForbiddenError(f"Permission denied: {required_permission}")
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator
```

### Event Store Service

#### Service Overview
**Component ID**: COMP-011  
**Service Type**: Infrastructure Service  
**Deployment**: Stateful, clustered  
**Primary Port**: 8011

**Primary Responsibilities**:
- Event sourcing implementation and event persistence
- Event stream management and replay capabilities  
- Aggregate state reconstruction from events
- Event projection management and consistency
- Audit trail maintenance and compliance

#### Event Store Implementation

**Event Storage and Retrieval**:
```python
class EventStoreService:
    """Event sourcing implementation with PostgreSQL backend"""
    
    def __init__(self, database_pool: asyncpg.Pool):
        self.db_pool = database_pool
        self.event_serializer = EventSerializer()
        self.projection_manager = ProjectionManager()
    
    async def append_events(self, stream_id: UUID, expected_version: int, 
                          events: List[DomainEvent]) -> None:
        """Append events to stream with optimistic concurrency control"""
        
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # Check current stream version
                current_version = await self.get_current_version(conn, stream_id)
                
                if current_version != expected_version:
                    raise ConcurrencyError(
                        f"Expected version {expected_version}, got {current_version}"
                    )
                
                # Append new events
                for i, event in enumerate(events):
                    event_version = expected_version + i + 1
                    
                    await conn.execute("""
                        INSERT INTO event_store (
                            stream_id, stream_type, event_type, event_version,
                            event_data, metadata, occurred_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, 
                    stream_id,
                    event.aggregate_type,
                    event.event_type,
                    event_version,
                    self.event_serializer.serialize(event.data),
                    self.event_serializer.serialize(event.metadata),
                    event.occurred_at
                    )
                
                # Update projections asynchronously
                await self.projection_manager.update_projections(stream_id, events)
    
    async def read_events(self, stream_id: UUID, from_version: int = 0) -> List[StoredEvent]:
        """Read events from stream starting from specified version"""
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT stream_id, stream_type, event_type, event_version,
                       event_data, metadata, occurred_at
                FROM event_store
                WHERE stream_id = $1 AND event_version > $2
                ORDER BY event_version ASC
            """, stream_id, from_version)
            
            return [
                StoredEvent(
                    stream_id=row["stream_id"],
                    stream_type=row["stream_type"],
                    event_type=row["event_type"],
                    event_version=row["event_version"],
                    event_data=self.event_serializer.deserialize(row["event_data"]),
                    metadata=self.event_serializer.deserialize(row["metadata"]),
                    occurred_at=row["occurred_at"]
                )
                for row in rows
            ]
    
    async def replay_events(self, from_timestamp: datetime, 
                          to_timestamp: Optional[datetime] = None) -> AsyncIterator[StoredEvent]:
        """Replay events within specified time range"""
        
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT stream_id, stream_type, event_type, event_version,
                       event_data, metadata, occurred_at
                FROM event_store
                WHERE occurred_at >= $1
            """
            params = [from_timestamp]
            
            if to_timestamp:
                query += " AND occurred_at <= $2"
                params.append(to_timestamp)
            
            query += " ORDER BY occurred_at ASC"
            
            async with conn.transaction():
                async for row in conn.cursor(query, *params):
                    yield StoredEvent(
                        stream_id=row["stream_id"],
                        stream_type=row["stream_type"],
                        event_type=row["event_type"],
                        event_version=row["event_version"],
                        event_data=self.event_serializer.deserialize(row["event_data"]),
                        metadata=self.event_serializer.deserialize(row["metadata"]),
                        occurred_at=row["occurred_at"]
                    )
```
- **Custom Metrics**: Trading-specific metrics like P&L, position tracking

#### Technical Specifications

**Metrics Collection Framework**:
```python
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
import asyncio

class PatriotMetricsCollector:
    """
    Business and technical metrics collection for PATRIOT trading system
    """
    
    def __init__(self):
        self.registry = CollectorRegistry()
        self._setup_business_metrics()
        self._setup_technical_metrics()
    
    def _setup_business_metrics(self):
        """Define business-specific metrics"""
        # Order metrics
        self.orders_total = Counter(
            'orders_total',
            'Total number of orders processed',
            ['user_id', 'symbol', 'side', 'status', 'exchange'],
            registry=self.registry
        )
        
        self.order_processing_duration = Histogram(
            'order_processing_duration_seconds',
            'Time taken to process orders',
            ['exchange', 'order_type'],
            registry=self.registry,
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        )
        
        # Portfolio metrics
        self.portfolio_value_usd = Gauge(
            'portfolio_value_usd_total',
            'Total portfolio value in USD',
            ['user_id', 'exchange'],
            registry=self.registry
        )
        
        self.unrealized_pnl_usd = Gauge(
            'unrealized_pnl_usd',
            'Unrealized P&L in USD',
            ['user_id', 'symbol'],
            registry=self.registry
        )
        
        # Risk metrics
        self.risk_limit_violations = Counter(
            'risk_limit_violations_total',
            'Number of risk limit violations',
            ['user_id', 'violation_type'],
            registry=self.registry
        )
        
        # Strategy metrics
        self.strategy_performance = Gauge(
            'strategy_performance_percent',
            'Strategy performance percentage',
            ['strategy_id', 'timeframe'],
            registry=self.registry
        )
    
    def _setup_technical_metrics(self):
        """Define technical system metrics"""
        # HTTP request metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['service', 'endpoint', 'method', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['service', 'endpoint'],
            registry=self.registry
        )
        
        # Database metrics
        self.database_queries_total = Counter(
            'database_queries_total',
            'Total database queries',
            ['service', 'operation', 'table'],
            registry=self.registry
        )
        
        self.database_query_duration = Histogram(
            'database_query_duration_seconds',
            'Database query duration',
            ['service', 'operation'],
            registry=self.registry
        )
        
        # Kafka metrics
        self.kafka_messages_produced = Counter(
            'kafka_messages_produced_total',
            'Total Kafka messages produced',
            ['service', 'topic'],
            registry=self.registry
        )
        
        self.kafka_messages_consumed = Counter(
            'kafka_messages_consumed_total',
            'Total Kafka messages consumed',
            ['service', 'topic'],
            registry=self.registry
        )
    
    # Business metric recording methods
    async def record_order_created(
        self, 
        user_id: str, 
        symbol: str, 
        side: str,
        exchange: str,
        correlation_id: str
    ):
        """Record order creation metrics"""
        self.orders_total.labels(
            user_id=user_id,
            symbol=symbol, 
            side=side,
            status='created',
            exchange=exchange
        ).inc()
        
        # Also log for correlation
        logger.info("Order created metric recorded",
                   correlation_id=correlation_id,
                   user_id=user_id,
                   symbol=symbol)
    
    async def record_portfolio_update(
        self,
        user_id: str,
        exchange: str, 
        total_value_usd: float,
        correlation_id: str
    ):
        """Record portfolio value updates"""
        self.portfolio_value_usd.labels(
            user_id=user_id,
            exchange=exchange
        ).set(total_value_usd)
        
        logger.info("Portfolio value updated",
                   correlation_id=correlation_id,
                   user_id=user_id,
                   total_value_usd=total_value_usd)
    
    async def record_risk_violation(
        self,
        user_id: str,
        violation_type: str,
        correlation_id: str
    ):
        """Record risk limit violations"""
        self.risk_limit_violations.labels(
            user_id=user_id,
            violation_type=violation_type
        ).inc()
        
        logger.error("Risk violation detected",
                    correlation_id=correlation_id,
                    user_id=user_id,
                    violation_type=violation_type)
```

**Prometheus Configuration**:
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "patriot_alerts.yml"

scrape_configs:
  - job_name: 'patriot-services'
    static_configs:
      - targets: ['user-command-service:8001']
        labels:
          service: 'user-command'
      - targets: ['order-command-service:8002'] 
        labels:
          service: 'order-command'
      - targets: ['portfolio-query-service:8003']
        labels:
          service: 'portfolio-query'
    
    scrape_interval: 5s
    metrics_path: /metrics
    
  - job_name: 'patriot-infrastructure'
    static_configs:
      - targets: ['kong:8001']
        labels:
          component: 'api-gateway'
      - targets: ['kafka-exporter:9308']
        labels:
          component: 'kafka'
      - targets: ['postgres-exporter:9187']
        labels:
          component: 'database'

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Component 12: Health Check & Service Discovery

#### Purpose & Scope
Monitors service health and provides service discovery capabilities for dynamic scaling.

#### Core Responsibilities
- **Health Monitoring**: Check service availability and performance
- **Service Registration**: Automatic service registration and deregistration  
- **Load Balancer Integration**: Update load balancer configurations
- **Failure Detection**: Detect and respond to service failures

#### Technical Specifications

**Health Check Framework**:
```python
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List
import aiohttp
import asyncio

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded" 
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    service_name: str
    status: HealthStatus
    response_time_ms: float
    details: Dict[str, any]
    correlation_id: str
    timestamp: str

class HealthCheckService:
    """
    Comprehensive health checking for all PATRIOT services
    """
    
    def __init__(self):
        self.services = self._load_service_registry()
        self.health_history = {}
        self.alert_thresholds = self._load_alert_thresholds()
    
    def _load_service_registry(self) -> Dict[str, Dict]:
        """Load service registry configuration"""
        return {
            'user-command-service': {
                'url': 'http://user-command-service:8001',
                'health_endpoint': '/health',
                'critical': True,
                'timeout_ms': 5000
            },
            'order-command-service': {
                'url': 'http://order-command-service:8002', 
                'health_endpoint': '/health',
                'critical': True,
                'timeout_ms': 3000
            },
            'portfolio-query-service': {
                'url': 'http://portfolio-query-service:8003',
                'health_endpoint': '/health', 
                'critical': False,
                'timeout_ms': 5000
            },
            'trading-engine': {
                'url': 'http://trading-engine:8004',
                'health_endpoint': '/health',
                'critical': True,
                'timeout_ms': 2000
            }
        }
    
    async def check_service_health(
        self, 
        service_name: str,
        correlation_id: str
    ) -> HealthCheckResult:
        """Perform comprehensive health check on a service"""
        service_config = self.services.get(service_name)
        if not service_config:
            return HealthCheckResult(
                service_name=service_name,
                status=HealthStatus.UNKNOWN,
                response_time_ms=0,
                details={'error': 'Service not found in registry'},
                correlation_id=correlation_id,
                timestamp=datetime.utcnow().isoformat()
            )
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(
                    total=service_config['timeout_ms'] / 1000
                )
            ) as session:
                headers = {'X-Correlation-ID': correlation_id}
                
                async with session.get(
                    f"{service_config['url']}{service_config['health_endpoint']}",
                    headers=headers
                ) as response:
                    response_time_ms = (time.time() - start_time) * 1000
                    health_data = await response.json()
                    
                    # Determine health status
                    if response.status == 200:
                        if response_time_ms > service_config.get('degraded_threshold_ms', 2000):
                            status = HealthStatus.DEGRADED
                        else:
                            status = HealthStatus.HEALTHY
                    else:
                        status = HealthStatus.UNHEALTHY
                    
                    return HealthCheckResult(
                        service_name=service_name,
                        status=status,
                        response_time_ms=response_time_ms,
                        details=health_data,
                        correlation_id=correlation_id,
                        timestamp=datetime.utcnow().isoformat()
                    )
                    
        except asyncio.TimeoutError:
            return HealthCheckResult(
                service_name=service_name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                details={'error': 'Health check timeout'},
                correlation_id=correlation_id,
                timestamp=datetime.utcnow().isoformat()
            )
        except Exception as e:
            return HealthCheckResult(
                service_name=service_name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                details={'error': str(e)},
                correlation_id=correlation_id,
                timestamp=datetime.utcnow().isoformat()
            )
    
    async def check_all_services(self, correlation_id: str) -> List[HealthCheckResult]:
        """Check health of all registered services"""
        tasks = [
            self.check_service_health(service_name, correlation_id)
            for service_name in self.services.keys()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log overall system health
        healthy_count = sum(1 for r in results if r.status == HealthStatus.HEALTHY)
        total_count = len(results)
        
        logger.info("System health check completed",
                   correlation_id=correlation_id,
                   healthy_services=healthy_count,
                   total_services=total_count,
                   health_percentage=round(healthy_count/total_count*100, 2))
        
        return results
```

**Service Discovery Integration**:
```python
class ServiceDiscovery:
    """
    Service discovery and registration for dynamic scaling
    """
    
    def __init__(self):
        self.consul_client = self._setup_consul_client()
        self.registered_services = set()
    
    async def register_service(
        self,
        service_name: str,
        service_id: str,
        address: str,
        port: int,
        health_check_url: str,
        correlation_id: str
    ):
        """Register service with discovery system"""
        service_definition = {
            'ID': service_id,
            'Name': service_name,
            'Tags': ['patriot', 'trading', 'microservice'],
            'Address': address,
            'Port': port,
            'Meta': {
                'correlation_id': correlation_id,
                'registered_at': datetime.utcnow().isoformat(),
                'version': '2.0'
            },
            'Check': {
                'HTTP': health_check_url,
                'Interval': '10s',
                'Timeout': '5s',
                'DeregisterCriticalServiceAfter': '30s'
            }
        }
        
        try:
            await self.consul_client.agent.service.register(service_definition)
            self.registered_services.add(service_id)
            
            logger.info("Service registered successfully",
                       correlation_id=correlation_id,
                       service_name=service_name,
                       service_id=service_id,
                       address=f"{address}:{port}")
            
        except Exception as e:
            logger.error("Service registration failed",
                        correlation_id=correlation_id,
                        service_name=service_name,
                        error=str(e))
            raise
    
    async def discover_services(
        self,
        service_name: str,
        correlation_id: str
    ) -> List[Dict]:
        """Discover available instances of a service"""
        try:
            health_services = await self.consul_client.health.service(
                service_name,
                passing=True
            )
            
            instances = []
            for service_info in health_services[1]:
                service = service_info['Service']
                instances.append({
                    'id': service['ID'],
                    'address': service['Address'],
                    'port': service['Port'],
                    'tags': service['Tags'],
                    'meta': service['Meta']
                })
            
            logger.info("Service discovery completed",
                       correlation_id=correlation_id,
                       service_name=service_name,
                       instances_found=len(instances))
            
            return instances
            
        except Exception as e:
            logger.error("Service discovery failed",
                        correlation_id=correlation_id,
                        service_name=service_name,
                        error=str(e))
            return []
```

---

> **Next Steps:**  
> 1. Review component specifications with development teams
> 2. Begin detailed [Infrastructure Planning](04-INFRASTRUCTURE.md)
> 3. Create implementation templates in [API Documentation](annexes/ANNEX-E-API-DOCUMENTATION.md)
> 4. Plan component integration testing strategy
> 5. Establish component monitoring and health check requirements

> **Implementation Notes:**  
> - All components should implement health check endpoints
> - Metrics collection required for all service operations
> - Structured logging mandatory for audit and debugging
> - Circuit breaker patterns for external service dependencies
