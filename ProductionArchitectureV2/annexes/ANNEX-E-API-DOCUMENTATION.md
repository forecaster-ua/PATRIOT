# PATRIOT Trading System - API Documentation and Integration Examples

## 📋 Document Information

**Document ID**: ANNEX-E-API-DOCUMENTATION  
**Version**: 2.0  
**Date**: September 2025  
**Authors**: Solution Architecture Team, API Team  
**Status**: Draft  

> **Cross-References:**  
> - Component Specifications: [../03-COMPONENT-SPECIFICATIONS.md](../03-COMPONENT-SPECIFICATIONS.md)  
> - System Architecture: [../02-SYSTEM-ARCHITECTURE.md](../02-SYSTEM-ARCHITECTURE.md#api-design-patterns)  
> - Data Schemas: [ANNEX-A-DATA-SCHEMAS.md](ANNEX-A-DATA-SCHEMAS.md)  
> - Deployment Examples: [ANNEX-C-DEPLOYMENT-EXAMPLES.md](ANNEX-C-DEPLOYMENT-EXAMPLES.md)  
> - Use Cases: [ANNEX-D-USE-CASES.md](ANNEX-D-USE-CASES.md)

---

## 🎯 API Architecture Overview

The PATRIOT trading system exposes a comprehensive RESTful API designed for high-performance trading operations. The API follows OpenAPI 3.0 specifications with consistent patterns, comprehensive error handling, and production-ready security features.

### API Design Principles

#### 1. **RESTful Resource Design**
All APIs follow REST principles with clear resource hierarchies and standard HTTP methods.

#### 2. **Event-Driven Responses**  
Critical operations return immediately with event IDs for asynchronous tracking via WebSocket or polling endpoints.

#### 3. **Comprehensive Error Handling**
Standardized error responses with machine-readable codes and human-readable messages.

#### 4. **Rate Limiting & Security**
Built-in rate limiting, JWT authentication, and API key management for secure access.

---

## 🔐 Authentication and Authorization

### JWT Authentication Flow

```typescript
// Authentication endpoint
POST /api/v1/auth/login
Content-Type: application/json

{
  "telegram_id": 123456789,
  "username": "trader_user",
  "signature": "telegram_auth_signature"
}

// Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "refresh_token_here",
  "expires_in": 3600,
  "token_type": "Bearer",
  "user": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "trader_user",
    "risk_profile": "MEDIUM",
    "permissions": ["trade", "view_portfolio", "manage_accounts"]
  }
}
```

### API Key Management

```typescript
// Create API key for external integrations
POST /api/v1/auth/api-keys
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "Trading Bot API Key",
  "permissions": ["trade", "view_portfolio"],
  "rate_limit": {
    "requests_per_minute": 100,
    "requests_per_hour": 1000
  },
  "expires_at": "2024-12-31T23:59:59Z",
  "ip_whitelist": ["192.168.1.100", "10.0.0.0/8"]
}

// Response
{
  "api_key_id": "ak_550e8400e29b41d4a716446655440000",
  "api_key": "pak_live_abc123def456...",
  "api_secret": "sak_abc123def456...",
  "name": "Trading Bot API Key",
  "created_at": "2025-09-24T20:50:00Z",
  "permissions": ["trade", "view_portfolio"],
  "rate_limit": {
    "requests_per_minute": 100,
    "requests_per_hour": 1000
  }
}
```

### Authorization Headers

```bash
# JWT Token Authentication
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# API Key Authentication
Authorization: ApiKey pak_live_abc123def456...
X-API-Secret: sak_abc123def456...
X-API-Timestamp: 1695587400
X-API-Signature: calculated_hmac_signature
```

---

## 👤 User Management API

### OpenAPI Specification

```yaml
openapi: 3.0.3
info:
  title: PATRIOT User Management API
  version: 2.0.0
  description: User registration, profile management, and account operations

servers:
  - url: https://api.patriot-trading.com/api/v1
    description: Production server
  - url: https://staging-api.patriot-trading.com/api/v1
    description: Staging server

security:
  - BearerAuth: []
  - ApiKeyAuth: []

paths:
  /users:
    post:
      summary: Register new user
      description: Register a new user with Telegram authentication
      tags: [Users]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UserRegistrationRequest'
            examples:
              basic_user:
                summary: Basic user registration
                value:
                  telegram_id: 123456789
                  username: "crypto_trader"
                  email: "trader@example.com"
                  risk_profile: "MEDIUM"
      responses:
        '201':
          description: User registered successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserResponse'
        '400':
          description: Validation error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '409':
          description: User already exists
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /users/{user_id}:
    get:
      summary: Get user profile
      description: Retrieve user profile information
      tags: [Users]
      parameters:
        - name: user_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          example: "550e8400-e29b-41d4-a716-446655440000"
      responses:
        '200':
          description: User profile retrieved
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserResponse'
        '404':
          description: User not found

    put:
      summary: Update user profile
      description: Update user profile information
      tags: [Users]
      parameters:
        - name: user_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UserUpdateRequest'
      responses:
        '200':
          description: User updated successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserResponse'

  /users/{user_id}/accounts:
    get:
      summary: List user exchange accounts
      description: Get all exchange accounts for a user
      tags: [User Accounts]
      parameters:
        - name: user_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: exchange
          in: query
          schema:
            type: string
            enum: [BINANCE, BYBIT, OKX, MEXC]
        - name: is_active
          in: query
          schema:
            type: boolean
      responses:
        '200':
          description: Accounts retrieved successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  accounts:
                    type: array
                    items:
                      $ref: '#/components/schemas/UserAccountResponse'
                  total_count:
                    type: integer
                  page:
                    type: integer
                  page_size:
                    type: integer

    post:
      summary: Add exchange account
      description: Link a new exchange account to user
      tags: [User Accounts]
      parameters:
        - name: user_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UserAccountRequest'
            examples:
              binance_account:
                summary: Binance account
                value:
                  exchange: "BINANCE"
                  account_name: "Main Trading Account"
                  api_key: "binance_api_key_here"
                  api_secret: "binance_api_secret_here"
                  is_testnet: false
      responses:
        '201':
          description: Account added successfully
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserAccountResponse'

components:
  schemas:
    UserRegistrationRequest:
      type: object
      required: [telegram_id, username]
      properties:
        telegram_id:
          type: integer
          format: int64
          description: Telegram user ID
          example: 123456789
        username:
          type: string
          minLength: 3
          maxLength: 50
          pattern: '^[a-zA-Z0-9_]+$'
          description: Username (alphanumeric and underscore only)
          example: "crypto_trader"
        email:
          type: string
          format: email
          description: User email address (optional)
          example: "trader@example.com"
        risk_profile:
          type: string
          enum: [LOW, MEDIUM, HIGH, ULTRA_HIGH]
          default: MEDIUM
          description: User risk tolerance level

    UserResponse:
      type: object
      properties:
        user_id:
          type: string
          format: uuid
          description: Unique user identifier
        telegram_id:
          type: integer
          format: int64
        username:
          type: string
        email:
          type: string
          format: email
        status:
          type: string
          enum: [ACTIVE, SUSPENDED, CLOSED, PENDING_VERIFICATION]
        risk_profile:
          type: string
          enum: [LOW, MEDIUM, HIGH, ULTRA_HIGH]
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time
        account_summary:
          type: object
          properties:
            total_accounts:
              type: integer
            active_accounts:
              type: integer
            total_balance_usd:
              type: number
              format: decimal
            unrealized_pnl_usd:
              type: number
              format: decimal

  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    ApiKeyAuth:
      type: apiKey
      in: header
      name: Authorization
```

### User Management Examples

#### 1. Complete User Registration Flow

```typescript
// TypeScript/Node.js example
import axios from 'axios';

class PatriotUserAPI {
    private baseURL: string;
    private authToken?: string;

    constructor(baseURL: string) {
        this.baseURL = baseURL;
    }

    // Register new user
    async registerUser(userData: {
        telegram_id: number;
        username: string;
        email?: string;
        risk_profile?: 'LOW' | 'MEDIUM' | 'HIGH' | 'ULTRA_HIGH';
    }): Promise<UserResponse> {
        try {
            const response = await axios.post(`${this.baseURL}/users`, userData, {
                headers: {
                    'Content-Type': 'application/json',
                    'X-Request-ID': this.generateRequestId()
                }
            });
            
            return response.data;
        } catch (error) {
            if (axios.isAxiosError(error) && error.response) {
                throw new PatriotAPIError(error.response.data);
            }
            throw error;
        }
    }

    // Authenticate and get JWT token
    async authenticate(telegramId: number, signature: string): Promise<AuthResponse> {
        const response = await axios.post(`${this.baseURL}/auth/login`, {
            telegram_id: telegramId,
            signature: signature
        });
        
        this.authToken = response.data.access_token;
        return response.data;
    }

    // Get user profile
    async getUserProfile(userId: string): Promise<UserResponse> {
        const response = await axios.get(`${this.baseURL}/users/${userId}`, {
            headers: {
                'Authorization': `Bearer ${this.authToken}`
            }
        });
        
        return response.data;
    }

    // Add exchange account
    async addExchangeAccount(userId: string, accountData: {
        exchange: 'BINANCE' | 'BYBIT' | 'OKX' | 'MEXC';
        account_name: string;
        api_key: string;
        api_secret: string;
        passphrase?: string;
        is_testnet?: boolean;
    }): Promise<UserAccountResponse> {
        const response = await axios.post(
            `${this.baseURL}/users/${userId}/accounts`,
            accountData,
            {
                headers: {
                    'Authorization': `Bearer ${this.authToken}`,
                    'Content-Type': 'application/json'
                }
            }
        );
        
        return response.data;
    }

    private generateRequestId(): string {
        return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
}

// Usage example
const userAPI = new PatriotUserAPI('https://api.patriot-trading.com/api/v1');

async function onboardNewUser() {
    try {
        // 1. Register user
        const user = await userAPI.registerUser({
            telegram_id: 123456789,
            username: 'crypto_trader_pro',
            email: 'trader@example.com',
            risk_profile: 'MEDIUM'
        });
        
        console.log('User registered:', user.user_id);
        
        // 2. Authenticate
        const auth = await userAPI.authenticate(123456789, 'telegram_signature');
        console.log('Authentication successful');
        
        // 3. Add exchange account
        const account = await userAPI.addExchangeAccount(user.user_id, {
            exchange: 'BINANCE',
            account_name: 'Main Trading Account',
            api_key: 'your_binance_api_key',
            api_secret: 'your_binance_api_secret',
            is_testnet: false
        });
        
        console.log('Exchange account added:', account.account_id);
        
    } catch (error) {
        console.error('Onboarding failed:', error);
    }
}
```

#### 2. Python Integration Example

```python
import requests
import json
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class PatriotConfig:
    base_url: str
    timeout: int = 30
    max_retries: int = 3

class PatriotUserClient:
    def __init__(self, config: PatriotConfig):
        self.config = config
        self.session = requests.Session()
        self.session.timeout = config.timeout
        self.auth_token: Optional[str] = None
    
    def register_user(self, telegram_id: int, username: str, 
                     email: Optional[str] = None, 
                     risk_profile: str = 'MEDIUM') -> Dict[str, Any]:
        """Register a new user"""
        
        payload = {
            'telegram_id': telegram_id,
            'username': username,
            'risk_profile': risk_profile
        }
        
        if email:
            payload['email'] = email
        
        response = self._make_request(
            'POST', 
            '/users', 
            json=payload
        )
        
        return response.json()
    
    def authenticate(self, telegram_id: int, signature: str) -> Dict[str, Any]:
        """Authenticate user and get JWT token"""
        
        payload = {
            'telegram_id': telegram_id,
            'signature': signature
        }
        
        response = self._make_request(
            'POST',
            '/auth/login',
            json=payload
        )
        
        auth_data = response.json()
        self.auth_token = auth_data['access_token']
        
        # Update session headers
        self.session.headers.update({
            'Authorization': f"Bearer {self.auth_token}"
        })
        
        return auth_data
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile information"""
        
        response = self._make_request(
            'GET',
            f'/users/{user_id}'
        )
        
        return response.json()
    
    def add_exchange_account(self, user_id: str, exchange: str, 
                           account_name: str, api_key: str, 
                           api_secret: str, **kwargs) -> Dict[str, Any]:
        """Add exchange account to user"""
        
        payload = {
            'exchange': exchange,
            'account_name': account_name,
            'api_key': api_key,
            'api_secret': api_secret,
            **kwargs
        }
        
        response = self._make_request(
            'POST',
            f'/users/{user_id}/accounts',
            json=payload
        )
        
        return response.json()
    
    def update_risk_profile(self, user_id: str, risk_profile: str) -> Dict[str, Any]:
        """Update user risk profile"""
        
        payload = {
            'risk_profile': risk_profile
        }
        
        response = self._make_request(
            'PUT',
            f'/users/{user_id}',
            json=payload
        )
        
        return response.json()
    
    def _make_request(self, method: str, endpoint: str, 
                     **kwargs) -> requests.Response:
        """Make HTTP request with retry logic"""
        
        url = f"{self.config.base_url}{endpoint}"
        
        # Add common headers
        headers = kwargs.get('headers', {})
        headers.update({
            'Content-Type': 'application/json',
            'X-Request-ID': f"req_{int(time.time())}_{id(self)}",
            'User-Agent': 'PATRIOT-Python-Client/2.0'
        })
        kwargs['headers'] = headers
        
        # Retry logic
        last_exception = None
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < self.config.max_retries - 1:
                    # Exponential backoff
                    time.sleep(2 ** attempt)
                    continue
                break
        
        raise last_exception

# Usage example
config = PatriotConfig(base_url='https://api.patriot-trading.com/api/v1')
client = PatriotUserClient(config)

def demo_user_management():
    try:
        # Register new user
        user = client.register_user(
            telegram_id=987654321,
            username='python_trader',
            email='python@example.com',
            risk_profile='HIGH'
        )
        print(f"User registered: {user['user_id']}")
        
        # Authenticate
        auth_result = client.authenticate(987654321, 'signature_here')
        print(f"Authentication successful, token expires in {auth_result['expires_in']} seconds")
        
        # Get profile
        profile = client.get_user_profile(user['user_id'])
        print(f"User status: {profile['status']}")
        
        # Add Bybit account
        account = client.add_exchange_account(
            user_id=user['user_id'],
            exchange='BYBIT',
            account_name='Bybit Main Account',
            api_key='bybit_api_key',
            api_secret='bybit_api_secret',
            is_testnet=True
        )
        print(f"Exchange account added: {account['account_id']}")
        
        # Update risk profile
        updated_user = client.update_risk_profile(user['user_id'], 'ULTRA_HIGH')
        print(f"Risk profile updated to: {updated_user['risk_profile']}")
        
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e.response.status_code}")
        print(f"Error details: {e.response.json()}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    demo_user_management()
```

---

## 📊 Order Management API

### Order Lifecycle Operations

```yaml
# Order Management API Specification
paths:
  /orders:
    post:
      summary: Create new order
      description: Place a new trading order on connected exchange
      tags: [Orders]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/OrderRequest'
            examples:
              market_buy:
                summary: Market buy order
                value:
                  account_id: "550e8400-e29b-41d4-a716-446655440001"
                  symbol: "BTCUSDT"
                  side: "BUY"
                  type: "MARKET"
                  quantity: "0.001"
                  time_in_force: "IOC"
              limit_sell:
                summary: Limit sell order
                value:
                  account_id: "550e8400-e29b-41d4-a716-446655440001"
                  symbol: "ETHUSDT"
                  side: "SELL"
                  type: "LIMIT"
                  quantity: "0.1"
                  price: "2500.50"
                  time_in_force: "GTC"
              stop_loss:
                summary: Stop loss order
                value:
                  account_id: "550e8400-e29b-41d4-a716-446655440001"
                  symbol: "ADAUSDT"
                  side: "SELL"
                  type: "STOP_MARKET"
                  quantity: "100"
                  stop_price: "0.45"
                  reduce_only: true
      responses:
        '201':
          description: Order created successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  order_id:
                    type: string
                    format: uuid
                  status:
                    type: string
                    enum: [PENDING, NEW, PARTIALLY_FILLED, FILLED, CANCELLED, REJECTED]
                  exchange_order_id:
                    type: string
                  created_at:
                    type: string
                    format: date-time
                  event_id:
                    type: string
                    description: Event ID for tracking order updates
        '400':
          description: Invalid order request
        '403':
          description: Risk limits exceeded
        '429':
          description: Rate limit exceeded

    get:
      summary: List orders
      description: Get orders with filtering and pagination
      tags: [Orders]
      parameters:
        - name: account_id
          in: query
          schema:
            type: string
            format: uuid
        - name: symbol
          in: query
          schema:
            type: string
        - name: status
          in: query
          schema:
            type: string
            enum: [PENDING, NEW, PARTIALLY_FILLED, FILLED, CANCELLED, REJECTED]
        - name: side
          in: query
          schema:
            type: string
            enum: [BUY, SELL]
        - name: from_date
          in: query
          schema:
            type: string
            format: date-time
        - name: to_date
          in: query
          schema:
            type: string
            format: date-time
        - name: page
          in: query
          schema:
            type: integer
            minimum: 1
            default: 1
        - name: page_size
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 50
      responses:
        '200':
          description: Orders retrieved successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  orders:
                    type: array
                    items:
                      $ref: '#/components/schemas/OrderResponse'
                  pagination:
                    $ref: '#/components/schemas/PaginationInfo'

  /orders/{order_id}:
    get:
      summary: Get order details
      description: Retrieve detailed information about a specific order
      tags: [Orders]
      parameters:
        - name: order_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Order details retrieved
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/OrderResponse'
                  - type: object
                    properties:
                      fills:
                        type: array
                        items:
                          $ref: '#/components/schemas/OrderFillResponse'
                      risk_checks:
                        type: array
                        items:
                          $ref: '#/components/schemas/RiskCheckResponse'

    put:
      summary: Modify order
      description: Modify an existing order (price, quantity, etc.)
      tags: [Orders]
      parameters:
        - name: order_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                quantity:
                  type: string
                  description: New order quantity
                price:
                  type: string
                  description: New order price (for limit orders)
                stop_price:
                  type: string
                  description: New stop price (for stop orders)
      responses:
        '200':
          description: Order modified successfully
        '400':
          description: Invalid modification request
        '404':
          description: Order not found
        '409':
          description: Order cannot be modified in current state

    delete:
      summary: Cancel order
      description: Cancel an existing order
      tags: [Orders]
      parameters:
        - name: order_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Order cancelled successfully
        '404':
          description: Order not found
        '409':
          description: Order cannot be cancelled in current state

components:
  schemas:
    OrderRequest:
      type: object
      required: [account_id, symbol, side, type, quantity]
      properties:
        account_id:
          type: string
          format: uuid
          description: Exchange account to place order on
        strategy_id:
          type: string
          format: uuid
          description: Strategy ID (if order is strategy-generated)
        symbol:
          type: string
          pattern: '^[A-Z]{3,10}USDT$'
          description: Trading pair symbol
        side:
          type: string
          enum: [BUY, SELL]
        type:
          type: string
          enum: [MARKET, LIMIT, STOP_MARKET, STOP_LIMIT, TAKE_PROFIT, TAKE_PROFIT_LIMIT]
        quantity:
          type: string
          pattern: '^[0-9]+\\.?[0-9]*$'
          description: Order quantity (as string to preserve precision)
        price:
          type: string
          pattern: '^[0-9]+\\.?[0-9]*$'
          description: Order price (required for limit orders)
        stop_price:
          type: string
          pattern: '^[0-9]+\\.?[0-9]*$'
          description: Stop price (required for stop orders)
        time_in_force:
          type: string
          enum: [GTC, IOC, FOK]
          default: GTC
        reduce_only:
          type: boolean
          default: false
          description: Reduce-only order flag
        post_only:
          type: boolean
          default: false
          description: Post-only order flag
        client_order_id:
          type: string
          maxLength: 64
          description: Client-provided order ID

    OrderResponse:
      type: object
      properties:
        order_id:
          type: string
          format: uuid
        user_id:
          type: string
          format: uuid
        account_id:
          type: string
          format: uuid
        strategy_id:
          type: string
          format: uuid
        exchange_order_id:
          type: string
        client_order_id:
          type: string
        symbol:
          type: string
        side:
          type: string
          enum: [BUY, SELL]
        type:
          type: string
          enum: [MARKET, LIMIT, STOP_MARKET, STOP_LIMIT, TAKE_PROFIT, TAKE_PROFIT_LIMIT]
        quantity:
          type: string
        price:
          type: string
        stop_price:
          type: string
        filled_quantity:
          type: string
        avg_fill_price:
          type: string
        commission:
          type: string
        commission_asset:
          type: string
        status:
          type: string
          enum: [PENDING, NEW, PARTIALLY_FILLED, FILLED, CANCELLED, REJECTED]
        time_in_force:
          type: string
          enum: [GTC, IOC, FOK]
        reduce_only:
          type: boolean
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time
        filled_at:
          type: string
          format: date-time
```

### Advanced Order Management Examples

```typescript
// Advanced order management client
class PatriotOrderAPI {
    private client: PatriotAPIClient;

    constructor(client: PatriotAPIClient) {
        this.client = client;
    }

    // Place market order with risk checks
    async placeMarketOrder(params: {
        account_id: string;
        symbol: string;
        side: 'BUY' | 'SELL';
        quantity: string;
        reduce_only?: boolean;
    }): Promise<OrderResponse> {
        const orderRequest: OrderRequest = {
            account_id: params.account_id,
            symbol: params.symbol,
            side: params.side,
            type: 'MARKET',
            quantity: params.quantity,
            time_in_force: 'IOC',
            reduce_only: params.reduce_only || false
        };

        // Pre-flight risk check
        await this.performRiskCheck(orderRequest);

        const response = await this.client.post('/orders', orderRequest);
        
        // Track order asynchronously
        this.trackOrderUpdates(response.order_id);
        
        return response;
    }

    // Place advanced limit order with conditional logic
    async placeLimitOrderWithConditions(params: {
        account_id: string;
        symbol: string;
        side: 'BUY' | 'SELL';
        quantity: string;
        price: string;
        conditions?: {
            stop_loss?: string;
            take_profit?: string;
            max_slippage?: string;
        };
    }): Promise<{ 
        primary_order: OrderResponse; 
        conditional_orders?: OrderResponse[] 
    }> {
        const results: { primary_order: OrderResponse; conditional_orders?: OrderResponse[] } = {
            primary_order: null as any
        };

        // Place primary limit order
        const primaryOrder: OrderRequest = {
            account_id: params.account_id,
            symbol: params.symbol,
            side: params.side,
            type: 'LIMIT',
            quantity: params.quantity,
            price: params.price,
            time_in_force: 'GTC'
        };

        results.primary_order = await this.client.post('/orders', primaryOrder);

        // Place conditional orders if specified
        if (params.conditions) {
            results.conditional_orders = [];

            // Stop loss order
            if (params.conditions.stop_loss) {
                const stopLossOrder: OrderRequest = {
                    account_id: params.account_id,
                    symbol: params.symbol,
                    side: params.side === 'BUY' ? 'SELL' : 'BUY',
                    type: 'STOP_MARKET',
                    quantity: params.quantity,
                    stop_price: params.conditions.stop_loss,
                    reduce_only: true
                };

                const stopLoss = await this.client.post('/orders', stopLossOrder);
                results.conditional_orders.push(stopLoss);
            }

            // Take profit order
            if (params.conditions.take_profit) {
                const takeProfitOrder: OrderRequest = {
                    account_id: params.account_id,
                    symbol: params.symbol,
                    side: params.side === 'BUY' ? 'SELL' : 'BUY',
                    type: 'TAKE_PROFIT',
                    quantity: params.quantity,
                    stop_price: params.conditions.take_profit,
                    reduce_only: true
                };

                const takeProfit = await this.client.post('/orders', takeProfitOrder);
                results.conditional_orders.push(takeProfit);
            }
        }

        return results;
    }

    // Batch order operations
    async batchOperations(operations: Array<{
        operation: 'CREATE' | 'MODIFY' | 'CANCEL';
        order_id?: string;
        order_data?: OrderRequest;
        modify_data?: { quantity?: string; price?: string; stop_price?: string };
    }>): Promise<BatchOrderResponse> {
        const results: BatchOrderResponse = {
            success: [],
            failed: [],
            total: operations.length
        };

        // Execute operations in parallel with concurrency limit
        const concurrencyLimit = 5;
        const chunks = this.chunkArray(operations, concurrencyLimit);

        for (const chunk of chunks) {
            const promises = chunk.map(async (op, index) => {
                try {
                    let result: any;
                    
                    switch (op.operation) {
                        case 'CREATE':
                            result = await this.client.post('/orders', op.order_data);
                            break;
                        case 'MODIFY':
                            result = await this.client.put(`/orders/${op.order_id}`, op.modify_data);
                            break;
                        case 'CANCEL':
                            result = await this.client.delete(`/orders/${op.order_id}`);
                            break;
                    }

                    results.success.push({
                        operation: op.operation,
                        order_id: result.order_id || op.order_id,
                        result: result
                    });

                } catch (error) {
                    results.failed.push({
                        operation: op.operation,
                        order_id: op.order_id,
                        error: error.message,
                        error_code: error.code
                    });
                }
            });

            await Promise.allSettled(promises);
        }

        return results;
    }

    // Smart order routing with price improvement
    async placeSmartOrder(params: {
        symbol: string;
        side: 'BUY' | 'SELL';
        quantity: string;
        max_slippage_bps?: number;
        time_limit_ms?: number;
        accounts?: string[]; // Multiple accounts for routing
    }): Promise<SmartOrderResponse> {
        const maxSlippage = params.max_slippage_bps || 50; // 0.5% default
        const timeLimit = params.time_limit_ms || 30000; // 30 seconds default
        
        // Get market data and determine optimal execution strategy
        const marketData = await this.client.get(`/market/depth/${params.symbol}`);
        const bestPrice = params.side === 'BUY' ? marketData.asks[0].price : marketData.bids[0].price;
        
        // Calculate price impact and determine if we need to split the order
        const priceImpact = this.calculatePriceImpact(params.quantity, marketData, params.side);
        
        if (priceImpact > maxSlippage) {
            // Split into smaller orders using TWAP strategy
            return await this.executeTWAPStrategy(params, marketData);
        } else {
            // Single order execution
            const account_id = params.accounts?.[0] || await this.getOptimalAccount(params.symbol);
            
            return {
                strategy: 'SINGLE_ORDER',
                orders: [await this.placeMarketOrder({
                    account_id,
                    symbol: params.symbol,
                    side: params.side,
                    quantity: params.quantity
                })],
                total_quantity: params.quantity,
                avg_price: bestPrice,
                total_commission: '0', // Will be updated after fills
                execution_time_ms: 0
            };
        }
    }

    // Track order updates via WebSocket
    private trackOrderUpdates(orderId: string): void {
        const ws = this.client.createWebSocket();
        
        ws.send(JSON.stringify({
            action: 'subscribe',
            channel: 'order_updates',
            filters: {
                order_ids: [orderId]
            }
        }));

        ws.onmessage = (event) => {
            const update = JSON.parse(event.data);
            
            if (update.channel === 'order_updates' && update.data.order_id === orderId) {
                // Handle order update
                this.handleOrderUpdate(update.data);
            }
        };
    }

    private async performRiskCheck(order: OrderRequest): Promise<void> {
        const riskCheck = await this.client.post('/risk/check', {
            account_id: order.account_id,
            symbol: order.symbol,
            side: order.side,
            quantity: order.quantity,
            price: order.price
        });

        if (!riskCheck.approved) {
            throw new Error(`Risk check failed: ${riskCheck.reason}`);
        }
    }

    private calculatePriceImpact(quantity: string, marketData: any, side: string): number {
        // Implementation of price impact calculation
        const orderValue = parseFloat(quantity);
        const book = side === 'BUY' ? marketData.asks : marketData.bids;
        
        let totalQuantity = 0;
        let totalValue = 0;
        
        for (const level of book) {
            const levelQuantity = Math.min(parseFloat(level.quantity), orderValue - totalQuantity);
            totalQuantity += levelQuantity;
            totalValue += levelQuantity * parseFloat(level.price);
            
            if (totalQuantity >= orderValue) break;
        }
        
        const avgPrice = totalValue / totalQuantity;
        const bestPrice = parseFloat(book[0].price);
        
        return Math.abs((avgPrice - bestPrice) / bestPrice) * 10000; // in basis points
    }

    private chunkArray<T>(array: T[], chunkSize: number): T[][] {
        const chunks: T[][] = [];
        for (let i = 0; i < array.length; i += chunkSize) {
            chunks.push(array.slice(i, i + chunkSize));
        }
        return chunks;
    }
}

// Usage examples
async function demonstrateOrderManagement() {
    const client = new PatriotAPIClient('https://api.patriot-trading.com/api/v1');
    await client.authenticate('your_jwt_token');
    
    const orderAPI = new PatriotOrderAPI(client);

    try {
        // 1. Simple market buy
        const marketOrder = await orderAPI.placeMarketOrder({
            account_id: 'account-uuid-here',
            symbol: 'BTCUSDT',
            side: 'BUY',
            quantity: '0.001'
        });
        console.log('Market order placed:', marketOrder.order_id);

        // 2. Advanced limit order with stop loss and take profit
        const advancedOrder = await orderAPI.placeLimitOrderWithConditions({
            account_id: 'account-uuid-here',
            symbol: 'ETHUSDT',
            side: 'BUY',
            quantity: '0.1',
            price: '2400.00',
            conditions: {
                stop_loss: '2300.00',
                take_profit: '2600.00'
            }
        });
        console.log('Advanced order placed:', {
            primary: advancedOrder.primary_order.order_id,
            conditionals: advancedOrder.conditional_orders?.map(o => o.order_id)
        });

        // 3. Batch operations
        const batchResult = await orderAPI.batchOperations([
            {
                operation: 'CREATE',
                order_data: {
                    account_id: 'account-uuid-here',
                    symbol: 'ADAUSDT',
                    side: 'BUY',
                    type: 'LIMIT',
                    quantity: '100',
                    price: '0.50'
                }
            },
            {
                operation: 'MODIFY',
                order_id: 'existing-order-uuid',
                modify_data: { price: '0.52' }
            },
            {
                operation: 'CANCEL',
                order_id: 'order-to-cancel-uuid'
            }
        ]);
        console.log('Batch operations:', {
            successful: batchResult.success.length,
            failed: batchResult.failed.length
        });

        // 4. Smart order with optimal routing
        const smartOrder = await orderAPI.placeSmartOrder({
            symbol: 'BTCUSDT',
            side: 'BUY',
            quantity: '1.0', // Large order that might need splitting
            max_slippage_bps: 30, // 0.3% max slippage
            accounts: ['account1-uuid', 'account2-uuid'] // Multiple accounts for routing
        });
        console.log('Smart order executed:', {
            strategy: smartOrder.strategy,
            orders: smartOrder.orders.length,
            avg_price: smartOrder.avg_price
        });

    } catch (error) {
        console.error('Order management error:', error);
    }
}
```

---

## 💰 Portfolio Management API

### Portfolio Queries and Analytics

```yaml
# Portfolio Management API
paths:
  /portfolio/summary:
    get:
      summary: Get portfolio summary
      description: Retrieve comprehensive portfolio summary across all accounts
      tags: [Portfolio]
      parameters:
        - name: user_id
          in: query
          schema:
            type: string
            format: uuid
        - name: as_of_date
          in: query
          schema:
            type: string
            format: date-time
        - name: include_history
          in: query
          schema:
            type: boolean
            default: false
      responses:
        '200':
          description: Portfolio summary retrieved
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PortfolioSummaryResponse'

  /portfolio/positions:
    get:
      summary: Get current positions
      description: List all current positions across accounts
      tags: [Portfolio]
      parameters:
        - name: account_id
          in: query
          schema:
            type: string
            format: uuid
        - name: symbol
          in: query
          schema:
            type: string
        - name: min_value_usd
          in: query
          schema:
            type: number
            minimum: 0
      responses:
        '200':
          description: Positions retrieved
          content:
            application/json:
              schema:
                type: object
                properties:
                  positions:
                    type: array
                    items:
                      $ref: '#/components/schemas/PositionResponse'
                  total_value_usd:
                    type: number
                  unrealized_pnl_usd:
                    type: number

  /portfolio/performance:
    get:
      summary: Get performance metrics
      description: Retrieve detailed performance analytics
      tags: [Portfolio]
      parameters:
        - name: user_id
          in: query
          schema:
            type: string
            format: uuid
        - name: period
          in: query
          schema:
            type: string
            enum: [1H, 4H, 1D, 7D, 30D, 90D, 1Y, ALL]
            default: 30D
        - name: benchmark
          in: query
          schema:
            type: string
            enum: [BTC, ETH, SPY]
        - name: granularity
          in: query
          schema:
            type: string
            enum: [HOURLY, DAILY, WEEKLY]
            default: DAILY
      responses:
        '200':
          description: Performance metrics retrieved
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PerformanceResponse'

  /portfolio/analytics/risk:
    get:
      summary: Get risk analytics
      description: Comprehensive risk analysis of portfolio
      tags: [Portfolio, Risk]
      parameters:
        - name: user_id
          in: query
          schema:
            type: string
            format: uuid
        - name: confidence_level
          in: query
          schema:
            type: number
            minimum: 0.9
            maximum: 0.99
            default: 0.95
        - name: time_horizon_hours
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 720
            default: 24
      responses:
        '200':
          description: Risk analytics retrieved
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RiskAnalyticsResponse'

components:
  schemas:
    PortfolioSummaryResponse:
      type: object
      properties:
        user_id:
          type: string
          format: uuid
        as_of_date:
          type: string
          format: date-time
        total_balance_usd:
          type: number
          format: decimal
        available_balance_usd:
          type: number
          format: decimal
        margin_balance_usd:
          type: number
          format: decimal
        unrealized_pnl_usd:
          type: number
          format: decimal
        realized_pnl_usd:
          type: number
          format: decimal
        total_positions:
          type: integer
        active_orders:
          type: integer
        accounts:
          type: array
          items:
            type: object
            properties:
              account_id:
                type: string
                format: uuid
              exchange:
                type: string
              balance_usd:
                type: number
              unrealized_pnl_usd:
                type: number
              position_count:
                type: integer
        daily_change:
          type: object
          properties:
            absolute_usd:
              type: number
            percentage:
              type: number
        risk_metrics:
          type: object
          properties:
            var_95_usd:
              type: number
            max_drawdown_usd:
              type: number
            leverage_ratio:
              type: number
            margin_ratio:
              type: number

    PositionResponse:
      type: object
      properties:
        position_id:
          type: string
        account_id:
          type: string
          format: uuid
        symbol:
          type: string
        side:
          type: string
          enum: [LONG, SHORT]
        size:
          type: string
          description: Position size in base asset
        entry_price:
          type: string
        mark_price:
          type: string
        unrealized_pnl_usd:
          type: number
        unrealized_pnl_percentage:
          type: number
        margin_used_usd:
          type: number
        leverage:
          type: number
        liquidation_price:
          type: string
        created_at:
          type: string
          format: date-time
        updated_at:
          type: string
          format: date-time

    PerformanceResponse:
      type: object
      properties:
        user_id:
          type: string
          format: uuid
        period:
          type: string
        start_date:
          type: string
          format: date-time
        end_date:
          type: string
          format: date-time
        total_return:
          type: object
          properties:
            absolute_usd:
              type: number
            percentage:
              type: number
        metrics:
          type: object
          properties:
            total_trades:
              type: integer
            winning_trades:
              type: integer
            losing_trades:
              type: integer
            win_rate:
              type: number
            profit_factor:
              type: number
            sharpe_ratio:
              type: number
            sortino_ratio:
              type: number
            calmar_ratio:
              type: number
            max_drawdown:
              type: object
              properties:
                absolute_usd:
                  type: number
                percentage:
                  type: number
                duration_days:
                  type: integer
            volatility:
              type: number
        time_series:
          type: array
          items:
            type: object
            properties:
              timestamp:
                type: string
                format: date-time
              portfolio_value:
                type: number
              daily_return:
                type: number
              cumulative_return:
                type: number
        benchmark_comparison:
          type: object
          properties:
            benchmark:
              type: string
            portfolio_return:
              type: number
            benchmark_return:
              type: number
            alpha:
              type: number
            beta:
              type: number
            correlation:
              type: number

    RiskAnalyticsResponse:
      type: object
      properties:
        user_id:
          type: string
          format: uuid
        as_of_date:
          type: string
          format: date-time
        confidence_level:
          type: number
        time_horizon_hours:
          type: integer
        risk_metrics:
          type: object
          properties:
            var_usd:
              type: number
              description: Value at Risk in USD
            cvar_usd:
              type: number
              description: Conditional Value at Risk in USD
            portfolio_volatility:
              type: number
            diversification_ratio:
              type: number
            concentration_risk:
              type: number
        position_risks:
          type: array
          items:
            type: object
            properties:
              symbol:
                type: string
              position_var_usd:
                type: number
              marginal_var_usd:
                type: number
              component_var_usd:
                type: number
              risk_contribution_percentage:
                type: number
        correlation_matrix:
          type: object
          additionalProperties:
            type: object
            additionalProperties:
              type: number
        stress_tests:
          type: array
          items:
            type: object
            properties:
              scenario:
                type: string
              portfolio_impact_usd:
                type: number
              portfolio_impact_percentage:
                type: number
```

### Portfolio Management Implementation

```python
# Portfolio management client implementation
import asyncio
import pandas as pd
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

class PatriotPortfolioClient:
    def __init__(self, api_client):
        self.api_client = api_client
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    async def get_portfolio_summary(self, user_id: str, 
                                   as_of_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        
        params = {'user_id': user_id}
        if as_of_date:
            params['as_of_date'] = as_of_date.isoformat()
        
        response = await self.api_client.get('/portfolio/summary', params=params)
        
        # Cache the result
        cache_key = f"portfolio_summary_{user_id}_{as_of_date or 'latest'}"
        self.cache[cache_key] = {
            'data': response,
            'timestamp': datetime.now()
        }
        
        return response
    
    async def get_positions(self, account_id: Optional[str] = None,
                          symbol: Optional[str] = None,
                          min_value_usd: Optional[float] = None) -> List[Dict[str, Any]]:
        """Get current positions with optional filtering"""
        
        params = {}
        if account_id:
            params['account_id'] = account_id
        if symbol:
            params['symbol'] = symbol
        if min_value_usd:
            params['min_value_usd'] = min_value_usd
        
        response = await self.api_client.get('/portfolio/positions', params=params)
        return response['positions']
    
    async def get_performance_metrics(self, user_id: str, period: str = '30D',
                                    benchmark: Optional[str] = None,
                                    granularity: str = 'DAILY') -> Dict[str, Any]:
        """Get detailed performance analytics"""
        
        params = {
            'user_id': user_id,
            'period': period,
            'granularity': granularity
        }
        if benchmark:
            params['benchmark'] = benchmark
        
        response = await self.api_client.get('/portfolio/performance', params=params)
        
        # Convert time series to pandas DataFrame for easier analysis
        if 'time_series' in response:
            df = pd.DataFrame(response['time_series'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            response['time_series_df'] = df
        
        return response
    
    async def get_risk_analytics(self, user_id: str, 
                               confidence_level: float = 0.95,
                               time_horizon_hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive risk analysis"""
        
        params = {
            'user_id': user_id,
            'confidence_level': confidence_level,
            'time_horizon_hours': time_horizon_hours
        }
        
        response = await self.api_client.get('/portfolio/analytics/risk', params=params)
        
        # Process correlation matrix into pandas DataFrame
        if 'correlation_matrix' in response:
            corr_data = response['correlation_matrix']
            symbols = list(corr_data.keys())
            corr_matrix = [[corr_data[s1][s2] for s2 in symbols] for s1 in symbols]
            response['correlation_df'] = pd.DataFrame(
                corr_matrix, 
                index=symbols, 
                columns=symbols
            )
        
        return response
    
    async def generate_portfolio_report(self, user_id: str, 
                                      period: str = '30D') -> Dict[str, Any]:
        """Generate comprehensive portfolio report"""
        
        # Gather all data in parallel
        tasks = [
            self.get_portfolio_summary(user_id),
            self.get_positions(),
            self.get_performance_metrics(user_id, period),
            self.get_risk_analytics(user_id)
        ]
        
        summary, positions, performance, risk = await asyncio.gather(*tasks)
        
        # Calculate additional metrics
        report = {
            'generated_at': datetime.now().isoformat(),
            'period': period,
            'summary': summary,
            'positions': positions,
            'performance': performance,
            'risk': risk,
            'insights': self._generate_insights(summary, positions, performance, risk)
        }
        
        return report
    
    def _generate_insights(self, summary: Dict, positions: List[Dict], 
                         performance: Dict, risk: Dict) -> List[Dict[str, str]]:
        """Generate actionable insights from portfolio data"""
        
        insights = []
        
        # Portfolio concentration insights
        total_value = summary['total_balance_usd']
        position_values = [p['size'] * p['mark_price'] for p in positions if p.get('mark_price')]
        
        if position_values:
            max_position_value = max(position_values)
            concentration = max_position_value / total_value
            
            if concentration > 0.3:
                insights.append({
                    'type': 'WARNING',
                    'category': 'CONCENTRATION',
                    'message': f'Portfolio is heavily concentrated ({concentration:.1%}) in a single position. Consider diversification.'
                })
        
        # Performance insights
        if 'metrics' in performance:
            win_rate = performance['metrics'].get('win_rate', 0)
            sharpe_ratio = performance['metrics'].get('sharpe_ratio', 0)
            
            if win_rate < 0.4:
                insights.append({
                    'type': 'INFO',
                    'category': 'PERFORMANCE',
                    'message': f'Win rate is {win_rate:.1%}. Consider reviewing trading strategy.'
                })
            
            if sharpe_ratio > 2.0:
                insights.append({
                    'type': 'SUCCESS',
                    'category': 'PERFORMANCE',
                    'message': f'Excellent risk-adjusted returns (Sharpe: {sharpe_ratio:.2f}).'
                })
        
        # Risk insights
        if 'risk_metrics' in risk:
            var_percentage = risk['risk_metrics']['var_usd'] / total_value
            
            if var_percentage > 0.05:  # 5% VaR
                insights.append({
                    'type': 'WARNING',
                    'category': 'RISK',
                    'message': f'High portfolio risk (VaR: {var_percentage:.1%}). Consider reducing leverage or diversifying.'
                })
        
        return insights
    
    async def optimize_portfolio(self, user_id: str, 
                               optimization_method: str = 'SHARPE',
                               constraints: Optional[Dict] = None) -> Dict[str, Any]:
        """Portfolio optimization suggestions"""
        
        # Get current portfolio data
        current_positions = await self.get_positions()
        risk_data = await self.get_risk_analytics(user_id)
        
        # This would integrate with portfolio optimization algorithms
        # For now, return basic rebalancing suggestions
        
        suggestions = []
        
        # Calculate current allocation
        total_value = sum(float(p['size']) * float(p['mark_price']) 
                         for p in current_positions if p.get('mark_price'))
        
        allocations = {}
        for position in current_positions:
            symbol = position['symbol']
            value = float(position['size']) * float(position['mark_price'])
            allocations[symbol] = value / total_value
        
        # Simple rebalancing logic (in production, use sophisticated optimization)
        target_allocations = self._calculate_target_allocations(
            allocations, risk_data, optimization_method
        )
        
        for symbol, current_alloc in allocations.items():
            target_alloc = target_allocations.get(symbol, current_alloc)
            diff = target_alloc - current_alloc
            
            if abs(diff) > 0.05:  # 5% threshold
                suggestions.append({
                    'symbol': symbol,
                    'current_allocation': current_alloc,
                    'target_allocation': target_alloc,
                    'action': 'INCREASE' if diff > 0 else 'DECREASE',
                    'amount_usd': abs(diff) * total_value
                })
        
        return {
            'optimization_method': optimization_method,
            'current_allocations': allocations,
            'target_allocations': target_allocations,
            'suggestions': suggestions,
            'expected_improvement': self._calculate_expected_improvement(
                current_positions, suggestions
            )
        }
    
    def _calculate_target_allocations(self, current_allocations: Dict, 
                                    risk_data: Dict, method: str) -> Dict[str, float]:
        """Calculate target allocations based on optimization method"""
        
        if method == 'EQUAL_WEIGHT':
            # Equal weight allocation
            n_assets = len(current_allocations)
            return {symbol: 1.0 / n_assets for symbol in current_allocations}
        
        elif method == 'RISK_PARITY':
            # Risk parity allocation (inverse volatility weighting)
            if 'position_risks' in risk_data:
                risks = {pr['symbol']: pr['position_var_usd'] 
                        for pr in risk_data['position_risks']}
                
                total_inv_risk = sum(1/risk for risk in risks.values() if risk > 0)
                
                return {symbol: (1/risk) / total_inv_risk 
                       for symbol, risk in risks.items() if risk > 0}
        
        # Default: maintain current allocations
        return current_allocations
    
    def _calculate_expected_improvement(self, positions: List, suggestions: List) -> Dict:
        """Calculate expected portfolio improvement from suggestions"""
        
        # Simplified calculation - in production use proper portfolio theory
        total_rebalance_amount = sum(s['amount_usd'] for s in suggestions)
        expected_risk_reduction = min(0.1, total_rebalance_amount / 100000)  # Max 10% risk reduction
        
        return {
            'expected_sharpe_improvement': expected_risk_reduction * 0.5,
            'expected_risk_reduction_percentage': expected_risk_reduction,
            'rebalancing_cost_estimate_usd': total_rebalance_amount * 0.001  # 0.1% transaction cost
        }

# Usage example
async def portfolio_analysis_demo():
    api_client = PatriotAPIClient('https://api.patriot-trading.com/api/v1')
    await api_client.authenticate('your_jwt_token')
    
    portfolio_client = PatriotPortfolioClient(api_client)
    user_id = 'your-user-id-here'
    
    try:
        # Get comprehensive portfolio report
        report = await portfolio_client.generate_portfolio_report(user_id, '30D')
        
        print("=== Portfolio Report ===")
        print(f"Total Balance: ${report['summary']['total_balance_usd']:,.2f}")
        print(f"Unrealized P&L: ${report['summary']['unrealized_pnl_usd']:,.2f}")
        print(f"Number of Positions: {len(report['positions'])}")
        
        # Performance metrics
        perf = report['performance']['metrics']
        print(f"\
=== Performance (30D) ===")
        print(f"Total Trades: {perf['total_trades']}")
        print(f"Win Rate: {perf['win_rate']:.1%}")
        print(f"Sharpe Ratio: {perf['sharpe_ratio']:.2f}")
        print(f"Max Drawdown: {perf['max_drawdown']['percentage']:.2%}")
        
        # Risk metrics
        risk = report['risk']['risk_metrics']
        print(f"\=== Risk Analytics ===")
        print(f"VaR (95%): ${risk['var_usd']:,.2f}")
        print(f"Portfolio Volatility: {risk['portfolio_volatility']:.2%}")
        print(f"Concentration Risk: {risk['concentration_risk']:.2%}")
        
        # Insights
        print(f"\=== Insights ===")
        for insight in report['insights']:
            print(f"[{insight['type']}] {insight['message']}")
        
        # Portfolio optimization suggestions
        optimization = await portfolio_client.optimize_portfolio(user_id, 'SHARPE')
        
        print(f"=== Optimization Suggestions ===")
        for suggestion in optimization['suggestions']:
            print(f"{suggestion['symbol']}: {suggestion['action']} by ${suggestion['amount_usd']:,.2f}")
        
        expected = optimization['expected_improvement']
        print(f"Expected Sharpe Improvement: +{expected['expected_sharpe_improvement']:.2f}")
        print(f"Expected Risk Reduction: -{expected['expected_risk_reduction_percentage']:.1%}")
        
    except Exception as e:
        print(f"Portfolio analysis error: {e}")

if __name__ == "__main__":
    asyncio.run(portfolio_analysis_demo())
```

---

## 📊 Real-Time Data Streaming API

### WebSocket API Specification

```yaml
# WebSocket API for real-time data streaming
websocket_endpoints:
  - url: wss://api.patriot-trading.com/ws/v1
    description: Main WebSocket endpoint for real-time data
    authentication:
      type: jwt
      location: query_param
      parameter: token
    
  - url: wss://api.patriot-trading.com/ws/v1/private
    description: Private user data streams
    authentication:
      type: jwt
      location: header
      header: Authorization

channels:
  # Public market data channels
  market_data:
    description: Real-time market data (trades, order book, ticker)
    subscription:
      action: subscribe
      channel: market_data
      symbols: ["BTCUSDT", "ETHUSDT"]
      data_types: ["trades", "depth", "ticker"]
    message_format:
      type: object
      properties:
        channel: 
          type: string
          const: market_data
        symbol:
          type: string
        data_type:
          type: string
          enum: [trades, depth, ticker, kline]
        timestamp:
          type: integer
          format: unix_timestamp_ms
        data:
          oneOf:
            - $ref: '#/components/schemas/TradeData'
            - $ref: '#/components/schemas/DepthData'
            - $ref: '#/components/schemas/TickerData'
  
  # Private user channels  
  order_updates:
    description: Real-time order status updates
    subscription:
      action: subscribe
      channel: order_updates
      filters:
        user_id: string (optional, defaults to authenticated user)
        account_ids: array of strings (optional)
        symbols: array of strings (optional)
    message_format:
      type: object
      properties:
        channel:
          type: string
          const: order_updates
        event_type:
          type: string
          enum: [order_created, order_filled, order_cancelled, order_rejected]
        timestamp:
          type: integer
        data:
          $ref: '#/components/schemas/OrderUpdateData'

  portfolio_updates:
    description: Real-time portfolio changes
    subscription:
      action: subscribe
      channel: portfolio_updates
      filters:
        user_id: string
        update_types: ["balance", "position", "pnl"]
    message_format:
      type: object
      properties:
        channel:
          type: string
          const: portfolio_updates
        update_type:
          type: string
          enum: [balance_update, position_update, pnl_update]
        timestamp:
          type: integer
        data:
          oneOf:
            - $ref: '#/components/schemas/BalanceUpdateData'
            - $ref: '#/components/schemas/PositionUpdateData'
            - $ref: '#/components/schemas/PnLUpdateData'

  risk_alerts:
    description: Real-time risk violation alerts
    subscription:
      action: subscribe
      channel: risk_alerts
      filters:
        user_id: string
        severity: ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    message_format:
      type: object
      properties:
        channel:
          type: string
          const: risk_alerts
        alert_type:
          type: string
          enum: [drawdown_limit, position_size, leverage_limit, var_exceeded]
        severity:
          type: string
          enum: [LOW, MEDIUM, HIGH, CRITICAL]
        timestamp:
          type: integer
        data:
          $ref: '#/components/schemas/RiskAlertData'

components:
  schemas:
    TradeData:
      type: object
      properties:
        trade_id:
          type: string
        price:
          type: string
        quantity:
          type: string
        side:
          type: string
          enum: [BUY, SELL]
        timestamp:
          type: integer

    DepthData:
      type: object
      properties:
        bids:
          type: array
          items:
            type: array
            items:
              type: string
            minItems: 2
            maxItems: 2
        asks:
          type: array
          items:
            type: array
            items:
              type: string
            minItems: 2
            maxItems: 2
        last_update_id:
          type: integer

    OrderUpdateData:
      type: object
      properties:
        order_id:
          type: string
          format: uuid
        user_id:
          type: string
          format: uuid
        symbol:
          type: string
        side:
          type: string
        status:
          type: string
        filled_quantity:
          type: string
        remaining_quantity:
          type: string
        avg_fill_price:
          type: string
        commission:
          type: string
```

### WebSocket Client Implementation

```typescript
// Real-time WebSocket client for PATRIOT API
class PatriotWebSocketClient {
    private ws: WebSocket | null = null;
    private url: string;
    private token: string;
    private subscriptions: Map<string, any> = new Map();
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 1000;
    private heartbeatInterval: NodeJS.Timeout | null = null;
    private callbacks: Map<string, Function[]> = new Map();

    constructor(url: string, token: string) {
        this.url = url;
        this.token = token;
    }

    async connect(): Promise<void> {
        return new Promise((resolve, reject) => {
            try {
                const wsUrl = `${this.url}?token=${this.token}`;
                this.ws = new WebSocket(wsUrl);

                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.reconnectAttempts = 0;
                    this.startHeartbeat();
                    this.resubscribeAll();
                    resolve();
                };

                this.ws.onmessage = (event) => {
                    this.handleMessage(JSON.parse(event.data));
                };

                this.ws.onclose = (event) => {
                    console.log('WebSocket closed:', event.code, event.reason);
                    this.stopHeartbeat();
                    
                    if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
                        this.scheduleReconnect();
                    }
                };

                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    reject(error);
                };

            } catch (error) {
                reject(error);
            }
        });
    }

    // Subscribe to market data
    subscribeMarketData(symbols: string[], dataTypes: string[] = ['trades', 'depth', 'ticker']): void {
        const subscription = {
            action: 'subscribe',
            channel: 'market_data',
            symbols: symbols,
            data_types: dataTypes
        };

        this.send(subscription);
        this.subscriptions.set('market_data', subscription);
    }

    // Subscribe to order updates
    subscribeOrderUpdates(filters: {
        user_id?: string;
        account_ids?: string[];
        symbols?: string[];
    } = {}): void {
        const subscription = {
            action: 'subscribe',
            channel: 'order_updates',
            filters: filters
        };

        this.send(subscription);
        this.subscriptions.set('order_updates', subscription);
    }

    // Subscribe to portfolio updates
    subscribePortfolioUpdates(userId: string, updateTypes: string[] = ['balance', 'position', 'pnl']): void {
        const subscription = {
            action: 'subscribe',
            channel: 'portfolio_updates',
            filters: {
                user_id: userId,
                update_types: updateTypes
            }
        };

        this.send(subscription);
        this.subscriptions.set('portfolio_updates', subscription);
    }

    // Subscribe to risk alerts
    subscribeRiskAlerts(userId: string, severity: string[] = ['MEDIUM', 'HIGH', 'CRITICAL']): void {
        const subscription = {
            action: 'subscribe',
            channel: 'risk_alerts',
            filters: {
                user_id: userId,
                severity: severity
            }
        };

        this.send(subscription);
        this.subscriptions.set('risk_alerts', subscription);
    }

    // Event listeners
    onMarketData(callback: (data: any) => void): void {
        this.addEventListener('market_data', callback);
    }

    onOrderUpdate(callback: (data: any) => void): void {
        this.addEventListener('order_updates', callback);
    }

    onPortfolioUpdate(callback: (data: any) => void): void {
        this.addEventListener('portfolio_updates', callback);
    }

    onRiskAlert(callback: (data: any) => void): void {
        this.addEventListener('risk_alerts', callback);
    }

    private addEventListener(channel: string, callback: Function): void {
        if (!this.callbacks.has(channel)) {
            this.callbacks.set(channel, []);
        }
        this.callbacks.get(channel)!.push(callback);
    }

    private handleMessage(message: any): void {
        const { channel, data } = message;

        // Handle different message types
        switch (message.type) {
            case 'pong':
                // Heartbeat response
                break;
            
            case 'subscription_confirmed':
                console.log(`Subscription confirmed for channel: ${channel}`);
                break;
            
            case 'error':
                console.error(`WebSocket error:`, message);
                break;
            
            default:
                // Data message
                if (channel && this.callbacks.has(channel)) {
                    const callbacks = this.callbacks.get(channel)!;
                    callbacks.forEach(callback => {
                        try {
                            callback(message);
                        } catch (error) {
                            console.error(`Error in callback for channel ${channel}:`, error);
                        }
                    });
                }
        }
    }

    private send(data: any): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        } else {
            console.warn('WebSocket not connected, message queued:', data);
        }
    }

    private startHeartbeat(): void {
        this.heartbeatInterval = setInterval(() => {
            this.send({ type: 'ping', timestamp: Date.now() });
        }, 30000); // 30 seconds
    }

    private stopHeartbeat(): void {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    private scheduleReconnect(): void {
        setTimeout(() => {
            this.reconnectAttempts++;
            console.log(`Reconnecting... Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
            this.connect().catch(error => {
                console.error('Reconnect failed:', error);
            });
        }, this.reconnectDelay * Math.pow(2, this.reconnectAttempts)); // Exponential backoff
    }

    private resubscribeAll(): void {
        this.subscriptions.forEach((subscription) => {
            this.send(subscription);
        });
    }

    disconnect(): void {
        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
            this.ws = null;
        }
        this.stopHeartbeat();
    }
}

// Advanced trading dashboard using WebSocket
class TradingDashboard {
    private wsClient: PatriotWebSocketClient;
    private orderBook: Map<string, any> = new Map();
    private positions: Map<string, any> = new Map();
    private orders: Map<string, any> = new Map();
    private portfolioValue = 0;

    constructor(wsUrl: string, token: string) {
        this.wsClient = new PatriotWebSocketClient(wsUrl, token);
        this.setupEventHandlers();
    }

    async initialize(userId: string): Promise<void> {
        await this.wsClient.connect();
        
        // Subscribe to all relevant channels
        this.wsClient.subscribeMarketData(['BTCUSDT', 'ETHUSDT', 'ADAUSDT']);
        this.wsClient.subscribeOrderUpdates({ user_id: userId });
        this.wsClient.subscribePortfolioUpdates(userId);
        this.wsClient.subscribeRiskAlerts(userId);
    }

    private setupEventHandlers(): void {
        // Market data handler
        this.wsClient.onMarketData((message: any) => {
            const { symbol, data_type, data } = message;
            
            switch (data_type) {
                case 'depth':
                    this.updateOrderBook(symbol, data);
                    break;
                case 'trades':
                    this.updateLastTrade(symbol, data);
                    break;
                case 'ticker':
                    this.updateTicker(symbol, data);
                    break;
            }
        });

        // Order updates handler
        this.wsClient.onOrderUpdate((message: any) => {
            const { event_type, data } = message;
            
            switch (event_type) {
                case 'order_created':
                    this.orders.set(data.order_id, { ...data, status: 'NEW' });
                    this.notifyOrderCreated(data);
                    break;
                case 'order_filled':
                    if (this.orders.has(data.order_id)) {
                        const order = this.orders.get(data.order_id);
                        order.status = data.filled_quantity === data.quantity ? 'FILLED' : 'PARTIALLY_FILLED';
                        order.filled_quantity = data.filled_quantity;
                        order.avg_fill_price = data.avg_fill_price;
                        this.notifyOrderFilled(order);
                    }
                    break;
                case 'order_cancelled':
                    if (this.orders.has(data.order_id)) {
                        this.orders.get(data.order_id).status = 'CANCELLED';
                        this.notifyOrderCancelled(data);
                    }
                    break;
            }
        });

        // Portfolio updates handler
        this.wsClient.onPortfolioUpdate((message: any) => {
            const { update_type, data } = message;
            
            switch (update_type) {
                case 'balance_update':
                    this.portfolioValue = data.total_balance_usd;
                    this.notifyBalanceUpdate(data);
                    break;
                case 'position_update':
                    this.positions.set(data.symbol, data);
                    this.notifyPositionUpdate(data);
                    break;
                case 'pnl_update':
                    this.notifyPnLUpdate(data);
                    break;
            }
        });

        // Risk alerts handler
        this.wsClient.onRiskAlert((message: any) => {
            const { alert_type, severity, data } = message;
            this.handleRiskAlert(alert_type, severity, data);
        });
    }

    // UI update methods (would integrate with your frontend framework)
    private updateOrderBook(symbol: string, depth: any): void {
        this.orderBook.set(symbol, depth);
        // Update UI order book display
        this.notifyUI('orderbook_update', { symbol, depth });
    }

    private updateLastTrade(symbol: string, trade: any): void {
        // Update UI with last trade info
        this.notifyUI('trade_update', { symbol, trade });
    }

    private updateTicker(symbol: string, ticker: any): void {
        // Update UI ticker display
        this.notifyUI('ticker_update', { symbol, ticker });
    }

    private notifyOrderCreated(order: any): void {
        this.notifyUI('order_created', order);
        // Could also play sound notification
    }

    private notifyOrderFilled(order: any): void {
        this.notifyUI('order_filled', order);
        // Success notification
        this.showNotification(`Order filled: ${order.symbol} ${order.side} ${order.filled_quantity}`, 'success');
    }

    private notifyOrderCancelled(order: any): void {
        this.notifyUI('order_cancelled', order);
        this.showNotification(`Order cancelled: ${order.symbol}`, 'info');
    }

    private notifyBalanceUpdate(data: any): void {
        this.notifyUI('balance_update', data);
    }

    private notifyPositionUpdate(position: any): void {
        this.notifyUI('position_update', position);
    }

    private notifyPnLUpdate(pnl: any): void {
        this.notifyUI('pnl_update', pnl);
    }

    private handleRiskAlert(alertType: string, severity: string, data: any): void {
        const message = this.formatRiskAlertMessage(alertType, data);
        
        // Show urgent notification for high/critical alerts
        if (['HIGH', 'CRITICAL'].includes(severity)) {
            this.showNotification(message, 'error', true); // persistent notification
        } else {
            this.showNotification(message, 'warning');
        }
        
        // Log the risk alert
        console.warn(`[RISK ALERT - ${severity}] ${alertType}:`, data);
        
        // Update UI risk dashboard
        this.notifyUI('risk_alert', { alertType, severity, data, message });
    }

    private formatRiskAlertMessage(alertType: string, data: any): string {
        switch (alertType) {
            case 'drawdown_limit':
                return `Drawdown limit exceeded: ${data.current_drawdown_percentage}%`;
            case 'position_size':
                return `Position size limit exceeded for ${data.symbol}: $${data.position_value}`;
            case 'leverage_limit':
                return `Leverage limit exceeded: ${data.current_leverage}x`;
            case 'var_exceeded':
                return `Value at Risk exceeded: $${data.current_var}`;
            default:
                return `Risk alert: ${alertType}`;
        }
    }

    private notifyUI(event: string, data: any): void {
        // This would integrate with your UI framework (React, Vue, etc.)
        // Example: emit event to component or update state store
        window.dispatchEvent(new CustomEvent(`patriot:${event}`, { detail: data }));
    }

    private showNotification(message: string, type: 'info' | 'success' | 'warning' | 'error', persistent = false): void {
        // Integrate with your notification system
        console.log(`[${type.toUpperCase()}] ${message}`);
        // Example: toast notification, browser notification, etc.
    }

    // Public API methods
    getCurrentOrderBook(symbol: string): any {
        return this.orderBook.get(symbol);
    }

    getCurrentPositions(): Map<string, any> {
        return this.positions;
    }

    getCurrentOrders(): Map<string, any> {
        return this.orders;
    }

    getPortfolioValue(): number {
        return this.portfolioValue;
    }

    disconnect(): void {
        this.wsClient.disconnect();
    }
}

// Usage example
async function initializeTradingDashboard() {
    const token = 'your_jwt_token_here';
    const userId = 'your_user_id_here';
    const wsUrl = 'wss://api.patriot-trading.com/ws/v1';
    
    const dashboard = new TradingDashboard(wsUrl, token);
    
    try {
        await dashboard.initialize(userId);
        console.log('Trading dashboard initialized successfully');
        
        // Set up UI event listeners
        window.addEventListener('patriot:order_filled', (event: any) => {
            const order = event.detail;
            console.log(`Order filled notification: ${order.symbol} ${order.side}`);
            // Update UI components
        });
        
        window.addEventListener('patriot:risk_alert', (event: any) => {
            const { alertType, severity, message } = event.detail;
            console.log(`Risk alert: [${severity}] ${message}`);
            // Update risk dashboard UI
        });
        
    } catch (error) {
        console.error('Failed to initialize trading dashboard:', error);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initializeTradingDashboard);
```

---

## 🔒 Security and Rate Limiting

### API Security Headers

```typescript
// Security middleware configuration
const securityHeaders = {
    // CORS configuration
    'Access-Control-Allow-Origin': 'https://admin.patriot-trading.com',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Authorization, Content-Type, X-API-Key, X-API-Secret, X-API-Timestamp, X-API-Signature',
    'Access-Control-Max-Age': '3600',
    
    // Security headers
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self' wss://api.patriot-trading.com",
    
    // API-specific headers
    'X-RateLimit-Limit': '1000',
    'X-RateLimit-Remaining': '999',
    'X-RateLimit-Reset': '1695587400',
    'X-API-Version': '2.0',
    'X-Request-ID': 'req_1695587400_abc123'
};
```

### Rate Limiting Specification

```yaml
rate_limits:
  # User-based limits
  authenticated_user:
    requests_per_minute: 1000
    requests_per_hour: 10000
    requests_per_day: 100000
    burst_allowance: 100
    
  # API key-based limits  
  api_key_basic:
    requests_per_minute: 100
    requests_per_hour: 1000
    requests_per_day: 10000
    
  api_key_premium:
    requests_per_minute: 500
    requests_per_hour: 5000
    requests_per_day: 50000
    
  # Endpoint-specific limits
  order_creation:
    requests_per_minute: 100
    requests_per_hour: 1000
    cooldown_ms: 100  # Minimum time between requests
    
  market_data:
    requests_per_minute: 2000
    requests_per_hour: 20000
    
  portfolio_queries:
    requests_per_minute: 300
    requests_per_hour: 3000
    
  # IP-based limits (DDoS protection)
  per_ip:
    requests_per_minute: 1000
    requests_per_hour: 5000
    ban_threshold: 10000  # Auto-ban threshold
    ban_duration_minutes: 60

# Rate limit headers returned in responses
rate_limit_headers:
  - X-RateLimit-Limit
  - X-RateLimit-Remaining  
  - X-RateLimit-Reset
  - X-RateLimit-Type
  - Retry-After (when limit exceeded)
```

### Error Response Standards

```yaml
# Standardized error responses
error_responses:
  400_bad_request:
    error:
      code: "VALIDATION_ERROR"
      type: "ValidationError"
      details:
        field_errors:
          - field: "quantity"
            message: "Quantity must be greater than 0"
            invalid_value: "-0.001"
            constraint: "gt=0"
    message: "Request validation failed"
    request_id: "req_1695587400_abc123"
    timestamp: "2025-09-24T20:50:00Z"
    documentation_url: "https://docs.patriot-trading.com/errors#validation-error"
    
  401_unauthorized:
    error:
      code: "AUTHENTICATION_FAILED"
      type: "AuthenticationError"
      details:
        reason: "Invalid or expired JWT token"
        token_expired_at: "2025-09-24T19:50:00Z"
    message: "Authentication required"
    request_id: "req_1695587400_def456"
    timestamp: "2025-09-24T20:50:00Z"
    
  403_forbidden:
    error:
      code: "INSUFFICIENT_PERMISSIONS"
      type: "AuthorizationError"
      details:
        required_permission: "trade"
        user_permissions: ["view_portfolio", "view_orders"]
    message: "Insufficient permissions for this operation"
    request_id: "req_1695587400_ghi789"
    timestamp: "2025-09-24T20:50:00Z"
    
  429_rate_limited:
    error:
      code: "RATE_LIMIT_EXCEEDED"
      type: "RateLimitError"
      details:
        limit_type: "requests_per_minute"
        current_usage: 1001
        limit: 1000
        reset_at: "2025-09-24T20:51:00Z"
    message: "Rate limit exceeded"
    request_id: "req_1695587400_jkl012"
    timestamp: "2025-09-24T20:50:00Z"
    retry_after: 60
    
  500_internal_error:
    error:
      code: "INTERNAL_SERVER_ERROR"
      type: "SystemError"
      details:
        incident_id: "inc_1695587400_mno345"
        service: "order-command-service"
    message: "Internal server error occurred"
    request_id: "req_1695587400_pqr678"
    timestamp: "2025-09-24T20:50:00Z"
    support_url: "https://support.patriot-trading.com"
```

---

## 📖 SDK and Integration Examples

### Official Python SDK

```python
# PATRIOT Trading System Python SDK
# pip install patriot-trading-sdk

import asyncio
from patriot_trading import PatriotClient, OrderSide, OrderType

class PatriotTradingBot:
    def __init__(self, api_key: str, api_secret: str, base_url: str = None):
        self.client = PatriotClient(
            api_key=api_key,
            api_secret=api_secret,
            base_url=base_url or 'https://api.patriot-trading.com/api/v1'
        )
        
    async def initialize(self):
        """Initialize the trading bot"""
        await self.client.authenticate()
        
        # Get user profile
        self.user = await self.client.users.get_profile()
        print(f"Initialized bot for user: {self.user['username']}")
        
        # Get accounts
        self.accounts = await self.client.users.list_accounts()
        print(f"Found {len(self.accounts)} trading accounts")
        
    async def run_scalping_strategy(self, symbol: str = 'BTCUSDT'):
        """Simple scalping strategy example"""
        account = self.accounts[0]  # Use first account
        
        # Subscribe to real-time market data
        async with self.client.stream() as stream:
            await stream.subscribe_market_data([symbol], ['trades', 'depth'])
            
            # Simple strategy state
            last_trade_price = None
            position_size = 0
            target_profit = 0.001  # 0.1%
            
            async for message in stream:
                if message['channel'] == 'market_data' and message['data_type'] == 'trades':
                    trade = message['data']
                    current_price = float(trade['price'])
                    
                    if last_trade_price is None:
                        last_trade_price = current_price
                        continue
                    
                    # Simple mean reversion logic
                    price_change = (current_price - last_trade_price) / last_trade_price
                    
                    if position_size == 0:  # No position
                        if abs(price_change) > 0.002:  # 0.2% price move
                            # Enter position opposite to price move
                            side = OrderSide.BUY if price_change < 0 else OrderSide.SELL
                            quantity = self.calculate_position_size(account, current_price)
                            
                            order = await self.client.orders.create_market_order(
                                account_id=account['account_id'],
                                symbol=symbol,
                                side=side,
                                quantity=str(quantity)
                            )
                            
                            if order['status'] in ['NEW', 'FILLED']:
                                position_size = quantity if side == OrderSide.BUY else -quantity
                                print(f"Entered {side} position: {quantity} @ {current_price}")
                    
                    elif position_size > 0:  # Long position
                        if current_price >= last_trade_price * (1 + target_profit):
                            # Take profit
                            await self.close_position(account, symbol, position_size, 'PROFIT')
                            position_size = 0
                    
                    elif position_size < 0:  # Short position
                        if current_price <= last_trade_price * (1 - target_profit):
                            # Take profit
                            await self.close_position(account, symbol, abs(position_size), 'PROFIT')
                            position_size = 0
                    
                    last_trade_price = current_price
    
    def calculate_position_size(self, account, price):
        """Calculate position size based on account balance and risk management"""
        balance = float(account['balance_usd'])
        max_risk_per_trade = 0.01  # 1% of account        
        position_value = balance * max_risk_per_trade
        quantity = position_value / price
        return round(quantity, 6)
    
    async def close_position(self, account, symbol, quantity, reason):
        """Close position with market order"""
        side = OrderSide.SELL  # Assuming we're closing long position
        
        order = await self.client.orders.create_market_order(
            account_id=account['account_id'],
            symbol=symbol,
            side=side,
            quantity=str(quantity)
        )
        
        print(f"Closed position: {reason} - {quantity} @ market price")
        return order

# Usage
async def main():
    bot = PatriotTradingBot(
        api_key='your_api_key',
        api_secret='your_api_secret'
    )
    
    await bot.initialize()
    await bot.run_scalping_strategy('BTCUSDT')

if __name__ == "__main__":
    asyncio.run(main())
```

### JavaScript/Node.js SDK

```javascript
// PATRIOT Trading System JavaScript SDK
// npm install patriot-trading-js

const { PatriotClient, OrderSide, OrderType } = require('patriot-trading-js');

class PatriotPortfolioManager {
    constructor(apiKey, apiSecret, options = {}) {
        this.client = new PatriotClient({
            apiKey,
            apiSecret,
            baseURL: options.baseURL || 'https://api.patriot-trading.com/api/v1',
            sandbox: options.sandbox || false
        });
        
        this.portfolioState = {
            positions: new Map(),
            orders: new Map(),
            balance: 0,
            unrealizedPnL: 0
        };
        
        this.riskLimits = {
            maxPositionSize: 10000, // $10k max position
            maxDailyLoss: 1000,     // $1k max daily loss
            maxDrawdown: 0.05       // 5% max drawdown
        };
    }
    
    async initialize() {
        await this.client.authenticate();
        
        // Load initial portfolio state
        const summary = await this.client.portfolio.getSummary();
        this.portfolioState.balance = summary.total_balance_usd;
        this.portfolioState.unrealizedPnL = summary.unrealized_pnl_usd;
        
        // Load current positions
        const positions = await this.client.portfolio.getPositions();
        positions.forEach(position => {
            this.portfolioState.positions.set(position.symbol, position);
        });
        
        // Set up real-time updates
        await this.setupRealTimeUpdates();
        
        console.log('Portfolio manager initialized');
        console.log(`Balance: $${this.portfolioState.balance.toFixed(2)}`);
        console.log(`Positions: ${this.portfolioState.positions.size}`);
    }
    
    async setupRealTimeUpdates() {
        const stream = await this.client.createStream();
        
        // Subscribe to portfolio updates
        await stream.subscribePortfolioUpdates();
        await stream.subscribeOrderUpdates();
        await stream.subscribeRiskAlerts();
        
        stream.on('portfolio_update', (update) => {
            this.handlePortfolioUpdate(update);
        });
        
        stream.on('order_update', (update) => {
            this.handleOrderUpdate(update);
        });
        
        stream.on('risk_alert', (alert) => {
            this.handleRiskAlert(alert);
        });
    }
    
    // Advanced order management
    async placeBracketOrder(symbol, side, quantity, entryPrice, stopLoss, takeProfit) {
        const accountId = await this.getOptimalAccount(symbol);
        
        try {
            // Place parent order
            const parentOrder = await this.client.orders.create({
                account_id: accountId,
                symbol: symbol,
                side: side,
                type: OrderType.LIMIT,
                quantity: quantity,
                price: entryPrice,
                time_in_force: 'GTC'
            });
            
            console.log(`Bracket order parent placed: ${parentOrder.order_id}`);
            
            // Place stop loss order (opposite side)
            const stopSide = side === OrderSide.BUY ? OrderSide.SELL : OrderSide.BUY;
            const stopOrder = await this.client.orders.create({
                account_id: accountId,
                symbol: symbol,
                side: stopSide,
                type: OrderType.STOP_MARKET,
                quantity: quantity,
                stop_price: stopLoss,
                reduce_only: true
            });
            
            // Place take profit order
            const takeProfitOrder = await this.client.orders.create({
                account_id: accountId,
                symbol: symbol,
                side: stopSide,
                type: OrderType.TAKE_PROFIT,
                quantity: quantity,
                stop_price: takeProfit,
                reduce_only: true
            });
            
            const bracketGroup = {
                parent: parentOrder,
                stopLoss: stopOrder,
                takeProfit: takeProfitOrder,
                symbol: symbol,
                createdAt: new Date()
            };
            
            this.portfolioState.orders.set(parentOrder.order_id, bracketGroup);
            
            return bracketGroup;
            
        } catch (error) {
            console.error('Failed to place bracket order:', error);
            throw error;
        }
    }
    
    // Risk management
    async checkRiskLimits(symbol, side, quantity, price) {
        const positionValue = quantity * price;
        
        // Check position size limit
        if (positionValue > this.riskLimits.maxPositionSize) {
            throw new Error(`Position size ${positionValue} exceeds limit ${this.riskLimits.maxPositionSize}`);
        }
        
        // Check daily loss limit
        const dayStartBalance = await this.getDayStartBalance();
        const currentLoss = dayStartBalance - this.portfolioState.balance;
        
        if (currentLoss > this.riskLimits.maxDailyLoss) {
            throw new Error(`Daily loss limit exceeded: $${currentLoss.toFixed(2)}`);
        }
        
        // Check drawdown limit
        const peakBalance = await this.getPeakBalance();
        const currentDrawdown = (peakBalance - this.portfolioState.balance) / peakBalance;
        
        if (currentDrawdown > this.riskLimits.maxDrawdown) {
            throw new Error(`Drawdown limit exceeded: ${(currentDrawdown * 100).toFixed(2)}%`);
        }
        
        return true;
    }
    
    // Portfolio rebalancing
    async rebalancePortfolio(targetAllocations) {
        const currentPositions = Array.from(this.portfolioState.positions.values());
        const totalValue = this.portfolioState.balance + this.portfolioState.unrealizedPnL;
        
        const rebalanceOrders = [];
        
        for (const [symbol, targetPercent] of Object.entries(targetAllocations)) {
            const targetValue = totalValue * targetPercent;
            const currentPosition = currentPositions.find(p => p.symbol === symbol);
            const currentValue = currentPosition ? 
                parseFloat(currentPosition.size) * parseFloat(currentPosition.mark_price) : 0;
            
            const difference = targetValue - currentValue;
            const threshold = totalValue * 0.01; // 1% threshold
            
            if (Math.abs(difference) > threshold) {
                const side = difference > 0 ? OrderSide.BUY : OrderSide.SELL;
                const quantity = Math.abs(difference) / parseFloat(await this.getMarketPrice(symbol));
                
                const order = await this.client.orders.create({
                    account_id: await this.getOptimalAccount(symbol),
                    symbol: symbol,
                    side: side,
                    type: OrderType.MARKET,
                    quantity: quantity.toFixed(6)
                });
                
                rebalanceOrders.push(order);
                console.log(`Rebalance order: ${side} ${quantity.toFixed(6)} ${symbol}`);
            }
        }
        
        return rebalanceOrders;
    }
    
    // Performance tracking
    async generatePerformanceReport(period = '30D') {
        const performance = await this.client.portfolio.getPerformance({
            period: period,
            benchmark: 'BTC'
        });
        
        const report = {
            period: period,
            generated_at: new Date().toISOString(),
            summary: {
                total_return: performance.total_return,
                sharpe_ratio: performance.metrics.sharpe_ratio,
                max_drawdown: performance.metrics.max_drawdown,
                win_rate: performance.metrics.win_rate,
                profit_factor: performance.metrics.profit_factor
            },
            top_performers: this.getTopPerformingPositions(),
            worst_performers: this.getWorstPerformingPositions(),
            risk_metrics: await this.calculateRiskMetrics(),
            recommendations: await this.generateRecommendations()
        };
        
        return report;
    }
    
    // Event handlers
    handlePortfolioUpdate(update) {
        switch (update.update_type) {
            case 'balance_update':
                this.portfolioState.balance = update.data.total_balance_usd;
                this.portfolioState.unrealizedPnL = update.data.unrealized_pnl_usd;
                break;
                
            case 'position_update':
                this.portfolioState.positions.set(update.data.symbol, update.data);
                break;
                
            case 'pnl_update':
                console.log(`P&L Update: ${update.data.realized_pnl_usd >= 0 ? '+' : ''}$${update.data.realized_pnl_usd.toFixed(2)}`);
                break;
        }
        
        this.emitPortfolioEvent('updated', this.portfolioState);
    }
    
    handleOrderUpdate(update) {
        const { event_type, data } = update;
        
        switch (event_type) {
            case 'order_filled':
                console.log(`Order filled: ${data.symbol} ${data.side} ${data.filled_quantity} @ ${data.avg_fill_price}`);
                this.emitPortfolioEvent('order_filled', data);
                break;
                
            case 'order_cancelled':
                console.log(`Order cancelled: ${data.order_id}`);
                this.portfolioState.orders.delete(data.order_id);
                break;
        }
    }
    
    handleRiskAlert(alert) {
        const { alert_type, severity, data } = alert;
        
        console.warn(`[${severity}] Risk Alert: ${alert_type}`);
        
        if (severity === 'CRITICAL') {
            // Auto-close positions if critical risk
            this.emergencyCloseAllPositions(alert_type);
        }
        
        this.emitPortfolioEvent('risk_alert', alert);
    }
    
    async emergencyCloseAllPositions(reason) {
        console.log(`EMERGENCY: Closing all positions due to ${reason}`);
        
        const positions = Array.from(this.portfolioState.positions.values());
        const closeOrders = [];
        
        for (const position of positions) {
            if (parseFloat(position.size) !== 0) {
                const side = parseFloat(position.size) > 0 ? OrderSide.SELL : OrderSide.BUY;
                
                try {
                    const order = await this.client.orders.create({
                        account_id: position.account_id,
                        symbol: position.symbol,
                        side: side,
                        type: OrderType.MARKET,
                        quantity: Math.abs(parseFloat(position.size)).toString(),
                        reduce_only: true
                    });
                    
                    closeOrders.push(order);
                    console.log(`Emergency close: ${position.symbol} ${side} ${position.size}`);
                    
                } catch (error) {
                    console.error(`Failed to emergency close ${position.symbol}:`, error);
                }
            }
        }
        
        return closeOrders;
    }
    
    // Utility methods
    async getOptimalAccount(symbol) {
        const accounts = await this.client.users.listAccounts({ is_active: true });
        // Simple logic: return first account that supports the symbol
        return accounts.find(account => account.is_active)?.account_id;
    }
    
    async getMarketPrice(symbol) {
        const ticker = await this.client.market.getTicker(symbol);
        return ticker.last_price;
    }
    
    emitPortfolioEvent(eventType, data) {
        // Emit events for external listeners
        if (this.eventEmitter) {
            this.eventEmitter.emit(eventType, data);
        }
    }
    
    // Public API
    on(eventType, callback) {
        if (!this.eventEmitter) {
            const EventEmitter = require('events');
            this.eventEmitter = new EventEmitter();
        }
        this.eventEmitter.on(eventType, callback);
    }
    
    getPortfolioState() {
        return { ...this.portfolioState };
    }
    
    async disconnect() {
        await this.client.disconnect();
    }
}

// Usage example
async function runPortfolioManager() {
    const manager = new PatriotPortfolioManager(
        'your_api_key',
        'your_api_secret',
        { sandbox: true }
    );
    
    // Set up event listeners
    manager.on('updated', (state) => {
        console.log(`Portfolio value: $${state.balance.toFixed(2)}`);
    });
    
    manager.on('order_filled', (order) => {
        console.log(`✅ Order filled: ${order.symbol} ${order.side}`);
    });
    
    manager.on('risk_alert', (alert) => {
        console.log(`⚠️ Risk alert: ${alert.alert_type} [${alert.severity}]`);
    });
    
    try {
        await manager.initialize();
        
        // Example: Place bracket order
        await manager.placeBracketOrder(
            'BTCUSDT',      // symbol
            OrderSide.BUY,  // side
            '0.001',        // quantity
            '65000',        // entry price
            '63000',        // stop loss
            '68000'         // take profit
        );
        
        // Example: Rebalance portfolio
        await manager.rebalancePortfolio({
            'BTCUSDT': 0.60,   // 60% BTC
            'ETHUSDT': 0.30,   // 30% ETH
            'ADAUSDT': 0.10    // 10% ADA
        });
        
        // Generate performance report
        const report = await manager.generatePerformanceReport('7D');
        console.log('Performance Report:', JSON.stringify(report, null, 2));
        
    } catch (error) {
        console.error('Portfolio manager error:', error);
    }
}

module.exports = { PatriotPortfolioManager };
```

---

## 📝 API Testing Examples

### Postman Collection

```json
{
    "info": {
        "name": "PATRIOT Trading API",
        "description": "Complete API collection for PATRIOT trading system",
        "version": "2.0.0"
    },
    "auth": {
        "type": "bearer",
        "bearer": [
            {
                "key": "token",
                "value": "{{access_token}}",
                "type": "string"
            }
        ]
    },
    "variable": [
        {
            "key": "base_url",
            "value": "https://api.patriot-trading.com/api/v1"
        },
        {
            "key": "user_id",
            "value": "550e8400-e29b-41d4-a716-446655440000"
        },
        {
            "key": "account_id",
            "value": "550e8400-e29b-41d4-a716-446655440001"
        }
    ],
    "item": [
        {
            "name": "Authentication",
            "item": [
                {
                    "name": "Login",
                    "request": {
                        "method": "POST",
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": "{\n  \"telegram_id\": 123456789,\n  \"username\": \"test_trader\",\n  \"signature\": \"telegram_auth_signature\"\n}"
                        },
                        "url": "{{base_url}}/auth/login"
                    },
                    "event": [
                        {
                            "listen": "test",
                            "script": {
                                "exec": [
                                    "if (pm.response.code === 200) {",
                                    "    const response = pm.response.json();",
                                    "    pm.collectionVariables.set('access_token', response.access_token);",
                                    "    pm.collectionVariables.set('user_id', response.user.user_id);",
                                    "    console.log('Authentication successful');",
                                    "} else {",
                                    "    console.log('Authentication failed');",
                                    "}"
                                ]
                            }
                        }
                    ]
                },
                {
                    "name": "Create API Key",
                    "request": {
                        "method": "POST",
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": "{\n  \"name\": \"Test API Key\",\n  \"permissions\": [\"trade\", \"view_portfolio\"],\n  \"rate_limit\": {\n    \"requests_per_minute\": 100\n  }\n}"
                        },
                        "url": "{{base_url}}/auth/api-keys"
                    }
                }
            ]
        },
        {
            "name": "User Management",
            "item": [
                {
                    "name": "Register User",
                    "request": {
                        "method": "POST",
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": "{\n  \"telegram_id\": 987654321,\n  \"username\": \"new_trader\",\n  \"email\": \"trader@example.com\",\n  \"risk_profile\": \"MEDIUM\"\n}"
                        },
                        "url": "{{base_url}}/users",
                        "auth": {
                            "type": "noauth"
                        }
                    }
                },
                {
                    "name": "Get User Profile",
                    "request": {
                        "method": "GET",
                        "url": "{{base_url}}/users/{{user_id}}"
                    }
                },
                {
                    "name": "Add Exchange Account",
                    "request": {
                        "method": "POST",
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": "{\n  \"exchange\": \"BINANCE\",\n  \"account_name\": \"Main Trading Account\",\n  \"api_key\": \"test_api_key\",\n  \"api_secret\": \"test_api_secret\",\n  \"is_testnet\": true\n}"
                        },
                        "url": "{{base_url}}/users/{{user_id}}/accounts"
                    },
                    "event": [
                        {
                            "listen": "test",
                            "script": {
                                "exec": [
                                    "if (pm.response.code === 201) {",
                                    "    const response = pm.response.json();",
                                    "    pm.collectionVariables.set('account_id', response.account_id);",
                                    "}"
                                ]
                            }
                        }
                    ]
                }
            ]
        },
        {
            "name": "Order Management",
            "item": [
                {
                    "name": "Create Market Order",
                    "request": {
                        "method": "POST",
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": "{\n  \"account_id\": \"{{account_id}}\",\n  \"symbol\": \"BTCUSDT\",\n  \"side\": \"BUY\",\n  \"type\": \"MARKET\",\n  \"quantity\": \"0.001\"\n}"
                        },
                        "url": "{{base_url}}/orders"
                    },
                    "event": [
                        {
                            "listen": "test",
                            "script": {
                                "exec": [
                                    "pm.test('Order created successfully', function () {",
                                    "    pm.response.to.have.status(201);",
                                    "});",
                                    "",
                                    "pm.test('Response contains order_id', function () {",
                                    "    const response = pm.response.json();",
                                    "    pm.expect(response).to.have.property('order_id');",
                                    "    pm.collectionVariables.set('order_id', response.order_id);",
                                    "});"
                                ]
                            }
                        }
                    ]
                },
                {
                    "name": "Create Limit Order",
                    "request": {
                        "method": "POST",
                        "header": [
                            {
                                "key": "Content-Type",
                                "value": "application/json"
                            }
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": "{\n  \"account_id\": \"{{account_id}}\",\n  \"symbol\": \"ETHUSDT\",\n  \"side\": \"BUY\",\n  \"type\": \"LIMIT\",\n  \"quantity\": \"0.01\",\n  \"price\": \"2400.00\",\n  \"time_in_force\": \"GTC\"\n}"
                        },
                        "url": "{{base_url}}/orders"
                    }
                },
                {
                    "name": "Get Order Details",
                    "request": {
                        "method": "GET",
                        "url": "{{base_url}}/orders/{{order_id}}"
                    }
                },
                {
                    "name": "List Orders",
                    "request": {
                        "method": "GET",
                        "url": "{{base_url}}/orders?account_id={{account_id}}&status=NEW&page=1&page_size=50"
                    }
                },
                {
                    "name": "Cancel Order",
                    "request": {
                        "method": "DELETE",
                        "url": "{{base_url}}/orders/{{order_id}}"
                    }
                }
            ]
        },
        {
            "name": "Portfolio Management",
            "item": [
                {
                    "name": "Get Portfolio Summary",
                    "request": {
                        "method": "GET",
                        "url": "{{base_url}}/portfolio/summary?user_id={{user_id}}"
                    }
                },
                {
                    "name": "Get Current Positions",
                    "request": {
                        "method": "GET",
                        "url": "{{base_url}}/portfolio/positions?account_id={{account_id}}"
                    }
                },
                {
                    "name": "Get Performance Metrics",
                    "request": {
                        "method": "GET",
                        "url": "{{base_url}}/portfolio/performance?user_id={{user_id}}&period=30D&benchmark=BTC"
                    }
                },
                {
                    "name": "Get Risk Analytics",
                    "request": {
                        "method": "GET",
                        "url": "{{base_url}}/portfolio/analytics/risk?user_id={{user_id}}&confidence_level=0.95"
                    }
                }
            ]
        }
    ],
    "event": [
        {
            "listen": "prerequest",
            "script": {
                "type": "text/javascript",
                "exec": [
                    "// Add request timestamp for API key authentication",
                    "if (pm.request.headers.get('X-API-Key')) {",
                    "    pm.request.headers.add({",
                    "        key: 'X-API-Timestamp',",
                    "        value: Date.now().toString()",
                    "    });",
                    "}"
                ]
            }
        }
    ]
}
```

### Automated Test Suite

```python
# Comprehensive API test suite using pytest
import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
import aiohttp

class TestPatriotAPI:
    """Comprehensive test suite for PATRIOT Trading API"""
    
    @pytest.fixture(scope="class")
    async def api_client(self):
        """Set up API client for testing"""
        client = PatriotTestClient(
            base_url='https://staging-api.patriot-trading.com/api/v1',
            api_key='test_api_key',
            api_secret='test_api_secret'
        )
        await client.authenticate()
        yield client
        await client.cleanup()
    
    @pytest.fixture
    async def test_user(self, api_client):
        """Create test user for testing"""
        user_data = {
            'telegram_id': int(datetime.now().timestamp()),
            'username': f'test_user_{uuid.uuid4().hex[:8]}',
            'email': 'test@example.com',
            'risk_profile': 'MEDIUM'
        }
        
        user = await api_client.create_user(user_data)
        yield user
        await api_client.cleanup_user(user['user_id'])
    
    @pytest.fixture
    async def test_account(self, api_client, test_user):
        """Create test exchange account"""
        account_data = {
            'exchange': 'BINANCE',
            'account_name': 'Test Account',
            'api_key': 'test_binance_key',
            'api_secret': 'test_binance_secret',
            'is_testnet': True
        }
        
        account = await api_client.add_exchange_account(
            test_user['user_id'], 
            account_data
        )
        yield account
    
    # User Management Tests
    async def test_user_registration(self, api_client):
        """Test user registration flow"""
        user_data = {
            'telegram_id': int(datetime.now().timestamp()),
            'username': f'new_user_{uuid.uuid4().hex[:8]}',
            'risk_profile': 'HIGH'
        }
        
        response = await api_client.post('/users', json=user_data)
        assert response.status == 201
        
        user = await response.json()
        assert user['telegram_id'] == user_data['telegram_id']
        assert user['username'] == user_data['username']
        assert user['risk_profile'] == 'HIGH'
        assert user['status'] == 'ACTIVE'
        
        # Cleanup
        await api_client.cleanup_user(user['user_id'])
    
    async def test_duplicate_user_registration(self, api_client, test_user):
        """Test duplicate user registration handling"""
        duplicate_data = {
            'telegram_id': test_user['telegram_id'],
            'username': 'duplicate_user'
        }
        
        response = await api_client.post('/users', json=duplicate_data)
        assert response.status == 409
        
        error = await response.json()
        assert error['error']['code'] == 'USER_ALREADY_EXISTS'
    
    async def test_user_profile_update(self, api_client, test_user):
        """Test user profile updates"""
        update_data = {
            'risk_profile': 'ULTRA_HIGH',
            'email': 'updated@example.com'
        }
        
        response = await api_client.put(
            f'/users/{test_user["user_id"]}', 
            json=update_data
        )
        assert response.status == 200
        
        updated_user = await response.json()
        assert updated_user['risk_profile'] == 'ULTRA_HIGH'
        assert updated_user['email'] == 'updated@example.com'
    
    # Order Management Tests
    async def test_market_order_creation(self, api_client, test_account):
        """Test market order placement"""
        order_data = {
            'account_id': test_account['account_id'],
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'type': 'MARKET',
            'quantity': '0.001'
        }
        
        response = await api_client.post('/orders', json=order_data)
        assert response.status == 201
        
        order = await response.json()
        assert order['symbol'] == 'BTCUSDT'
        assert order['side'] == 'BUY'
        assert order['type'] == 'MARKET'
        assert order['status'] in ['PENDING', 'NEW', 'FILLED']
        
        return order['order_id']
    
    async def test_limit_order_creation(self, api_client, test_account):
        """Test limit order placement"""
        order_data = {
            'account_id': test_account['account_id'],
            'symbol': 'ETHUSDT',
            'side': 'BUY',
            'type': 'LIMIT',
            'quantity': '0.01',
            'price': '2000.00',  # Below market for testing
            'time_in_force': 'GTC'
        }
        
        response = await api_client.post('/orders', json=order_data)
        assert response.status == 201
        
        order = await response.json()
        assert order['type'] == 'LIMIT'
        assert order['price'] == '2000.00'
        assert order['status'] == 'NEW'
    
    async def test_order_validation(self, api_client, test_account):
        """Test order validation errors"""
        # Test negative quantity
        invalid_order = {
            'account_id': test_account['account_id'],
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'type': 'MARKET',
            'quantity': '-0.001'  # Invalid negative quantity        }
        
        response = await api_client.post('/orders', json=invalid_order)
        assert response.status == 400
        
        error = await response.json()
        assert error['error']['code'] == 'VALIDATION_ERROR'
        assert 'quantity' in str(error['error']['details'])
    
    async def test_order_cancellation(self, api_client, test_account):
        """Test order cancellation"""
        # First create a limit order
        order_data = {
            'account_id': test_account['account_id'],
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'type': 'LIMIT',
            'quantity': '0.001',
            'price': '30000.00',  # Well below market
            'time_in_force': 'GTC'
        }
        
        create_response = await api_client.post('/orders', json=order_data)
        assert create_response.status == 201
        order = await create_response.json()
        
        # Cancel the order
        cancel_response = await api_client.delete(f'/orders/{order["order_id"]}')
        assert cancel_response.status == 200
        
        # Verify order is cancelled
        get_response = await api_client.get(f'/orders/{order["order_id"]}')
        cancelled_order = await get_response.json()
        assert cancelled_order['status'] == 'CANCELLED'
    
    async def test_order_modification(self, api_client, test_account):
        """Test order modification"""
        # Create limit order
        order_data = {
            'account_id': test_account['account_id'],
            'symbol': 'ETHUSDT',
            'side': 'BUY',
            'type': 'LIMIT',
            'quantity': '0.01',
            'price': '2000.00',
            'time_in_force': 'GTC'
        }
        
        create_response = await api_client.post('/orders', json=order_data)
        order = await create_response.json()
        
        # Modify the order
        modify_data = {
            'price': '1950.00',
            'quantity': '0.02'
        }
        
        modify_response = await api_client.put(
            f'/orders/{order["order_id"]}', 
            json=modify_data
        )
        assert modify_response.status == 200
        
        modified_order = await modify_response.json()
        assert modified_order['price'] == '1950.00'
        assert modified_order['quantity'] == '0.02'
    
    # Portfolio Tests
    async def test_portfolio_summary(self, api_client, test_user):
        """Test portfolio summary retrieval"""
        response = await api_client.get(
            f'/portfolio/summary?user_id={test_user["user_id"]}'
        )
        assert response.status == 200
        
        summary = await response.json()
        assert 'total_balance_usd' in summary
        assert 'unrealized_pnl_usd' in summary
        assert 'accounts' in summary
        assert summary['user_id'] == test_user['user_id']
    
    async def test_performance_metrics(self, api_client, test_user):
        """Test performance metrics"""
        response = await api_client.get(
            f'/portfolio/performance?user_id={test_user["user_id"]}&period=7D'
        )
        assert response.status == 200
        
        performance = await response.json()
        assert 'metrics' in performance
        assert 'total_return' in performance
        assert performance['period'] == '7D'
    
    async def test_risk_analytics(self, api_client, test_user):
        """Test risk analytics"""
        response = await api_client.get(
            f'/portfolio/analytics/risk?user_id={test_user["user_id"]}'
        )
        assert response.status == 200
        
        risk = await response.json()
        assert 'risk_metrics' in risk
        assert 'var_usd' in risk['risk_metrics']
        assert risk['confidence_level'] == 0.95  # default
    
    # Rate Limiting Tests
    async def test_rate_limiting(self, api_client):
        """Test API rate limiting"""
        # Make rapid requests to trigger rate limit
        tasks = []
        for i in range(50):  # Exceed minute limit
            task = api_client.get('/portfolio/summary?user_id=test')
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check that some requests were rate limited
        rate_limited_count = sum(1 for r in responses 
                               if hasattr(r, 'status') and r.status == 429)
        assert rate_limited_count > 0
    
    # Authentication Tests
    async def test_jwt_expiration(self, api_client):
        """Test JWT token expiration handling"""
        # This would require a special test token with short expiry
        # In practice, you'd use a test environment with configurable token TTL
        pass
    
    async def test_invalid_authentication(self):
        """Test invalid authentication"""
        client = aiohttp.ClientSession()
        
        # Test with invalid token
        headers = {'Authorization': 'Bearer invalid_token'}
        async with client.get(
            'https://staging-api.patriot-trading.com/api/v1/users/test',
            headers=headers
        ) as response:
            assert response.status == 401
            error = await response.json()
            assert error['error']['code'] == 'AUTHENTICATION_FAILED'
        
        await client.close()
    
    # Error Handling Tests
    async def test_not_found_errors(self, api_client):
        """Test 404 error handling"""
        response = await api_client.get('/orders/nonexistent-order-id')
        assert response.status == 404
        
        error = await response.json()
        assert error['error']['code'] == 'ORDER_NOT_FOUND'
    
    async def test_validation_errors(self, api_client):
        """Test validation error responses"""
        invalid_data = {
            'telegram_id': 'invalid',  # Should be integer
            'username': '',            # Too short
            'risk_profile': 'INVALID'  # Invalid enum value
        }
        
        response = await api_client.post('/users', json=invalid_data)
        assert response.status == 400
        
        error = await response.json()
        assert error['error']['code'] == 'VALIDATION_ERROR'
        assert 'field_errors' in error['error']['details']
        assert len(error['error']['details']['field_errors']) >= 3
    
    # Integration Tests
    async def test_complete_trading_flow(self, api_client, test_user, test_account):
        """Test complete trading workflow"""
        # 1. Check initial portfolio
        initial_summary = await api_client.get(
            f'/portfolio/summary?user_id={test_user["user_id"]}'
        )
        initial_data = await initial_summary.json()
        
        # 2. Place a limit buy order
        buy_order_data = {
            'account_id': test_account['account_id'],
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'type': 'LIMIT',
            'quantity': '0.001',
            'price': '30000.00',  # Below market
            'time_in_force': 'GTC'
        }
        
        buy_response = await api_client.post('/orders', json=buy_order_data)
        buy_order = await buy_response.json()
        assert buy_order['status'] == 'NEW'
        
        # 3. Modify the order
        modify_response = await api_client.put(
            f'/orders/{buy_order["order_id"]}',
            json={'price': '31000.00'}
        )
        assert modify_response.status == 200
        
        # 4. Cancel the order
        cancel_response = await api_client.delete(f'/orders/{buy_order["order_id"]}')
        assert cancel_response.status == 200
        
        # 5. Verify order history
        orders_response = await api_client.get(
            f'/orders?account_id={test_account["account_id"]}&status=CANCELLED'
        )
        orders = await orders_response.json()
        cancelled_orders = [o for o in orders['orders'] 
                          if o['order_id'] == buy_order['order_id']]
        assert len(cancelled_orders) == 1
        assert cancelled_orders[0]['status'] == 'CANCELLED'
    
    async def test_risk_management_integration(self, api_client, test_account):
        """Test risk management system integration"""
        # Attempt to place order that exceeds risk limits
        large_order = {
            'account_id': test_account['account_id'],
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'type': 'MARKET',
            'quantity': '100.0'  # Very large order to trigger risk check
        }
        
        response = await api_client.post('/orders', json=large_order)
        # Should be rejected by risk management
        assert response.status == 403
        
        error = await response.json()
        assert error['error']['code'] in [
            'RISK_LIMIT_EXCEEDED', 
            'INSUFFICIENT_BALANCE',
            'POSITION_SIZE_LIMIT_EXCEEDED'
        ]


class PatriotTestClient:
    """Test client for PATRIOT API"""
    
    def __init__(self, base_url: str, api_key: str, api_secret: str):
        self.base_url = base_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = None
        self.access_token = None
        self.created_resources = []  # Track resources for cleanup
    
    async def authenticate(self):
        """Authenticate and get access token"""
        self.session = aiohttp.ClientSession()
        
        auth_data = {
            'telegram_id': 123456789,
            'username': 'test_client',
            'signature': 'test_signature'
        }
        
        async with self.session.post(
            f'{self.base_url}/auth/login',
            json=auth_data
        ) as response:
            if response.status == 200:
                auth_result = await response.json()
                self.access_token = auth_result['access_token']
            else:
                raise Exception('Authentication failed')
    
    async def get(self, endpoint: str, **kwargs):
        """Make GET request"""
        return await self._request('GET', endpoint, **kwargs)
    
    async def post(self, endpoint: str, **kwargs):
        """Make POST request"""
        return await self._request('POST', endpoint, **kwargs)
    
    async def put(self, endpoint: str, **kwargs):
        """Make PUT request"""
        return await self._request('PUT', endpoint, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs):
        """Make DELETE request"""
        return await self._request('DELETE', endpoint, **kwargs)
    
    async def _request(self, method: str, endpoint: str, **kwargs):
        """Make HTTP request with authentication"""
        url = f'{self.base_url}{endpoint}'
        
        headers = kwargs.get('headers', {})
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        headers['Content-Type'] = 'application/json'
        kwargs['headers'] = headers
        
        return await self.session.request(method, url, **kwargs)
    
    async def create_user(self, user_data: dict):
        """Create test user"""
        response = await self.post('/users', json=user_data)
        user = await response.json()
        self.created_resources.append(('user', user['user_id']))
        return user
    
    async def add_exchange_account(self, user_id: str, account_data: dict):
        """Add exchange account for user"""
        response = await self.post(f'/users/{user_id}/accounts', json=account_data)
        account = await response.json()
        self.created_resources.append(('account', account['account_id']))
        return account
    
    async def cleanup_user(self, user_id: str):
        """Clean up test user"""
        try:
            await self.delete(f'/users/{user_id}')
        except:
            pass  # Ignore cleanup errors
    
    async def cleanup(self):
        """Clean up all created resources"""
        # Clean up in reverse order
        for resource_type, resource_id in reversed(self.created_resources):
            try:
                if resource_type == 'user':
                    await self.delete(f'/users/{resource_id}')
                elif resource_type == 'account':
                    await self.delete(f'/accounts/{resource_id}')
            except:
                pass  # Ignore cleanup errors
        
        if self.session:
            await self.session.close()


# Load Testing with Locust
from locust import HttpUser, task, between

class PatriotAPILoadTest(HttpUser):
    """Load testing for PATRIOT API"""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Set up authentication for load testing"""
        # Authenticate
        auth_data = {
            'telegram_id': 123456789,
            'username': 'load_test_user',
            'signature': 'test_signature'
        }
        
        response = self.client.post('/auth/login', json=auth_data)
        if response.status_code == 200:
            auth_result = response.json()
            self.access_token = auth_result['access_token']
            self.user_id = auth_result['user']['user_id']
            
            # Set authorization header
            self.client.headers.update({
                'Authorization': f'Bearer {self.access_token}'
            })
        else:
            self.access_token = None
    
    @task(3)
    def get_portfolio_summary(self):
        """Test portfolio summary endpoint"""
        if self.access_token:
            self.client.get(f'/portfolio/summary?user_id={self.user_id}')
    
    @task(2)
    def get_market_data(self):
        """Test market data endpoint"""
        self.client.get('/market/ticker/BTCUSDT')
    
    @task(1)
    def create_and_cancel_order(self):
        """Test order creation and cancellation"""
        if self.access_token:
            # Create limit order
            order_data = {
                'account_id': 'test-account-id',
                'symbol': 'BTCUSDT',
                'side': 'BUY',
                'type': 'LIMIT',
                'quantity': '0.001',
                'price': '30000.00'
            }
            
            response = self.client.post('/orders', json=order_data)
            if response.status_code == 201:
                order = response.json()
                # Cancel the order
                self.client.delete(f'/orders/{order["order_id"]}')
    
    @task(1)
    def get_performance_metrics(self):
        """Test performance metrics endpoint"""
        if self.access_token:
            self.client.get(
                f'/portfolio/performance?user_id={self.user_id}&period=1D'
            )

# Run tests with:
# pytest test_patriot_api.py -v
# locust -f test_patriot_api.py --host=https://staging-api.patriot-trading.com/api/v1
```

---

## 📋 API Documentation Standards

### Documentation Generation

```yaml
# OpenAPI documentation configuration
openapi_config:
  title: PATRIOT Trading System API
  version: "2.0.0"
  description: |
    High-performance trading API for cryptocurrency exchanges with advanced 
    risk management, portfolio analytics, and real-time data streaming.
    
    ## Authentication
    
    The API supports multiple authentication methods:
    - **JWT Tokens**: For web applications and user sessions
    - **API Keys**: For programmatic access and trading bots
    - **WebSocket**: Token-based authentication for real-time streams
    
    ## Rate Limits
    
    All endpoints are rate limited to ensure fair usage:
    - **Authenticated Users**: 1000 requests/minute, 10000 requests/hour
    - **API Keys**: Varies by tier (100-500 requests/minute)
    - **Order Creation**: 100 orders/minute with 100ms cooldown
    
    ## Error Handling
    
    The API returns standardized error responses with:
    - Machine-readable error codes
    - Human-readable messages
    - Detailed validation errors
    - Request IDs for debugging
    
    ## SDKs and Libraries
    
    Official SDKs available for:
    - Python: `pip install patriot-trading-sdk`
    - JavaScript/Node.js: `npm install patriot-trading-js`
    - Go: `go get github.com/patriot-trading/go-sdk`
    
  contact:
    name: PATRIOT API Support
    url: https://support.patriot-trading.com
    email: api-support@patriot-trading.com
  
  license:
    name: MIT
    url: https://opensource.org/licenses/MIT
  
  servers:
    - url: https://api.patriot-trading.com/api/v1
      description: Production server
    - url: https://staging-api.patriot-trading.com/api/v1
      description: Staging server
    - url: https://sandbox-api.patriot-trading.com/api/v1
      description: Sandbox server (testnet)
  
  security:
    - BearerAuth: []
    - ApiKeyAuth: []
  
  tags:
    - name: Authentication
      description: User authentication and API key management
    - name: Users
      description: User registration and profile management
    - name: Orders
      description: Order placement, modification, and tracking
    - name: Portfolio
      description: Portfolio analytics and position management
    - name: Risk
      description: Risk management and monitoring
    - name: Market Data
      description: Real-time and historical market data
    - name: WebSocket
      description: Real-time data streaming

  components:
    securitySchemes:
      BearerAuth:
        type: http
        scheme: bearer
        bearerFormat: JWT
        description: JWT token obtained from /auth/login endpoint
      ApiKeyAuth:
        type: apiKey
        in: header
        name: Authorization
        description: |
          API key authentication using the format: `ApiKey <api_key>`
          
          Additional required headers:
          - X-API-Secret: HMAC signature of the request
          - X-API-Timestamp: Unix timestamp in milliseconds
```

### Interactive API Explorer

```html
<!-- API Documentation Page -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PATRIOT Trading API Documentation</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css" />
    <style>
        body { margin: 0; padding: 0; }
        .swagger-ui .topbar { display: none; }
        .api-explorer { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .hero-section { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 60px 20px; 
            text-align: center;
        }
        .hero-section h1 { font-size: 3rem; margin-bottom: 1rem; }
        .hero-section p { font-size: 1.2rem; margin-bottom: 2rem; }
        .cta-buttons { display: flex; gap: 20px; justify-content: center; flex-wrap: wrap; }
        .cta-button { 
            background: rgba(255,255,255,0.2); 
            border: 2px solid white; 
            color: white; 
            padding: 12px 24px; 
            text-decoration: none; 
            border-radius: 5px; 
            font-weight: bold;
        }
        .cta-button:hover { background: rgba(255,255,255,0.3); }
        .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 30px; padding: 60px 20px; }
        .feature { text-align: center; }
        .feature h3 { color: #333; margin-bottom: 1rem; }
        .code-examples { background: #f8f9fa; padding: 60px 20px; }
        .code-examples h2 { text-align: center; margin-bottom: 3rem; }
        .code-example { margin-bottom: 2rem; }
        .code-example h3 { color: #333; margin-bottom: 1rem; }
    </style>
</head>
<body>
    <!-- Hero Section -->
    <div class="hero-section">
        <h1>PATRIOT Trading API</h1>
        <p>High-performance cryptocurrency trading API with advanced risk management and portfolio analytics</p>
        <div class="cta-buttons">
            <a href="#api-explorer" class="cta-button">Explore API</a>
            <a href="https://github.com/patriot-trading/examples" class="cta-button">View Examples</a>
            <a href="https://support.patriot-trading.com" class="cta-button">Get Support</a>
        </div>
    </div>

    <!-- Features -->
    <div class="features">
        <div class="feature">
            <h3>⚡ High Performance</h3>
            <p>Sub-millisecond order execution with 99.99% uptime and advanced caching for optimal performance.</p>
        </div>
        <div class="feature">
            <h3>🛡️ Risk Management</h3>
            <p>Built-in risk controls with real-time monitoring, position limits, and automated risk alerts.</p>
        </div>
        <div class="feature">
            <h3>📊 Advanced Analytics</h3>
            <p>Comprehensive portfolio analytics with performance metrics, risk analytics, and custom reporting.</p>
        </div>
        <div class="feature">
            <h3>🔄 Real-time Data</h3>
            <p>WebSocket streams for live market data, order updates, and portfolio changes with low latency.</p>
        </div>
        <div class="feature">
            <h3>🌐 Multi-Exchange</h3>
            <p>Unified API supporting Binance, Bybit, OKX, MEXC with smart order routing and aggregation.</p>
        </div>
        <div class="feature">
            <h3>🔧 Developer Friendly</h3>
            <p>Comprehensive SDKs, detailed documentation, and extensive examples for rapid integration.</p>
        </div>
    </div>

    <!-- Code Examples -->
    <div class="code-examples">
        <h2>Quick Start Examples</h2>
        
        <div class="code-example">
            <h3>Python - Place Market Order</h3>
            <pre><code>from patriot_trading import PatriotClient

client = PatriotClient(api_key='your_key', api_secret='your_secret')
await client.authenticate()

order = await client.orders.create_market_order(
    account_id='account-uuid',
    symbol='BTCUSDT',
    side='BUY',
    quantity='0.001'
)
print(f"Order placed: {order['order_id']}")
</code></pre>
        </div>

        <div class="code-example">
            <h3>JavaScript - Portfolio Summary</h3>
            <pre><code>const { PatriotClient } = require('patriot-trading-js');

const client = new PatriotClient({
    apiKey: 'your_key',
    apiSecret: 'your_secret'
});

await client.authenticate();

const portfolio = await client.portfolio.getSummary();
console.log(`Portfolio Value: $${portfolio.total_balance_usd}`);
</code></pre>
        </div>

        <div class="code-example">
            <h3>cURL - Get Market Data</h3>
            <pre><code>curl -X GET "https://api.patriot-trading.com/api/v1/market/ticker/BTCUSDT" \
     -H "Authorization: Bearer your_jwt_token" \
     -H "Content-Type: application/json"
</code></pre>
        </div>
    </div>

    <!-- API Explorer -->
    <div id="api-explorer" class="api-explorer">
        <div id="swagger-ui"></div>
    </div>

    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-standalone-preset.js"></script>
    <script>
        SwaggerUIBundle({
            url: 'https://api.patriot-trading.com/api/v1/openapi.json',
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIStandalonePreset
            ],
            plugins: [
                SwaggerUIBundle.plugins.DownloadUrl
            ],
            layout: "StandaloneLayout",
            requestInterceptor: (request) => {
                // Add API key if available
                const apiKey = localStorage.getItem('patriot_api_key');
                if (apiKey) {
                    request.headers['Authorization'] = `Bearer ${apiKey}`;
                }
                return request;
            },
            responseInterceptor: (response) => {
                // Handle rate limiting
                if (response.status === 429) {
                    const retryAfter = response.headers['retry-after'];
                    console.warn(`Rate limited. Retry after: ${retryAfter} seconds`);
                }
                return response;
            }
        });
    </script>
</body>
</html>
```

---

> **API Documentation Status:**
> - ✅ Complete OpenAPI 3.0 specifications for all endpoints
> - ✅ Comprehensive authentication and authorization examples  
> - ✅ Real-time WebSocket API with subscription management
> - ✅ Advanced order management with bracket orders and smart routing
> - ✅ Portfolio analytics with performance metrics and risk analysis
> - ✅ Official SDKs for Python, JavaScript, and integration examples
> - ✅ Extensive test suites with unit, integration, and load tests
> - ✅ Interactive API explorer with live documentation
> - ✅ Rate limiting, error handling, and security specifications

> **Key API Features:**
> 1. **High Performance**: Sub-millisecond response times with advanced caching
> 2. **Security First**: JWT authentication, API keys, rate limiting, CORS protection
> 3. **Real-time Streams**: WebSocket APIs for live market data and portfolio updates
> 4. **Advanced Orders**: Market, limit, stop orders with bracket trading support
> 5. **Risk Management**: Built-in risk checks with configurable limits and alerts  
> 6. **Portfolio Analytics**: Comprehensive performance metrics and risk analysis
> 7. **Developer Experience**: Complete SDKs, examples, and interactive documentation
> 8. **Production Ready**: Comprehensive testing, monitoring, and error handling

> **Integration Support:**
> - Complete REST API with 50+ endpoints
> - WebSocket streams for real-time data  
> - Official SDKs in Python, JavaScript, Go
> - Postman collections and automated tests
> - Interactive API documentation
> - Comprehensive error handling and rate limiting
> - Production-ready security and authentication

The PATRIOT API is now fully documented and ready for integration with trading applications, portfolio management tools, and automated trading systems! 🚀
