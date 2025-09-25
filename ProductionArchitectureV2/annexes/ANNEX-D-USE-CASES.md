# PATRIOT Trading System - Use Cases and User Scenarios

## 📋 Document Information

**Document ID**: ANNEX-D-USE-CASES  
**Version**: 2.0  
**Date**: September 2025  
**Authors**: Solution Architecture Team, Business Analysis Team  
**Status**: Draft  

> **Cross-References:**  
> - System Requirements: [../01-SYSTEM-REQUIREMENTS.md](../01-SYSTEM-REQUIREMENTS.md)  
> - System Architecture: [../02-SYSTEM-ARCHITECTURE.md](../02-SYSTEM-ARCHITECTURE.md)  
> - Component Specifications: [../03-COMPONENT-SPECIFICATIONS.md](../03-COMPONENT-SPECIFICATIONS.md)  
> - API Documentation: [ANNEX-E-API-DOCUMENTATION.md](ANNEX-E-API-DOCUMENTATION.md)

---

## 🎯 Use Case Overview

The PATRIOT trading system operates as a hedge fund platform where users delegate their exchange accounts to centralized trading strategies. This document outlines all primary and secondary use cases, user journeys, and interaction patterns.

### Actor Definitions

#### Primary Actors
- **End User (Trader)**: Individual providing exchange account access for automated trading
- **Administrator**: System operator managing strategies, users, and overall platform health
- **Strategy Manager**: Trading expert defining and monitoring trading strategies

#### Secondary Actors  
- **Exchange APIs**: External cryptocurrency exchanges (Binance, Bybit, etc.)
- **Telegram Bot API**: Communication channel with users
- **Monitoring Systems**: External monitoring and alerting services

---

## 👤 End User Use Cases

### UC-001: User Onboarding

```mermaid
sequenceDiagram
    participant U as User
    participant TB as Telegram Bot
    participant US as User Service
    participant AS as Account Service
    participant ES as Exchange Service

    U->>TB: /start command
    TB->>US: Register user request
    US->>US: Create user profile
    US->>TB: Welcome message + instructions
    TB->>U: Onboarding tutorial
    
    U->>TB: Provide exchange API credentials
    TB->>AS: Store encrypted credentials
    AS->>ES: Validate credentials
    ES->>AS: Validation result
    AS->>TB: Account status
    TB->>U: Confirmation + portfolio sync
```

**Primary Flow:**
1. User initiates contact with Telegram bot
2. System creates user profile with basic information
3. Bot provides onboarding tutorial and instructions
4. User provides exchange API credentials (read-only initially)
5. System validates credentials with exchange
6. User grants trading permissions (API key upgrade)
7. System syncs initial portfolio data
8. User is assigned to default strategies based on risk profile

**Alternative Flows:**
- **AF-001A**: Invalid API credentials → System prompts for correction
- **AF-001B**: Exchange connectivity issues → System queues validation for retry
- **AF-001C**: User already exists → System updates existing profile

**Preconditions:**
- User has active Telegram account
- User has exchange account with API access enabled

**Postconditions:**
- User profile created in system
- Exchange account linked and validated
- Initial portfolio sync completed
- Default strategies assigned

### UC-002: Portfolio Monitoring

```mermaid
flowchart TD
    A[User requests portfolio status] --> B{Real-time or Historical?}
    B -->|Real-time| C[Query live portfolio data]
    B -->|Historical| D[Query time-series data]
    
    C --> E[Aggregate across exchanges]
    D --> F[Apply date/time filters]
    
    E --> G[Calculate current P&L]
    F --> G
    
    G --> H[Format response for Telegram]
    H --> I[Send portfolio summary]
    
    I --> J{User requests details?}
    J -->|Yes| K[Show detailed positions]
    J -->|No| L[End interaction]
    
    K --> M[Display position breakdown]
    M --> N[Show performance metrics]
    N --> L
```

**Primary Flow:**
1. User requests portfolio status via Telegram command
2. System retrieves current portfolio data across all linked exchanges
3. System calculates consolidated P&L, positions, and performance metrics
4. Bot displays formatted portfolio summary
5. User can drill down into specific positions or time periods

**Performance Requirements:**
- Portfolio summary response within 2 seconds
- Real-time updates for active positions
- Historical data queries within 5 seconds

### UC-003: Strategy Management

```mermaid
stateDiagram-v2
    [*] --> ViewStrategies: User requests strategy list
    
    ViewStrategies --> StrategyDetails: Select specific strategy
    ViewStrategies --> StrategyAllocation: Modify allocations
    ViewStrategies --> StrategyPerformance: View performance
    
    StrategyDetails --> ModifyAllocation: Change allocation
    StrategyDetails --> ViewStrategies: Back to list
    
    StrategyAllocation --> ConfirmChanges: Submit changes
    ConfirmChanges --> RiskCheck: Validate risk limits
    
    RiskCheck --> ApproveChanges: Risk check passed
    RiskCheck --> RejectChanges: Risk check failed
    
    ApproveChanges --> ImplementChanges: Execute allocation
    RejectChanges --> StrategyAllocation: Show error message
    
    ImplementChanges --> [*]: Changes applied
    ViewStrategies --> [*]: Exit
    StrategyPerformance --> ViewStrategies: Back to list
```

**Primary Flow:**
1. User views available strategies and current allocations
2. User selects strategy to modify allocation percentage
3. System validates allocation changes against risk limits
4. System applies changes and rebalances portfolio accordingly
5. User receives confirmation of changes

**Business Rules:**
- Total allocation across all strategies cannot exceed 100%
- Individual strategy allocation minimum: 5%
- Maximum strategies per user: 5
- Changes take effect at next rebalancing cycle

### UC-004: Risk Management and Alerts

```mermaid
graph TD
    A[Risk Event Detected] --> B{Severity Level}
    
    B -->|LOW| C[Log event]
    B -->|MEDIUM| D[Send notification]
    B -->|HIGH| E[Send alert + require acknowledgment]  
    B -->|CRITICAL| F[Emergency actions]
    
    C --> G[Continue monitoring]
    D --> H[User acknowledges]
    E --> I[User responds]
    F --> J[Auto-close positions]
    
    H --> G
    I --> K{User action required?}
    J --> L[Notify user of actions taken]
    
    K -->|Yes| M[Present options]
    K -->|No| G
    
    M --> N[User selects action]
    N --> O[Execute user choice]
    O --> G
    L --> G
```

**Risk Event Types:**
- **Drawdown Alert**: Portfolio loss exceeds predefined threshold
- **Position Size Alert**: Single position exceeds risk limit
- **Correlation Alert**: Portfolio correlation risk too high
- **Liquidity Alert**: Market liquidity concerns for held positions

**Response Protocols:**
- **LOW**: Automated logging only
- **MEDIUM**: Telegram notification with current status
- **HIGH**: Urgent notification requiring user acknowledgment
- **CRITICAL**: Automatic position closure with immediate notification

---

## 👨‍💼 Administrator Use Cases

### UC-005: System Administration

```mermaid
flowchart TD
    A[Administrator Login] --> B[System Dashboard]
    
    B --> C{Admin Task}
    C -->|User Management| D[Manage Users]
    C -->|Strategy Management| E[Manage Strategies]
    C -->|System Health| F[Monitor System]
    C -->|Financial Oversight| G[Financial Reports]
    
    D --> D1[View User List]
    D --> D2[Modify User Settings]
    D --> D3[Handle Support Requests]
    
    E --> E1[Create/Update Strategies]
    E --> E2[Monitor Strategy Performance]
    E --> E3[Adjust Risk Parameters]
    
    F --> F1[View System Metrics]
    F --> F2[Check Service Health]
    F --> F3[Review Error Logs]
    
    G --> G1[Revenue Reports]
    G --> G2[Performance Analytics]
    G --> G3[Risk Assessment]
    
    D1 --> H[Update Database]
    D2 --> H
    D3 --> H
    E1 --> H
    E2 --> I[Generate Reports]
    E3 --> H
    F1 --> I
    F2 --> J[Alert Management]
    F3 --> J
    G1 --> I
    G2 --> I
    G3 --> I
    
    H --> B
    I --> B
    J --> K[Take Corrective Action]
    K --> B
```

**Key Administrative Functions:**
1. **User Lifecycle Management**: Registration approval, account suspension, data cleanup
2. **Strategy Operations**: Deploy new strategies, adjust parameters, monitor performance
3. **System Monitoring**: Health checks, performance metrics, error investigation
4. **Financial Oversight**: Fee collection, profit sharing, regulatory reporting

### UC-006: Strategy Performance Analysis

**Primary Flow:**
1. Administrator accesses strategy performance dashboard
2. System displays key metrics: ROI, Sharpe ratio, max drawdown, win rate
3. Administrator can filter by time period, user segment, or strategy type
4. System generates comparative analysis against benchmarks
5. Administrator identifies underperforming strategies for optimization

**Key Metrics Tracked:**
- **Performance**: Total return, risk-adjusted returns, volatility
- **Risk**: Maximum drawdown, VaR, correlation metrics  
- **Operational**: Trade frequency, execution quality, slippage
- **User Impact**: Satisfaction scores, retention rates, fee generation

---

## 🔄 System Integration Use Cases

### UC-007: Exchange Integration

```mermaid
sequenceDiagram
    participant TS as Trading System
    participant EX as Exchange API
    participant OM as Order Manager
    participant RM as Risk Manager
    participant US as User Service

    TS->>RM: Check risk limits
    RM->>TS: Risk approval/denial
    
    alt Risk Approved
        TS->>EX: Place order request
        EX->>TS: Order confirmation
        TS->>OM: Update order status
        OM->>US: Notify user (if significant)
        
        loop Order Monitoring
            TS->>EX: Check order status
            EX->>TS: Status update
            TS->>OM: Update local status
        end
        
        EX->>TS: Order filled notification
        TS->>OM: Process fill
        OM->>US: Update portfolio
        US->>US: Recalculate positions
        
    else Risk Denied
        TS->>US: Log risk violation
        US->>US: Send risk alert to user
    end
```

**Integration Patterns:**
- **Order Placement**: Async with confirmation tracking
- **Market Data**: Real-time WebSocket streams
- **Account Sync**: Periodic reconciliation with exchange balances
- **Error Handling**: Retry logic with exponential backoff

### UC-008: Data Synchronization

**Primary Flow:**
1. System initiates scheduled data sync across all user accounts
2. For each exchange account:
   - Fetch current balances and positions
   - Retrieve recent order history and fills
   - Update local database with new data
3. Detect and resolve data inconsistencies
4. Update user portfolio calculations
5. Generate sync reports for monitoring

**Synchronization Frequency:**
- **Real-time**: Active order status, critical balance changes
- **High-frequency**: Portfolio values, position updates (every 30 seconds)
- **Medium-frequency**: Order history, trade fills (every 5 minutes)  
- **Low-frequency**: Account settings, preferences (daily)

---

## 📱 Telegram Bot Interaction Patterns

### UC-009: Conversational Trading Interface

```mermaid
graph TD
    A[User Message] --> B{Message Type}
    
    B -->|Command| C[Parse Command]
    B -->|Question| D[Natural Language Processing]
    B -->|Data Request| E[Query Processing]
    
    C --> F{Valid Command?}
    F -->|Yes| G[Execute Command]
    F -->|No| H[Show Help]
    
    D --> I[Intent Recognition]
    I --> J[Context Retrieval]
    J --> K[Generate Response]
    
    E --> L[Validate Request]
    L --> M[Fetch Data]
    M --> N[Format Response]
    
    G --> O[Return Result]
    H --> O
    K --> O
    N --> O
    
    O --> P[Send to User]
    P --> Q{Follow-up Needed?}
    Q -->|Yes| R[Prompt for More Info]
    Q -->|No| S[End Conversation]
    
    R --> A
```

**Supported Interaction Types:**
1. **Commands**: `/portfolio`, `/strategies`, `/help`, `/settings`
2. **Natural Queries**: "How am I performing this week?", "Show me my BTCUSDT position"
3. **Quick Actions**: Inline keyboards for common operations
4. **Alerts**: Proactive notifications for important events

### UC-010: User Support and Help System

**Primary Flow:**
1. User requests help or encounters error
2. Bot provides contextual assistance based on user's current state
3. If issue persists, bot escalates to human support
4. Support ticket created with user context and conversation history
5. Administrator receives notification for ticket review

**Self-Service Capabilities:**
- **FAQ Integration**: Common questions with instant answers
- **Contextual Help**: Situation-specific guidance
- **Error Recovery**: Automated retry suggestions
- **Tutorial System**: Step-by-step guides for new features

---

## 🔒 Security and Compliance Use Cases

### UC-011: API Key Security Management

```mermaid
stateDiagram-v2
    [*] --> KeySubmission: User provides API keys
    
    KeySubmission --> Validation: Encrypt and validate
    Validation --> Approved: Valid keys
    Validation --> Rejected: Invalid keys
    
    Approved --> Active: Keys stored securely
    Rejected --> KeySubmission: Request resubmission
    
    Active --> Monitoring: Continuous monitoring
    
    Monitoring --> KeyRotation: Scheduled rotation
    Monitoring --> SecurityAlert: Suspicious activity
    Monitoring --> Active: Normal operation
    
    KeyRotation --> UpdateKeys: Request new keys from user
    SecurityAlert --> Lockdown: Disable trading
    
    UpdateKeys --> Validation: Validate new keys
    Lockdown --> Investigation: Admin review
    
    Investigation --> Resolved: Issue resolved
    Investigation --> Terminated: Account terminated
    
    Resolved --> Active: Restore normal operation
    Terminated --> [*]: Account closed
```

**Security Measures:**
- **Encryption**: AES-256 encryption for stored API keys
- **Access Control**: Role-based permissions for key access
- **Monitoring**: Continuous monitoring for unusual API usage
- **Rotation**: Periodic key rotation recommendations
- **Incident Response**: Automated response to security events

### UC-012: Compliance and Audit Trail

**Primary Flow:**
1. System continuously logs all trading activities
2. Audit trail includes: user actions, system decisions, external API calls
3. Regular compliance reports generated automatically
4. External auditor access provided through secure interface
5. Data retention managed according to regulatory requirements

**Audit Data Tracked:**
- **User Activities**: Login, settings changes, manual interventions
- **Trading Decisions**: Strategy triggers, risk checks, order placements
- **System Events**: Errors, performance issues, security incidents
- **Financial Flows**: Profit sharing, fee calculations, withdrawals

---

## 📊 Analytics and Reporting Use Cases

### UC-013: Performance Analytics

```mermaid
flowchart TD
    A[Analytics Request] --> B{Report Type}
    
    B -->|User Performance| C[Individual Analysis]
    B -->|Strategy Performance| D[Strategy Analysis]  
    B -->|System Performance| E[Platform Analysis]
    
    C --> F[Gather User Data]
    D --> G[Gather Strategy Data]
    E --> H[Gather System Metrics]
    
    F --> I[Calculate Personal Metrics]
    G --> J[Calculate Strategy Metrics]
    H --> K[Calculate System Metrics]
    
    I --> L[Generate User Report]
    J --> M[Generate Strategy Report]
    K --> N[Generate System Report]
    
    L --> O[Personalized Insights]
    M --> P[Strategy Recommendations]
    N --> Q[System Optimizations]
    
    O --> R[Deliver to User]
    P --> S[Deliver to Administrators]
    Q --> S
```

**Analytics Capabilities:**
- **Personal Performance**: Individual portfolio analysis with benchmarks
- **Strategy Effectiveness**: Comparative strategy performance analysis  
- **Risk Assessment**: Portfolio risk metrics and stress testing
- **Market Analysis**: Market condition impact on performance

### UC-014: Predictive Analytics

**Primary Flow:**
1. System collects historical performance and market data
2. Machine learning models analyze patterns and correlations
3. Predictive models generate forecasts for portfolio performance
4. Risk models identify potential future risk scenarios
5. Insights presented to users and administrators for decision-making

**Predictive Models:**
- **Performance Forecasting**: Expected returns based on historical patterns
- **Risk Prediction**: Probability of drawdown scenarios
- **Market Regime Detection**: Identification of changing market conditions
- **Strategy Optimization**: Recommended allocation adjustments

---

## 🎯 Business Process Use Cases

### UC-015: Fee Collection and Profit Sharing

```mermaid
sequenceDiagram
    participant BS as Billing System
    participant PS as Portfolio Service
    participant US as User Service
    participant FS as Financial Service
    participant EX as Exchange

    Note over BS: Monthly fee calculation cycle
    
    BS->>PS: Get user portfolio values
    PS->>BS: Portfolio snapshots (start/end month)
    
    BS->>BS: Calculate profit/loss
    BS->>BS: Determine fee amount
    
    alt Profit Generated
        BS->>FS: Calculate fee (% of profit)
        FS->>EX: Execute fee withdrawal
        EX->>FS: Confirm withdrawal
        FS->>US: Update user balance
        US->>US: Send fee notification
    else Loss or No Profit
        BS->>US: Send monthly report (no fee)
    end
    
    BS->>BS: Generate billing report
    BS->>US: Send monthly statement
```

**Fee Structure:**
- **Performance Fee**: 30% of monthly profits (high-water mark)
- **No Management Fee**: Only profit-sharing model
- **Minimum Fee**: None (no fee if no profit)
- **Fee Calculation**: Monthly cycle with daily portfolio snapshots

### UC-016: Customer Lifecycle Management

**Onboarding to Churn Prevention:**

1. **Acquisition**: User discovers platform through referrals or marketing
2. **Onboarding**: Guided setup process with tutorial and support
3. **Activation**: First successful strategy allocation and trading activity
4. **Engagement**: Regular portfolio monitoring and strategy optimization
5. **Retention**: Performance satisfaction and continued platform usage
6. **Expansion**: Increased allocation or additional exchange accounts
7. **Advocacy**: User referrals and positive reviews

**Churn Prevention Measures:**
- **Performance Monitoring**: Proactive outreach for underperforming accounts
- **Education**: Regular market insights and strategy explanations
- **Support**: Responsive customer service and technical assistance
- **Incentives**: Referral bonuses and loyalty rewards

---

## 🔄 Error Scenarios and Exception Handling

### UC-017: System Failure Recovery

```mermaid
stateDiagram-v2
    [*] --> NormalOperation: System running
    
    NormalOperation --> FailureDetected: Error occurs
    
    FailureDetected --> AssessImpact: Evaluate severity
    
    AssessImpact --> MinorIssue: Low impact
    AssessImpact --> MajorIssue: High impact
    AssessImpact --> CriticalIssue: System-wide impact
    
    MinorIssue --> AutoRecover: Automatic retry
    MajorIssue --> ManualIntervention: Admin notification
    CriticalIssue --> EmergencyProtocol: Immediate response
    
    AutoRecover --> NormalOperation: Recovery successful
    AutoRecover --> ManualIntervention: Retry failed
    
    ManualIntervention --> InvestigateIssue: Admin analysis
    EmergencyProtocol --> SafeMode: Protect user funds
    
    InvestigateIssue --> ImplementFix: Issue resolved
    SafeMode --> InvestigateIssue: Initial response complete
    
    ImplementFix --> NormalOperation: System restored
    ImplementFix --> PostIncident: Complex resolution
    
    PostIncident --> NormalOperation: Full resolution
```

**Failure Categories:**
- **Exchange API Failures**: Connectivity, rate limiting, maintenance
- **System Component Failures**: Service crashes, database issues, network problems  
- **Data Inconsistencies**: Synchronization errors, calculation mistakes
- **Security Incidents**: Unauthorized access attempts, API key compromise

**Recovery Procedures:**
- **Automated Recovery**: Retry logic, circuit breakers, fallback mechanisms
- **Manual Intervention**: Administrator notification and guided resolution
- **Emergency Protocols**: Position closure, trading halt, user communication

---

## 📈 Scalability Use Cases

### UC-018: Platform Growth Management

**Growth Scenarios:**
1. **User Base Expansion**: 100 → 1,000 → 10,000 users
2. **Strategy Diversification**: 5 → 20 → 50 strategies  
3. **Exchange Integration**: 2 → 5 → 10 exchanges
4. **Geographic Expansion**: Single region → Multi-region deployment

**Scalability Measures:**
- **Horizontal Scaling**: Microservices scale independently based on demand
- **Data Partitioning**: User data sharded across multiple database instances
- **Caching Strategy**: Multi-level caching for frequently accessed data
- **CDN Integration**: Global content delivery for static assets and documentation

### UC-019: Performance Optimization

**Optimization Targets:**
- **Response Time**: Portfolio queries under 500ms (99th percentile)
- **Throughput**: 10,000+ concurrent users with <1% error rate
- **Latency**: Order placement under 100ms end-to-end
- **Availability**: 99.99% uptime with graceful degradation

**Performance Monitoring:**
- **Real-time Metrics**: Response times, error rates, resource utilization
- **Alerting**: Automated alerts for performance degradation
- **Capacity Planning**: Predictive scaling based on usage patterns
- **Optimization**: Continuous performance tuning and bottleneck resolution

---

> **Use Case Coverage Status:**
> - ✅ **Primary User Journeys**: Complete end-to-end scenarios documented
> - ✅ **Administrator Functions**: Comprehensive system management use cases
> - ✅ **Integration Patterns**: External system interaction scenarios  
> - ✅ **Error Handling**: Exception scenarios and recovery procedures
> - ✅ **Security & Compliance**: Audit trails and regulatory requirements
> - ✅ **Business Processes**: Revenue generation and customer lifecycle
> - ✅ **Scalability Scenarios**: Growth management and performance optimization

> **Business Value Alignment:**
> 1. **User Experience**: Intuitive Telegram interface with comprehensive portfolio management
> 2. **Risk Management**: Proactive monitoring and automated protection mechanisms
> 3. **Operational Efficiency**: Automated processes with minimal manual intervention
> 4. **Revenue Generation**: Clear profit-sharing model with transparent fee structure
> 5. **Regulatory Compliance**: Complete audit trails and secure data handling
> 6. **Platform Scalability**: Architecture supports 10x user growth without redesign

> **Next Steps:**
> 1. Validate use cases with stakeholders and users
> 2. Map use cases to component specifications and API requirements  
> 3. Create detailed user journey wireframes and prototypes
> 4. Develop comprehensive test scenarios based on use cases
> 5. Establish success metrics and KPIs for each use case category
