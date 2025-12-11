# Enterprise Security - Quick Start Guide

**⚡ Get up and running in 5 minutes**

---

## Prerequisites

- Python 3.11+
- PostgreSQL (Supabase)
- Redis 7+
- Node.js 18+ (frontend)

---

## 1. Clone & Install

```bash
# Backend dependencies
cd backend
pip install -r requirements.txt

# Frontend dependencies (if needed)
cd ../frontend
npm install
```

---

## 2. Setup Redis

### Option A: Docker (Recommended)

```bash
docker run -d \
  --name redis-clonememoria \
  -p 6379:6379 \
  redis:7-alpine \
  redis-server --appendonly yes
```

### Option B: Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  redis_data:
```

```bash
docker-compose up -d redis
```

### Option C: Local Install (Linux)

```bash
sudo apt-get install redis-server
sudo systemctl start redis
redis-cli ping  # Should return PONG
```

---

## 3. Configure Environment

```bash
# Copy example
cp .env.example .env

# Edit .env
nano .env
```

### Required Variables

```bash
# JWT Enterprise
SECRET_KEY=<run: python -c "import secrets; print(secrets.token_urlsafe(64))">
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Redis
REDIS_URL=redis://localhost:6379/0

# Supabase (already configured)
SUPABASE_URL=https://gniuyicdmjmzbgwbnvmk.supabase.co
SUPABASE_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>

# Security
ALLOWED_HOSTS=localhost,127.0.0.1
FRONTEND_URL=http://localhost:3000
```

### Generate SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Copy output to `.env` as `SECRET_KEY`.

---

## 4. Apply Database Migration

Migration already applied: `20251211040000_phase6_enterprise_security.sql`

Verify in Supabase dashboard:
1. Go to Database > Migrations
2. Check for Phase 6 migration
3. Verify tables exist: `roles`, `refresh_tokens`, `token_blacklist`, `rate_limits`

---

## 5. Start Backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output**:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 6. Test Setup

### A. Health Check

```bash
curl http://localhost:8000/api/health
```

**Expected**: `{"status":"healthy"}`

### B. Redis Connection

```bash
redis-cli ping
```

**Expected**: `PONG`

### C. Register User (JWT Enterprise)

```bash
curl -X POST http://localhost:8000/api/auth-v2/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!@#",
    "full_name": "Test User"
  }'
```

**Expected**:
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "uuid",
    "email": "test@example.com",
    "full_name": "Test User"
  }
}
```

### D. Test Rate Limiting

```bash
# Extract token from register response
TOKEN="<your-access-token>"

# Send 60 requests (pro plan limit is 50/min)
for i in {1..60}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    http://localhost:8000/api/clones \
    -H "Authorization: Bearer $TOKEN"
done
```

**Expected**: First 50 return `200`, then `429` (Too Many Requests)

---

## 7. API Documentation

Open in browser:
```
http://localhost:8000/docs
```

Look for new endpoints under "auth-enterprise" tag:
- POST `/api/auth-v2/register`
- POST `/api/auth-v2/login`
- POST `/api/auth-v2/refresh`
- POST `/api/auth-v2/logout`
- GET `/api/auth-v2/sessions`
- POST `/api/auth-v2/logout-all`
- GET `/api/auth-v2/me`

---

## 8. Frontend Integration (Optional)

Update your frontend API client:

```typescript
// apiClient.ts
const API_BASE = 'http://localhost:8000/api';

export async function login(email: string, password: string) {
  const response = await fetch(`${API_BASE}/auth-v2/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include', // Important for cookies!
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) throw new Error('Login failed');

  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);

  return data;
}

export async function refreshToken() {
  const refresh_token = localStorage.getItem('refresh_token');

  const response = await fetch(`${API_BASE}/auth-v2/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ refresh_token }),
  });

  if (!response.ok) {
    // Refresh failed, logout user
    localStorage.clear();
    window.location.href = '/login';
    throw new Error('Session expired');
  }

  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);

  return data;
}

export async function apiRequest(endpoint: string, options: RequestInit = {}) {
  const token = localStorage.getItem('access_token');

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`,
    },
    credentials: 'include',
  });

  if (response.status === 401) {
    // Token expired, try refresh
    try {
      await refreshToken();
      // Retry request with new token
      const newToken = localStorage.getItem('access_token');
      return fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: {
          ...options.headers,
          'Authorization': `Bearer ${newToken}`,
        },
        credentials: 'include',
      });
    } catch {
      // Refresh failed
      throw new Error('Session expired');
    }
  }

  return response;
}
```

---

## 9. RBAC Integration (Optional)

Protect your routes with RBAC:

```python
from fastapi import APIRouter, Depends
from uuid import UUID
from backend.api.rbac_middleware import require_admin, require_editor

router = APIRouter()

@router.get("/clones/{id}")
async def get_clone(
    id: UUID,
    space_id: UUID,  # Required query param
    current_user: dict = Depends(require_viewer)
):
    """Requires viewer role or higher"""
    # Your code here
    pass

@router.delete("/clones/{id}")
async def delete_clone(
    id: UUID,
    space_id: UUID,
    current_user: dict = Depends(require_admin)
):
    """Requires admin role or higher"""
    # Your code here
    pass
```

**Call from frontend**:
```typescript
// GET requires viewer+
await apiRequest('/clones/123?space_id=456');

// DELETE requires admin+
await apiRequest('/clones/123?space_id=456', { method: 'DELETE' });
```

---

## 10. Monitoring (Optional)

### View Redis Keys

```bash
redis-cli keys "ratelimit:*"
```

### Check Rate Limit Status

```sql
-- Supabase SQL Editor
SELECT * FROM rate_limit_configs WHERE plan = 'pro';
```

### View Audit Log

```sql
SELECT * FROM audit_log
WHERE event LIKE 'user_%'
ORDER BY created_at DESC
LIMIT 10;
```

### View Active Sessions

```sql
SELECT
  rt.id,
  rt.user_id,
  u.email,
  rt.created_at,
  rt.ip_address,
  rt.device_info->>'user_agent' as user_agent
FROM refresh_tokens rt
JOIN users u ON u.id = rt.user_id
WHERE rt.revoked_at IS NULL
ORDER BY rt.created_at DESC;
```

---

## Common Issues & Solutions

### ❌ "Redis connection failed"

**Problem**: Redis not running

**Solution**:
```bash
docker ps | grep redis
docker start redis-clonememoria
redis-cli ping
```

---

### ❌ "Invalid refresh token"

**Problem**: Token expired or revoked

**Solution**:
1. Login again to get new tokens
2. Check token in database:
```sql
SELECT * FROM refresh_tokens WHERE user_id = 'xxx';
```

---

### ❌ "Rate limit not working"

**Problem**: Redis not configured or REDIS_URL wrong

**Solution**:
1. Check .env has `REDIS_URL=redis://localhost:6379/0`
2. Test Redis: `redis-cli ping`
3. Check logs: `tail -f logs/app.log | grep RATE_LIMIT`

---

### ❌ "403 Forbidden" on RBAC-protected route

**Problem**: Missing space_id or insufficient role

**Solution**:
1. Add `space_id` query param: `/api/resource?space_id={uuid}`
2. Check user's role:
```sql
SELECT sm.*, r.name as role_name
FROM space_members sm
JOIN roles r ON r.id = sm.role_id
WHERE sm.user_id = 'xxx' AND sm.space_id = 'yyy';
```

---

## Next Steps

1. **Read Full Documentation**
   - `ENTERPRISE_SECURITY_GUIDE.md` - Complete API reference
   - `DEVOPS_DELIVERY_SUMMARY.md` - Deployment guide
   - `RBAC_INTEGRATION_EXAMPLE.py` - Code examples

2. **Configure Production**
   - Generate strong SECRET_KEY
   - Setup production Redis (Redis Cloud, AWS ElastiCache)
   - Update CORS origins
   - Enable secure cookies (`secure=True`)

3. **Add Monitoring**
   - Setup alerts for rate limit violations
   - Monitor Redis memory usage
   - Track failed login attempts
   - Review audit logs regularly

4. **Test Security**
   - Pen test rate limiting
   - Test token revocation
   - Verify RBAC permissions
   - Test session management

---

## Quick Commands Reference

```bash
# Start Redis
docker start redis-clonememoria

# Start backend
cd backend && uvicorn main:app --reload

# Start frontend
cd frontend && npm run dev

# Test health
curl http://localhost:8000/api/health

# Test Redis
redis-cli ping

# View Redis keys
redis-cli keys "*"

# Clear rate limits
redis-cli keys "ratelimit:*" | xargs redis-cli del

# View logs
tail -f logs/app.log
```

---

**🎉 Setup Complete!**

Your CloneMemoria backend now has:
- ✅ JWT Enterprise (refresh tokens, rotation)
- ✅ RBAC (5-level permissions)
- ✅ Redis Rate Limiting (per-user, per-endpoint)
- ✅ HTTPOnly Cookies (XSS protection)
- ✅ Complete Audit Trail

**Ready for production deployment.**

For help, see: `ENTERPRISE_SECURITY_GUIDE.md`
