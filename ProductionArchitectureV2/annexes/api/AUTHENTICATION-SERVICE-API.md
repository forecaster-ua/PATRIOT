# Authentication Service API Documentation

## 📋 Service Information

**Service ID**: COMP-010  
**Port**: 8010  
**Base URL**: `/api/v1/auth`  
**Authentication**: Mixed (public and protected endpoints)  
**Rate Limiting**: 50 requests/minute per IP

## 🔗 Quick Links
- [Health Check](#health-endpoints)
- [Authentication](#authentication-endpoints)
- [Token Management](#token-management)
- [Role Management](#role-management)
- [Session Management](#session-management)
- [Administrative](#admin-endpoints)
- [Error Codes](#error-handling)

## 📊 Health Endpoints

### Service Health Check
```typescript
GET /api/v1/auth/health
```

**Response:**
```json
{
  "service": "authentication-service",
  "status": "healthy",
  "version": "2.1.0",
  "timestamp": "2025-09-27T08:00:00Z",
  "dependencies": {
    "database": "healthy",
    "redis": "healthy",
    "jwt_service": "healthy"
  }
}
```

### Service Readiness
```typescript
GET /api/v1/auth/ready
```

**Response:**
```json
{
  "ready": true,
  "checks": {
    "database_connection": "pass",
    "redis_connection": "pass",
    "jwt_keys_loaded": "pass"
  }
}
```

## 🔐 Authentication Endpoints

### User Login via Telegram
```typescript
POST /api/v1/auth/login
Content-Type: application/json
```

**Request Body:**
```json
{
  "telegram_id": 123456789,
  "username": "trader_user",
  "signature": "telegram_auth_signature"
}
```

**Response:**
```json
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

### Refresh Token
```typescript
POST /api/v1/auth/refresh
Content-Type: application/json
```

**Request Body:**
```json
{
  "refresh_token": "refresh_token_here"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600,
  "token_type": "Bearer"
}
```

### Logout
```typescript
POST /api/v1/auth/logout
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "message": "Successfully logged out",
  "logged_out_at": "2025-09-27T08:00:00Z"
}
```

## 🎫 Token Management

### Create API Key
```typescript
POST /api/v1/auth/api-keys
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
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
```

**Response:**
```json
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

### List API Keys
```typescript
GET /api/v1/auth/api-keys
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "api_keys": [
    {
      "api_key_id": "ak_550e8400e29b41d4a716446655440000",
      "name": "Trading Bot API Key",
      "created_at": "2025-09-24T20:50:00Z",
      "last_used_at": "2025-09-27T07:30:00Z",
      "permissions": ["trade", "view_portfolio"],
      "status": "active"
    }
  ]
}
```

### Revoke API Key
```typescript
DELETE /api/v1/auth/api-keys/{api_key_id}
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "message": "API key revoked successfully",
  "revoked_at": "2025-09-27T08:00:00Z"
}
```

## 👥 Role Management

### Get User Permissions
```typescript
GET /api/v1/auth/permissions
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "permissions": [
    "trade",
    "view_portfolio",
    "manage_accounts"
  ],
  "roles": ["trader"],
  "risk_profile": "MEDIUM"
}
```

### Update User Permissions (Admin)
```typescript
PUT /api/v1/auth/users/{user_id}/permissions
Authorization: Bearer <admin_jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "permissions": ["trade", "view_portfolio", "manage_accounts", "admin"],
  "roles": ["trader", "admin"],
  "risk_profile": "HIGH"
}
```

**Response:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "updated_permissions": ["trade", "view_portfolio", "manage_accounts", "admin"],
  "updated_roles": ["trader", "admin"],
  "updated_at": "2025-09-27T08:00:00Z"
}
```

## 🕐 Session Management

### Get Active Sessions
```typescript
GET /api/v1/auth/sessions
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "sess_abc123def456",
      "device_type": "web",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "created_at": "2025-09-27T06:00:00Z",
      "last_activity": "2025-09-27T07:45:00Z",
      "is_current": true
    }
  ],
  "total_sessions": 1
}
```

### Terminate Session
```typescript
DELETE /api/v1/auth/sessions/{session_id}
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "message": "Session terminated successfully",
  "terminated_at": "2025-09-27T08:00:00Z"
}
```

### Terminate All Sessions
```typescript
DELETE /api/v1/auth/sessions
Authorization: Bearer <jwt_token>
```

**Response:**
```json
{
  "message": "All sessions terminated",
  "sessions_terminated": 3,
  "terminated_at": "2025-09-27T08:00:00Z"
}
```

## 🛠️ Administrative Endpoints  

### System Authentication Status
```typescript
GET /api/v1/auth/admin/status
Authorization: Bearer <admin_jwt_token>
```

**Response:**
```json
{
  "total_active_sessions": 45,
  "total_active_api_keys": 12,
  "authentication_rate": {
    "last_hour": 234,
    "last_24h": 2840
  },
  "failed_attempts": {
    "last_hour": 5,
    "last_24h": 23
  }
}
```

### Force User Logout
```typescript
POST /api/v1/auth/admin/users/{user_id}/logout
Authorization: Bearer <admin_jwt_token>
```

**Response:**
```json
{
  "message": "User logged out successfully",
  "sessions_terminated": 2,
  "logged_out_at": "2025-09-27T08:00:00Z"
}
```

## ❌ Error Handling

### Common Error Responses

#### 401 Unauthorized
```json
{
  "error": "AUTHENTICATION_FAILED",
  "message": "Invalid or expired JWT token",
  "details": {
    "reason": "Invalid or expired JWT token",
    "token_expired_at": "2025-09-24T19:50:00Z",
    "refresh_required": true
  },
  "request_id": "req_1695587400_def456",
  "timestamp": "2025-09-24T20:50:00Z"
}
```

#### 403 Forbidden
```json
{
  "error": "INSUFFICIENT_PERMISSIONS",
  "message": "User does not have required permissions",
  "details": {
    "required_permissions": ["admin"],
    "user_permissions": ["trade", "view_portfolio"]
  },
  "request_id": "req_1695587400_ghi789",
  "timestamp": "2025-09-24T20:50:00Z"
}
```

#### 429 Rate Limit Exceeded
```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Too many authentication attempts",
  "details": {
    "rate_limit": "50 requests per minute",
    "retry_after": 60,
    "reset_time": "2025-09-24T21:00:00Z"
  },
  "request_id": "req_1695587400_jkl012",
  "timestamp": "2025-09-24T20:50:00Z"
}
```

## 📖 Examples

### Complete Authentication Flow

```typescript
// 1. Login with Telegram
const loginResponse = await fetch('/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    telegram_id: 123456789,
    username: 'trader_user',
    signature: 'telegram_auth_signature'
  })
});

const auth = await loginResponse.json();
console.log('Access token:', auth.access_token);

// 2. Use token for authenticated requests
const apiResponse = await fetch('/api/v1/users/profile', {
  headers: {
    'Authorization': `Bearer ${auth.access_token}`
  }
});

// 3. Create API key for external integrations
const apiKeyResponse = await fetch('/api/v1/auth/api-keys', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${auth.access_token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'Trading Bot',
    permissions: ['trade', 'view_portfolio']
  })
});

const apiKey = await apiKeyResponse.json();
console.log('API Key:', apiKey.api_key);

// 4. Use API key for programmatic access
const tradingResponse = await fetch('/api/v1/orders', {
  headers: {
    'Authorization': `ApiKey ${apiKey.api_key}`,
    'X-API-Secret': apiKey.api_secret,
    'X-API-Timestamp': Date.now().toString(),
    'X-API-Signature': calculateSignature(/* ... */)
  }
});
```

### Python Example

```python
import requests
import hashlib
import hmac
import time

class AuthClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.access_token = None
        
    def login(self, telegram_id, signature):
        response = requests.post(f"{self.base_url}/auth/login", json={
            "telegram_id": telegram_id,
            "username": "trader_user",
            "signature": signature
        })
        auth_data = response.json()
        self.access_token = auth_data['access_token']
        return auth_data
        
    def create_api_key(self, name, permissions):
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.post(f"{self.base_url}/auth/api-keys", 
                               headers=headers,
                               json={"name": name, "permissions": permissions})
        return response.json()
```

## 🔄 Integration Notes

### Authorization Headers
Use one of the following authentication methods:

**JWT Token (for user sessions):**
```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**API Key (for programmatic access):**
```bash
Authorization: ApiKey pak_live_abc123def456...
X-API-Secret: sak_abc123def456...
X-API-Timestamp: 1695587400
X-API-Signature: calculated_hmac_signature
```

### Rate Limiting
- Authentication endpoints: 50 requests/minute per IP
- API key creation: 10 requests/hour per user
- Session management: 100 requests/minute per user

### Security Considerations
- JWT tokens expire after 1 hour
- Refresh tokens expire after 30 days
- API keys can be configured with custom expiration
- IP whitelisting supported for API keys
- All authentication events are logged for audit

### WebSocket Authentication
For WebSocket connections, include JWT token as query parameter:
```javascript
const ws = new WebSocket(`wss://api.patriot-trading.com/ws/v1?token=${access_token}`);
```

---

> **📚 Documentation Navigation:**  
> [← Back to API Overview](../ANNEX-E-API-OVERVIEW.md) | [All Service APIs](./) | [Component Specs](../../03-COMPONENT-SPECIFICATIONS.md)
