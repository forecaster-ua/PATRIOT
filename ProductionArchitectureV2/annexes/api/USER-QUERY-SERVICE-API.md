# User Query Service API Documentation

## 📋 Service Information

**Service ID**: COMP-002  
**Port**: 8002  
**Base URL**: `/api/v1/users`  
**Authentication**: JWT Bearer Token  
**Rate Limiting**: 200 requests/minute per user

## 🔗 Quick Links
- [Health Check](#health-endpoints)
- [User Queries](#user-queries)
- [Account Information](#account-information)
- [Activity History](#activity-history)
- [Search Operations](#search-operations)
- [Error Codes](#error-handling)

## 📊 Health Endpoints

### Service Health Check
```typescript
GET /api/v1/users/health
```

**Response:**
```json
{
  "service": "user-query-service",
  "status": "healthy",
  "version": "2.1.0",
  "timestamp": "2025-09-27T08:00:00Z",
  "dependencies": {
    "database": "healthy",
    "cache": "healthy",
    "read_replica": "healthy"
  }
}
```

### Service Readiness
```typescript
GET /api/v1/users/ready
```

**Response:**
```json
{
  "ready": true,
  "checks": {
    "database_connection": "pass",
    "redis_connection": "pass",
    "query_performance": "pass"
  }
}
```

## 👤 User Queries

### Get User Profile
```typescript
GET /api/v1/users/{user_id}
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "telegram_id": 123456789,
  "username": "crypto_trader_pro",
  "email": "trader@example.com",
  "risk_profile": "MEDIUM",
  "status": "ACTIVE",
  "created_at": "2025-09-27T08:00:00Z",
  "last_login": "2025-09-27T07:45:00Z",
  "permissions": ["trade", "view_portfolio", "manage_accounts"],
  "notification_preferences": {
    "email_enabled": true,
    "telegram_enabled": true,
    "trade_notifications": true,
    "risk_alerts": true
  },
  "verification": {
    "email_verified": true,
    "telegram_verified": true,
    "kyc_status": "COMPLETED"
  }
}
```

### Get Current User Profile
```typescript
GET /api/v1/users/me
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "telegram_id": 123456789,
  "username": "crypto_trader_pro",
  "email": "trader@example.com",
  "risk_profile": "MEDIUM",
  "status": "ACTIVE",
  "created_at": "2025-09-27T08:00:00Z",
  "permissions": ["trade", "view_portfolio"],
  "active_sessions": 2,
  "last_activity": "2025-09-27T08:45:00Z"
}
```

### List Users (Admin)
```typescript
GET /api/v1/users?page=1&limit=20&status=ACTIVE&risk_profile=MEDIUM
Authorization: Bearer <admin_jwt_token>
```

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20, max: 100)
- `status` (optional): Filter by status (ACTIVE, INACTIVE, SUSPENDED)
- `risk_profile` (optional): Filter by risk profile
- `created_after` (optional): Filter by creation date
- `search` (optional): Search by username or email

**Response:**
```json
{
  "users": [
    {
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "crypto_trader_pro",
      "email": "trader@example.com",
      "risk_profile": "MEDIUM",
      "status": "ACTIVE",
      "created_at": "2025-09-27T08:00:00Z",
      "last_activity": "2025-09-27T08:45:00Z",
      "account_count": 2
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 1,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false
  }
}
```

## 📊 Account Information

### List User Accounts
```typescript
GET /api/v1/users/{user_id}/accounts
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "accounts": [
    {
      "account_id": "acc_550e8400e29b41d4a716446655440000",
      "exchange": "BINANCE",
      "account_name": "Main Trading Account",
      "status": "ACTIVE",
      "permissions": ["trade", "read"],
      "verification_status": "VERIFIED",
      "created_at": "2025-09-27T08:25:00Z",
      "last_sync": "2025-09-27T08:50:00Z",
      "balance_summary": {
        "total_balance_usd": 50000.00,
        "available_balance_usd": 45000.00,
        "in_use_balance_usd": 5000.00
      }
    }
  ],
  "total_accounts": 1,
  "active_accounts": 1
}
```

### Get Account Details
```typescript
GET /api/v1/users/{user_id}/accounts/{account_id}
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "account_id": "acc_550e8400e29b41d4a716446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "exchange": "BINANCE",
  "account_name": "Main Trading Account",
  "status": "ACTIVE",
  "permissions": ["trade", "read"],
  "verification_status": "VERIFIED",
  "created_at": "2025-09-27T08:25:00Z",
  "last_sync": "2025-09-27T08:50:00Z",
  "api_key_info": {
    "key_partial": "abc123...def456",
    "permissions": ["SPOT", "FUTURES", "MARGIN"],
    "ip_restrictions": true,
    "expires_at": null
  },
  "trading_stats": {
    "total_trades": 1250,
    "win_rate": 0.68,
    "total_volume_usd": 2500000.00,
    "profit_loss_usd": 12500.00
  }
}
```

### Get Account Balance
```typescript
GET /api/v1/users/{user_id}/accounts/{account_id}/balance
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "account_id": "acc_550e8400e29b41d4a716446655440000",
  "exchange": "BINANCE",
  "balances": [
    {
      "asset": "USDT",
      "free": "45000.00000000",
      "locked": "5000.00000000",
      "total": "50000.00000000"
    },
    {
      "asset": "BTC",
      "free": "0.15000000",
      "locked": "0.05000000",
      "total": "0.20000000"
    }
  ],
  "total_balance_usd": 50000.00,
  "last_updated": "2025-09-27T08:50:00Z"
}
```

## 📈 Activity History

### Get User Activity Log
```typescript
GET /api/v1/users/{user_id}/activity?type=LOGIN&limit=50&after=2025-09-26T00:00:00Z
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
- `type` (optional): Activity type (LOGIN, LOGOUT, TRADE, ACCOUNT_UPDATE, etc.)
- `limit` (optional): Number of records (default: 50, max: 200)
- `after` (optional): Get activities after this timestamp
- `before` (optional): Get activities before this timestamp

**Response:**
```json
{
  "activities": [
    {
      "activity_id": "act_abc123def456",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "type": "LOGIN",
      "description": "User logged in via Telegram",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "timestamp": "2025-09-27T07:45:00Z",
      "metadata": {
        "session_id": "sess_abc123def456",
        "login_method": "telegram"
      }
    }
  ],
  "pagination": {
    "limit": 50,
    "has_more": false,
    "next_cursor": null
  }
}
```

### Get Trading Activity
```typescript
GET /api/v1/users/{user_id}/trading-activity?account_id=acc_123&days=7
Authorization: Bearer <jwt_token>
```

**Query Parameters:**
- `account_id` (optional): Filter by specific account
- `days` (optional): Number of days to look back (default: 7, max: 90)
- `symbol` (optional): Filter by trading pair

**Response:**
```json
{
  "trading_summary": {
    "period": "7_days",
    "total_trades": 45,
    "winning_trades": 28,
    "losing_trades": 17,
    "win_rate": 0.622,
    "total_volume_usd": 125000.00,
    "profit_loss_usd": 1250.50
  },
  "recent_trades": [
    {
      "trade_id": "trade_abc123",
      "symbol": "BTCUSDT",
      "side": "BUY",
      "quantity": "0.1",
      "price": "45000.00",
      "total_usd": 4500.00,
      "timestamp": "2025-09-27T08:30:00Z",
      "profit_loss_usd": 125.50
    }
  ]
}
```

## 🔍 Search Operations

*Content to be migrated from ANNEX-E*

## ❌ Error Handling

### Common Error Responses

#### 404 Not Found
```json
{
  "error": "USER_NOT_FOUND",
  "message": "User with specified ID does not exist",
  "details": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000"
  },
  "request_id": "req_1695587400_abc123",
  "timestamp": "2025-09-27T08:00:00Z"
}
```

#### 403 Forbidden
```json
{
  "error": "ACCESS_DENIED",
  "message": "User does not have permission to access this resource",
  "details": {
    "required_permissions": ["admin"],
    "user_permissions": ["trade", "view_portfolio"]
  },
  "request_id": "req_1695587400_def456",
  "timestamp": "2025-09-27T08:00:00Z"
}
```

#### 400 Bad Request
```json
{
  "error": "INVALID_QUERY_PARAMETERS",
  "message": "Invalid query parameters provided",
  "details": {
    "validation_errors": [
      {
        "parameter": "limit",
        "message": "Limit must be between 1 and 200"
      },
      {
        "parameter": "after",
        "message": "Invalid timestamp format"
      }
    ]
  },
  "request_id": "req_1695587400_ghi789",
  "timestamp": "2025-09-27T08:00:00Z"
}
```

## 📖 Examples

### Complete User Query Integration

```typescript
import axios from 'axios';

class UserQueryAPI {
  private baseURL: string;
  private authToken: string;

  constructor(baseURL: string, authToken: string) {
    this.baseURL = baseURL;
    this.authToken = authToken;
  }

  async getUserProfile(userId: string) {
    const response = await axios.get(`${this.baseURL}/users/${userId}`, {
      headers: { 'Authorization': `Bearer ${this.authToken}` }
    });
    return response.data;
  }

  async getCurrentUserProfile() {
    const response = await axios.get(`${this.baseURL}/users/me`, {
      headers: { 'Authorization': `Bearer ${this.authToken}` }
    });
    return response.data;
  }

  async getUserAccounts(userId: string) {
    const response = await axios.get(`${this.baseURL}/users/${userId}/accounts`, {
      headers: { 'Authorization': `Bearer ${this.authToken}` }
    });
    return response.data;
  }

  async getUserActivity(userId: string, options: {
    type?: string;
    limit?: number;
    after?: string;
  } = {}) {
    const params = new URLSearchParams();
    if (options.type) params.append('type', options.type);
    if (options.limit) params.append('limit', options.limit.toString());
    if (options.after) params.append('after', options.after);

    const response = await axios.get(
      `${this.baseURL}/users/${userId}/activity?${params.toString()}`,
      { headers: { 'Authorization': `Bearer ${this.authToken}` } }
    );
    return response.data;
  }

  async searchUsers(query: string, type: 'username' | 'email' | 'telegram_id' = 'username') {
    const response = await axios.get(
      `${this.baseURL}/users/search?q=${encodeURIComponent(query)}&type=${type}`,
      { headers: { 'Authorization': `Bearer ${this.authToken}` } }
    );
    return response.data;
  }
}

// Usage example
const queryAPI = new UserQueryAPI('https://api.patriot-trading.com/api/v1', 'your_jwt_token');

async function displayUserDashboard() {
  try {
    // Get current user profile
    const profile = await queryAPI.getCurrentUserProfile();
    console.log(`Welcome back, ${profile.username}!`);

    // Get user accounts
    const accounts = await queryAPI.getUserAccounts(profile.user_id);
    console.log(`You have ${accounts.total_accounts} trading accounts`);

    // Get recent activity
    const activity = await queryAPI.getUserActivity(profile.user_id, {
      limit: 10,
      type: 'LOGIN'
    });
    
    console.log('Recent login activity:', activity.activities);

  } catch (error) {
    console.error('Error loading dashboard:', error);
  }
}
```

### Python Query Example

```python
import requests
from typing import Optional, Dict, List
from datetime import datetime

class UserQueryClient:
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        })
    
    def get_user_profile(self, user_id: str) -> Dict:
        """Get detailed user profile information"""
        response = self.session.get(f'{self.base_url}/users/{user_id}')
        response.raise_for_status()
        return response.json()
    
    def get_current_user(self) -> Dict:
        """Get current authenticated user profile"""
        response = self.session.get(f'{self.base_url}/users/me')
        response.raise_for_status()
        return response.json()
    
    def list_user_accounts(self, user_id: str) -> Dict:
        """Get all exchange accounts for user"""
        response = self.session.get(f'{self.base_url}/users/{user_id}/accounts')
        response.raise_for_status()
        return response.json()
    
    def get_trading_activity(self, user_id: str, days: int = 7) -> Dict:
        """Get recent trading activity summary"""
        response = self.session.get(
            f'{self.base_url}/users/{user_id}/trading-activity?days={days}'
        )
        response.raise_for_status()
        return response.json()

# Usage
client = UserQueryClient('https://api.patriot-trading.com/api/v1', 'your_token')

# Get user information
user = client.get_current_user()
print(f"User: {user['username']}, Risk Profile: {user['risk_profile']}")

# Get trading activity
activity = client.get_trading_activity(user['user_id'], days=30)
print(f"Total trades: {activity['trading_summary']['total_trades']}")
print(f"Win rate: {activity['trading_summary']['win_rate']:.2%}")
```

## 🔄 Integration Notes

*Content to be migrated from ANNEX-E*

---

> **📚 Documentation Navigation:**  
> [← Back to API Overview](../ANNEX-E-API-OVERVIEW.md) | [All Service APIs](./) | [Component Specs](../../03-COMPONENT-SPECIFICATIONS.md)
