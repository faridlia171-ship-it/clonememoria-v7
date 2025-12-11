# Enterprise Security Implementation Guide

**Version**: 1.0
**Date**: December 11, 2025
**Status**: Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [JWT Enterprise System](#jwt-enterprise-system)
3. [RBAC (Role-Based Access Control)](#rbac)
4. [Rate Limiting with Redis](#rate-limiting)
5. [Integration Guide](#integration-guide)
6. [API Reference](#api-reference)
7. [Configuration](#configuration)
8. [Testing](#testing)
9. [Deployment](#deployment)
10. [Troubleshooting](#troubleshooting)

---

## Overview

CloneMemoria implements three core enterprise security features:

### 1. JWT Enterprise
- **Access Token**: Short-lived (30 min), for API authentication
- **Refresh Token**: Long-lived (30 days), for token rotation
- **Token Rotation**: Automatic on refresh, old tokens revoked
- **Blacklist**: Revoked tokens stored in database
- **HTTPOnly Cookies**: Secure token storage in browser
- **Session Tracking**: Device info, IP, user agent logged

### 2. RBAC
- **5 Hierarchical Roles**: system, owner, admin, editor, viewer
- **Workspace-Scoped**: Permissions per workspace
- **Database-Level**: Enforced in PostgreSQL with RLS
- **Middleware**: FastAPI dependency injection
- **Audit Trail**: All permission checks logged

### 3. Rate Limiting (Redis)
- **Multi-Window**: Per minute, hour, day
- **Per-User**: Individual limits based on billing plan
- **Per-Endpoint**: Different limits for different API routes
- **Graceful Degradation**: Falls back if Redis unavailable
- **Real-Time Tracking**: Sub-second latency

---

## JWT Enterprise System

### Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ 1. POST /auth-v2/login
       │    {email, password}
       ▼
┌─────────────────────────────┐
│     FastAPI Backend         │
│  ┌─────────────────────┐   │
│  │ auth_enterprise.py  │   │
│  └──────┬──────────────┘   │
│         │                   │
│  ┌──────▼──────────────┐   │
│  │  TokenService       │   │
│  │  - create_token_pair│   │
│  │  - refresh_token    │   │
│  │  - revoke_token     │   │
│  └──────┬──────────────┘   │
│         │                   │
│  ┌──────▼──────────────┐   │
│  │   Supabase DB       │   │
│  │  - refresh_tokens   │   │
│  │  - token_blacklist  │   │
│  │  - audit_log        │   │
│  └─────────────────────┘   │
└─────────────────────────────┘
       │ 2. Response
       │    {access_token, refresh_token}
       │    + HTTPOnly cookies
       ▼
┌─────────────┐
│   Client    │
│ (stores in  │
│  cookies)   │
└─────────────┘
```

### Token Lifecycle

```
1. LOGIN
   └─> POST /auth-v2/login
       └─> Create access + refresh tokens
           └─> Store refresh token in DB
               └─> Set HTTPOnly cookies
                   └─> Return tokens to client

2. API REQUEST (Access Token Valid)
   └─> GET /api/resource
       └─> Header: Authorization: Bearer {access_token}
           └─> Decode & validate token
               └─> Allow request

3. API REQUEST (Access Token Expired)
   └─> POST /auth-v2/refresh
       └─> Body: {refresh_token}
           └─> Validate refresh token from DB
               └─> Revoke old refresh token
                   └─> Create new token pair
                       └─> Return new tokens

4. LOGOUT
   └─> POST /auth-v2/logout
       └─> Revoke all user refresh tokens
           └─> Add to blacklist
               └─> Clear HTTPOnly cookies
                   └─> Return success
```

### API Endpoints

#### POST `/api/auth-v2/register`
Register new user with JWT enterprise

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecureP@ss123",
  "full_name": "John Doe"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "billing_plan": "free"
  }
}
```

**Cookies Set**:
- `access_token` (HTTPOnly, Max-Age: 1800s)
- `refresh_token` (HTTPOnly, Secure, SameSite: strict, Max-Age: 2592000s)

---

#### POST `/api/auth-v2/login`
Login with JWT enterprise

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecureP@ss123"
}
```

**Response**: Same as register

---

#### POST `/api/auth-v2/refresh`
Refresh access token using refresh token

**Request**:
```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response**:
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Notes**:
- Old refresh token is automatically revoked
- New refresh token issued (rotation)
- New cookies set

---

#### POST `/api/auth-v2/logout`
Logout and revoke all tokens

**Headers**:
```
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "message": "Logged out successfully",
  "tokens_revoked": 3
}
```

**Notes**:
- Revokes ALL refresh tokens for user
- Clears HTTPOnly cookies
- Logs audit event

---

#### POST `/api/auth-v2/revoke`
Revoke a specific refresh token

**Headers**:
```
Authorization: Bearer {access_token}
```

**Request**:
```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Response**:
```json
{
  "message": "Token revoked successfully"
}
```

---

#### GET `/api/auth-v2/sessions`
List all active sessions

**Headers**:
```
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "sessions": [
    {
      "id": "uuid",
      "created_at": "2025-12-11T10:00:00Z",
      "device_info": {
        "user_agent": "Mozilla/5.0...",
        "origin": "http://localhost:3000"
      },
      "ip_address": "192.168.1.1"
    }
  ],
  "total": 1
}
```

---

#### POST `/api/auth-v2/logout-all`
Logout from all devices/sessions

**Headers**:
```
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "message": "All sessions logged out successfully",
  "tokens_revoked": 5
}
```

---

#### GET `/api/auth-v2/me`
Get current user info

**Headers**:
```
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "billing_plan": "pro",
  "created_at": "2025-01-01T00:00:00Z"
}
```

---

### Client Integration

#### JavaScript/TypeScript

```typescript
// Login
const response = await fetch('http://localhost:8000/api/auth-v2/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  credentials: 'include', // Important for cookies
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123',
  }),
});

const { access_token, refresh_token, user } = await response.json();

// Store tokens (optional, already in cookies)
localStorage.setItem('access_token', access_token);
localStorage.setItem('refresh_token', refresh_token);

// API Request
const apiResponse = await fetch('http://localhost:8000/api/clones', {
  headers: {
    'Authorization': `Bearer ${access_token}`,
  },
  credentials: 'include',
});

// Handle 401 (token expired) -> Refresh
if (apiResponse.status === 401) {
  const refreshResponse = await fetch('http://localhost:8000/api/auth-v2/refresh', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({
      refresh_token: localStorage.getItem('refresh_token'),
    }),
  });

  const { access_token: newToken } = await refreshResponse.json();
  localStorage.setItem('access_token', newToken);

  // Retry original request
  const retryResponse = await fetch('http://localhost:8000/api/clones', {
    headers: {
      'Authorization': `Bearer ${newToken}`,
    },
    credentials: 'include',
  });
}

// Logout
await fetch('http://localhost:8000/api/auth-v2/logout', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access_token}`,
  },
  credentials: 'include',
});

localStorage.removeItem('access_token');
localStorage.removeItem('refresh_token');
```

---

## RBAC

### Role Hierarchy

| Role | Level | Permissions |
|------|-------|-------------|
| **system** | 100 | Platform admin, full access |
| **owner** | 90 | Workspace owner, delete workspace, manage all |
| **admin** | 80 | Manage members, settings, delete resources |
| **editor** | 70 | Create, update content, upload documents |
| **viewer** | 60 | Read-only access |

Higher level ≥ lower level permissions (e.g., admin can do everything editor/viewer can)

### Database Schema

```sql
-- roles table
CREATE TABLE roles (
  id uuid PRIMARY KEY,
  name text UNIQUE, -- system, owner, admin, editor, viewer
  description text,
  permissions jsonb,
  hierarchy_level integer,
  created_at timestamptz
);

-- space_members table (extended)
CREATE TABLE space_members (
  id uuid PRIMARY KEY,
  space_id uuid REFERENCES spaces(id),
  user_id uuid REFERENCES users(id),
  role text, -- legacy
  role_id uuid REFERENCES roles(id), -- new
  created_at timestamptz
);
```

### Middleware Usage

```python
from fastapi import APIRouter, Depends
from uuid import UUID
from backend.api.rbac_middleware import (
    require_viewer,
    require_editor,
    require_admin,
    require_owner,
    require_platform_admin
)

router = APIRouter()

@router.get("/clones/{id}")
async def get_clone(
    id: UUID,
    space_id: UUID,  # Required query parameter
    current_user: dict = Depends(require_viewer)
):
    """Requires viewer role or higher"""
    pass

@router.post("/clones")
async def create_clone(
    space_id: UUID,
    current_user: dict = Depends(require_editor)
):
    """Requires editor role or higher"""
    pass

@router.delete("/clones/{id}")
async def delete_clone(
    id: UUID,
    space_id: UUID,
    current_user: dict = Depends(require_admin)
):
    """Requires admin role or higher"""
    pass

@router.delete("/workspaces/{id}")
async def delete_workspace(
    id: UUID,
    current_user: dict = Depends(require_owner)
):
    """Requires owner role (workspace deletion)"""
    pass

@router.get("/admin/users")
async def list_users(
    current_user: dict = Depends(require_platform_admin)
):
    """Platform admin only (no workspace context)"""
    pass
```

### RBAC Service API

```python
from backend.services.rbac_service import RBACService
from backend.db.client import get_db

db = get_db()
rbac_service = RBACService(db)

# Check permission
result = rbac_service.check_permission(
    user_id=user_id,
    space_id=space_id,
    required_role="admin"
)

if result.allowed:
    print(f"User has {result.user_role} role")
else:
    print(f"Access denied: {result.reason}")

# Get user's role in workspace
role = rbac_service.get_user_role_in_workspace(
    user_id=user_id,
    space_id=space_id
)
print(f"User role: {role}")  # "admin", "editor", etc.

# Check if user is workspace owner
is_owner = rbac_service.is_workspace_owner(
    user_id=user_id,
    space_id=space_id
)

# Check if user is platform admin
is_admin = rbac_service.is_platform_admin(user_id=user_id)

# Get all roles
roles = rbac_service.get_all_roles()
for role in roles:
    print(f"{role['name']}: level {role['hierarchy_level']}")
```

---

## Rate Limiting

### Architecture

```
Client Request
    │
    ▼
┌──────────────────────────────────┐
│  RedisRateLimitMiddleware        │
│  1. Extract user_id              │
│  2. Normalize endpoint           │
│  3. Check Redis counters         │
│  4. Allow/Deny                   │
└──────────┬───────────────────────┘
           │
           ▼
    ┌──────────────┐
    │    Redis     │
    │ Key: ratelimit:minute:{user_id}:{endpoint} │
    │ Value: 45 (request count)                  │
    │ TTL: 60 seconds                            │
    └──────────────┘
```

### Configuration

Rate limits stored in `rate_limit_configs` table:

```sql
SELECT * FROM rate_limit_configs WHERE plan = 'pro';

| plan | endpoint_pattern | requests_per_minute | requests_per_hour | requests_per_day |
|------|-----------------|---------------------|-------------------|------------------|
| pro  | /api/chat/*     | 50                  | 500               | 5000             |
| pro  | /api/clones/*   | 100                 | 1000              | 10000            |
| pro  | /api/documents/*| 20                  | 200               | 2000             |
| pro  | /api/*          | 150                 | 1500              | 15000            |
```

### Redis Keys

```
ratelimit:minute:{user_id}:{endpoint}
ratelimit:hour:{user_id}:{endpoint}
ratelimit:day:{user_id}:{endpoint}
```

Example:
```
ratelimit:minute:550e8400-e29b-41d4-a716-446655440000:/api/chat/*
```

### Response Headers

When rate limited:
```
HTTP/1.1 429 Too Many Requests

X-RateLimit-Limit-Minute: 50
X-RateLimit-Limit-Hour: 500
X-RateLimit-Limit-Day: 5000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 2025-12-11T10:35:00Z

{
  "message": "Rate limit exceeded",
  "window": "minute",
  "current_count": 51,
  "limit_per_minute": 50,
  "limit_per_hour": 500,
  "limit_per_day": 5000,
  "reset_at": "2025-12-11T10:35:00Z"
}
```

### Bypass Routes

These routes are NOT rate limited:
- `/api/health`
- `/api/auth/login`
- `/api/auth/register`

### Service API

```python
from backend.services.redis_rate_limit_service import RedisRateLimitService

rate_limit_service = RedisRateLimitService()

# Check rate limit
result = rate_limit_service.check_rate_limit(
    user_id=user_id,
    endpoint="/api/chat/*"
)

if result["allowed"]:
    print(f"Allowed: {result['current_count']}/{result['limit_per_minute']}")
else:
    print(f"Rate limited! Window: {result['window']}")
    print(f"Reset at: {result['reset_at']}")

# Increment counter
rate_limit_service.increment_rate_limit(
    user_id=user_id,
    endpoint="/api/chat/*"
)

# Get status
status = rate_limit_service.get_user_rate_limit_status(
    user_id=user_id,
    endpoint_pattern="/api/*"
)
print(f"Current usage:")
print(f"  Minute: {status['current']['minute']}/{status['limits']['per_minute']}")
print(f"  Hour: {status['current']['hour']}/{status['limits']['per_hour']}")
print(f"  Day: {status['current']['day']}/{status['limits']['per_day']}")

# Reset user's limits (admin only)
deleted = rate_limit_service.reset_user_rate_limits(user_id=user_id)
print(f"Reset {deleted} rate limit keys")

# Health check
health = rate_limit_service.health_check()
print(f"Redis status: {health['status']}")
if health['status'] == 'healthy':
    print(f"Connected clients: {health['connected_clients']}")
    print(f"Ops/sec: {health['instantaneous_ops_per_sec']}")
```

---

## Configuration

### Environment Variables

Add to `.env`:

```bash
# JWT Configuration
SECRET_KEY=your-super-secret-key-min-64-chars-recommended
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Security
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
FRONTEND_URL=http://localhost:3000

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### Redis Setup

#### Docker (Development)

```bash
docker run --name redis-clonememoria \
  -p 6379:6379 \
  -d redis:7-alpine \
  redis-server --appendonly yes
```

#### Docker Compose

```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    container_name: redis-clonememoria
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

volumes:
  redis_data:
```

#### Production (Cloud)

**Redis Cloud**:
```bash
REDIS_URL=redis://default:password@redis-12345.cloud.redislabs.com:12345
```

**AWS ElastiCache**:
```bash
REDIS_URL=redis://master.your-cluster.cache.amazonaws.com:6379
```

**Azure Cache for Redis**:
```bash
REDIS_URL=redis://your-cache.redis.cache.windows.net:6380?ssl=True
```

---

## Testing

### JWT Tests

```bash
# Register
curl -X POST http://localhost:8000/api/auth-v2/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!@#",
    "full_name": "Test User"
  }' \
  -c cookies.txt

# Login
curl -X POST http://localhost:8000/api/auth-v2/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!@#"
  }' \
  -c cookies.txt

# Extract tokens
ACCESS_TOKEN=$(cat cookies.txt | grep access_token | awk '{print $7}')
REFRESH_TOKEN=$(cat cookies.txt | grep refresh_token | awk '{print $7}')

# API Request
curl -X GET http://localhost:8000/api/clones \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Refresh Token
curl -X POST http://localhost:8000/api/auth-v2/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}"

# Get Sessions
curl -X GET http://localhost:8000/api/auth-v2/sessions \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Logout
curl -X POST http://localhost:8000/api/auth-v2/logout \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### RBAC Tests

```bash
# As viewer (should succeed)
curl -X GET "http://localhost:8000/api/clones/123?space_id=456" \
  -H "Authorization: Bearer $VIEWER_TOKEN"

# As viewer trying to delete (should fail with 403)
curl -X DELETE "http://localhost:8000/api/clones/123?space_id=456" \
  -H "Authorization: Bearer $VIEWER_TOKEN"

# As admin (should succeed)
curl -X DELETE "http://localhost:8000/api/clones/123?space_id=456" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Rate Limit Tests

```bash
# Trigger rate limit (send 60 requests)
for i in {1..60}; do
  curl -X GET http://localhost:8000/api/clones \
    -H "Authorization: Bearer $TOKEN" \
    -w "\n%{http_code}\n"
done

# Expected after limit (50 for pro):
# HTTP 429 Too Many Requests
```

### Redis Tests

```bash
# Check Redis connection
redis-cli ping
# PONG

# View rate limit keys
redis-cli keys "ratelimit:*"

# Get specific key value
redis-cli get "ratelimit:minute:user-id:/api/clones/*"

# Get key TTL
redis-cli ttl "ratelimit:minute:user-id:/api/clones/*"

# Clear all rate limits
redis-cli keys "ratelimit:*" | xargs redis-cli del
```

---

## Deployment

### Pre-Deployment Checklist

- [ ] Generate secure `SECRET_KEY` (64+ characters)
- [ ] Configure production Redis URL
- [ ] Update `ALLOWED_ORIGINS` in CORS
- [ ] Update `TRUSTED_HOSTS`
- [ ] Set `FRONTEND_URL` to production domain
- [ ] Enable HTTPS (set `secure=True` in cookies)
- [ ] Configure CSP `connect-src` with production domains
- [ ] Setup Redis backup/persistence
- [ ] Configure Redis maxmemory-policy
- [ ] Test token refresh flow
- [ ] Test RBAC permissions
- [ ] Load test rate limiting

### Production Settings

**main.py**:
```python
# Enable secure cookies in production
secure = settings.ENVIRONMENT == "production"

set_auth_cookies(response, token_pair, secure=secure)
```

**Redis Configuration**:
```bash
# maxmemory policy (evict old rate limits first)
redis-cli config set maxmemory-policy allkeys-lru
redis-cli config set maxmemory 256mb

# Persistence
redis-cli config set appendonly yes
redis-cli config set save "900 1 300 10 60 10000"
```

### Monitoring

**Metrics to Track**:
1. Token refresh rate (per minute)
2. Token revocation rate
3. Active sessions count
4. Rate limit hit rate
5. Redis memory usage
6. Redis ops/sec
7. RBAC denial rate
8. Failed login attempts

**Alerts**:
- Rate limit hit rate > 10%
- Failed login attempts > 5 in 10 min
- Token revocation spike (> 100/min)
- Redis memory > 80%
- Redis connection failures

---

## Troubleshooting

### JWT Issues

**Problem**: "Invalid refresh token"
```
Solution:
1. Check token hasn't been revoked (token_blacklist table)
2. Verify token hasn't expired
3. Ensure refresh token type is 'refresh' not 'access'
4. Check SECRET_KEY matches between creation and verification
```

**Problem**: "Token decode error"
```
Solution:
1. Verify token format (should be JWT: xxx.yyy.zzz)
2. Check SECRET_KEY and ALGORITHM in .env
3. Ensure token wasn't tampered with
4. Try generating new token pair
```

### RBAC Issues

**Problem**: "403 Forbidden" on allowed action
```
Solution:
1. Check user's role: SELECT * FROM space_members WHERE user_id = 'xxx'
2. Verify space_id in query parameter
3. Check role hierarchy level
4. Look at audit_log for denial reason
```

**Problem**: "space_id required"
```
Solution:
Add space_id as query parameter: /api/resource?space_id={uuid}
```

### Rate Limiting Issues

**Problem**: Rate limiting not working
```
Solution:
1. Check Redis connection: redis-cli ping
2. Verify REDIS_URL in .env
3. Check middleware is enabled in main.py
4. Look for "rate_limiting_disabled" in logs
```

**Problem**: All requests get 429
```
Solution:
1. Check Redis keys: redis-cli keys "ratelimit:*"
2. Clear limits: redis-cli flushdb
3. Verify rate_limit_configs in database
4. Check user's billing_plan
```

### Redis Issues

**Problem**: "Redis connection failed"
```
Solution:
1. Verify Redis is running: redis-cli ping
2. Check REDIS_URL format: redis://host:port/db
3. Check firewall/network connectivity
4. Verify Redis auth if using password
```

**Problem**: "Redis out of memory"
```
Solution:
1. Set maxmemory: redis-cli config set maxmemory 512mb
2. Set eviction: redis-cli config set maxmemory-policy allkeys-lru
3. Clear old data: redis-cli keys "ratelimit:*" | xargs redis-cli del
```

---

## Support

For issues, questions, or contributions:
- **Documentation**: `/ENTERPRISE_SECURITY_GUIDE.md`
- **Examples**: `/backend/RBAC_INTEGRATION_EXAMPLE.py`
- **Database**: Check `audit_log` table for security events
- **Logs**: Check application logs for detailed error messages

---

**Enterprise Security Status**: ✅ Production Ready
**Last Updated**: December 11, 2025
