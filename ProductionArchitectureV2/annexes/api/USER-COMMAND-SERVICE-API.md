# User Command Service API Documentation

## 📋 Service Information

**Service ID**: COMP-001  
**Port**: 8001  
**Base URL**: `/api/v1/users`  
**Authentication**: JWT Bearer Token  
**Rate Limiting**: 100 requests/minute per user

## 🔗 Quick Links
- [Health Check](#health-endpoints)
- [User Registration](#user-registration)
- [Profile Management](#profile-management)
- [Account Linking](#account-linking)
- [Administrative](#admin-endpoints)
- [Error Codes](#error-handling)

## 📊 Health Endpoints

### Service Health Check
```typescript
GET /api/v1/users/health
```

**Response:**
```json
{
  "service": "user-command-service",
  "status": "healthy",
  "version": "2.1.0",
  "timestamp": "2025-09-27T08:00:00Z",
  "dependencies": {
    "database": "healthy",
    "event_bus": "healthy",
    "encryption_service": "healthy"
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
    "kafka_connection": "pass",
    "encryption_keys_loaded": "pass"
  }
}
```

## 👤 User Registration

### Register New User
```typescript
POST /api/v1/users
Content-Type: application/json
X-Request-ID: req_1695587400_abc123
```

**Request Body:**
```json
{
  "telegram_id": 123456789,
  "username": "crypto_trader_pro",
  "email": "trader@example.com",
  "risk_profile": "MEDIUM"
}
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
  "event_id": "evt_user_registered_abc123"
}
```

## 👤 Profile Management

### Update User Profile
```typescript
PUT /api/v1/users/{user_id}
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "updated_email@example.com",
  "risk_profile": "HIGH",
  "notification_preferences": {
    "email_enabled": true,
    "telegram_enabled": true,
    "trade_notifications": true,
    "risk_alerts": true
  }
}
```

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "updated_fields": ["email", "risk_profile", "notification_preferences"],
  "updated_at": "2025-09-27T08:15:00Z",
  "event_id": "evt_user_updated_def456"
}
```

### Update Risk Profile
```typescript
PATCH /api/v1/users/{user_id}/risk-profile
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "risk_profile": "ULTRA_HIGH",
  "justification": "Experienced trader with high risk tolerance"
}
```

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "previous_risk_profile": "HIGH",
  "new_risk_profile": "ULTRA_HIGH",
  "updated_at": "2025-09-27T08:20:00Z",
  "event_id": "evt_risk_profile_updated_ghi789"
}
```

## 🔗 Account Linking

### Add Exchange Account
```typescript
POST /api/v1/users/{user_id}/accounts
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "exchange": "BINANCE",
  "account_name": "Main Trading Account",
  "api_key": "your_binance_api_key",
  "api_secret": "your_binance_api_secret",
  "is_testnet": false,
  "permissions_verified": true
}
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
  "event_id": "evt_account_added_jkl012"
}
```

### Update Exchange Account
```typescript
PUT /api/v1/users/{user_id}/accounts/{account_id}
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "account_name": "Updated Account Name",
  "api_key": "new_api_key",
  "api_secret": "new_api_secret"
}
```

**Response:**
```json
{
  "account_id": "acc_550e8400e29b41d4a716446655440000",
  "updated_fields": ["account_name", "api_credentials"],
  "updated_at": "2025-09-27T08:30:00Z",
  "event_id": "evt_account_updated_mno345"
}
```

### Remove Exchange Account
```typescript
DELETE /api/v1/users/{user_id}/accounts/{account_id}
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "account_id": "acc_550e8400e29b41d4a716446655440000",
  "status": "DELETED",
  "deleted_at": "2025-09-27T08:35:00Z",
  "event_id": "evt_account_deleted_pqr678"
}
```

## 🛠️ Administrative Endpoints  

### Deactivate User (Admin)
```typescript
PATCH /api/v1/users/{user_id}/deactivate
Authorization: Bearer <admin_jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "reason": "Policy violation",
  "effective_date": "2025-09-27T12:00:00Z",
  "notify_user": true
}
```

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "DEACTIVATED",
  "reason": "Policy violation",
  "deactivated_at": "2025-09-27T08:40:00Z",
  "deactivated_by": "admin_user_id",
  "event_id": "evt_user_deactivated_stu901"
}
```

### Bulk User Operations (Admin)
```typescript
POST /api/v1/users/bulk
Authorization: Bearer <admin_jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "operation": "UPDATE_RISK_PROFILE",
  "user_ids": ["user1", "user2", "user3"],
  "data": {
    "risk_profile": "MEDIUM"
  }
}
```

**Response:**
```json
{
  "operation_id": "bulk_op_abc123",
  "total_users": 3,
  "successful": 3,
  "failed": 0,
  "event_id": "evt_bulk_operation_vwx234"
}
```

## ❌ Error Handling

### Common Error Responses

#### 400 Bad Request
```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid user data provided",
  "details": {
    "validation_errors": [
      {
        "field": "telegram_id",
        "message": "Telegram ID is required"
      },
      {
        "field": "risk_profile",
        "message": "Must be one of: LOW, MEDIUM, HIGH, ULTRA_HIGH"
      }
    ]
  },
  "request_id": "req_1695587400_abc123",
  "timestamp": "2025-09-27T08:00:00Z"
}
```

#### 409 Conflict
```json
{
  "error": "USER_ALREADY_EXISTS",
  "message": "User with this Telegram ID already exists",
  "details": {
    "existing_user_id": "550e8400-e29b-41d4-a716-446655440000",
    "telegram_id": 123456789
  },
  "request_id": "req_1695587400_def456",
  "timestamp": "2025-09-27T08:00:00Z"
}
```

#### 422 Unprocessable Entity
```json
{
  "error": "INVALID_API_CREDENTIALS",
  "message": "Exchange API credentials validation failed",
  "details": {
    "exchange": "BINANCE",
    "validation_errors": [
      "API key does not have trading permissions",
      "API key has withdrawal permissions (not allowed)"
    ]
  },
  "request_id": "req_1695587400_ghi789",
  "timestamp": "2025-09-27T08:00:00Z"
}
```

## 📖 Examples

### Complete User Onboarding Flow

```typescript
import axios from 'axios';

class UserCommandAPI {
  private baseURL: string;
  private authToken?: string;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  async registerUser(userData: {
    telegram_id: number;
    username: string;
    email?: string;
    risk_profile?: string;
  }) {
    const response = await axios.post(`${this.baseURL}/users`, userData, {
      headers: {
        'Content-Type': 'application/json',
        'X-Request-ID': this.generateRequestId()
      }
    });
    return response.data;
  }

  async addExchangeAccount(userId: string, accountData: any) {
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
const userAPI = new UserCommandAPI('https://api.patriot-trading.com/api/v1');

async function onboardUser() {
  try {
    // 1. Register user
    const user = await userAPI.registerUser({
      telegram_id: 123456789,
      username: 'crypto_trader_pro',
      email: 'trader@example.com',
      risk_profile: 'MEDIUM'
    });
    
    // 2. Add exchange account
    const account = await userAPI.addExchangeAccount(user.user_id, {
      exchange: 'BINANCE',
      account_name: 'Main Trading Account',
      api_key: 'your_api_key',
      api_secret: 'your_api_secret',
      is_testnet: false
    });
    
    console.log('User onboarded successfully:', user.user_id);
    
  } catch (error) {
    console.error('Onboarding failed:', error);
  }
}
```

## 🔄 Integration Notes

### Event-Driven Architecture
All user command operations publish events to Kafka topics:
- `user.registered` - User registration events
- `user.updated` - Profile update events  
- `user.deactivated` - User deactivation events
- `account.added` - Exchange account addition events
- `account.updated` - Exchange account update events
- `account.removed` - Exchange account removal events

### API Key Validation
Exchange API credentials are validated before storage:
- **Required permissions**: Trade, read account data
- **Prohibited permissions**: Withdraw, transfer funds
- **IP restrictions**: API keys should be restricted to system IPs
- **Rate limits**: Validate sufficient rate limits for trading operations

### Security Considerations
- All API credentials are encrypted at rest using AES-256
- Sensitive operations require additional authentication
- All commands are logged for audit purposes
- Rate limiting: 100 requests/minute per user

### Request IDs
Include `X-Request-ID` header for request tracking:
```bash
X-Request-ID: req_1695587400_abc123
```

### Idempotency
User registration and account operations support idempotency using request IDs.
Duplicate requests with same ID return original response within 24 hours.

---

> **📚 Documentation Navigation:**  
> [← Back to API Overview](../ANNEX-E-API-OVERVIEW.md) | [All Service APIs](./) | [Component Specs](../../03-COMPONENT-SPECIFICATIONS.md)
