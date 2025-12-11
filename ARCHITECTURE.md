# CloneMemoria - Architecture Documentation

## System Overview

CloneMemoria is a full-stack application that enables users to create AI-powered conversational clones of real people. The system is designed with a clean separation between backend (FastAPI) and frontend (Next.js), communicating via RESTful APIs.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                            │
│                  (Next.js 15 + React)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │    Pages     │  │  Components  │  │   Contexts   │    │
│  │ (App Router) │  │    (UI)      │  │    (State)   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│           │                │                  │            │
│           └────────────────┴──────────────────┘            │
│                          │                                  │
│                     API Client                              │
│                     (HTTP + Logging)                        │
└─────────────────────────────────────────────────────────────┘
                             │
                        REST API (JWT)
                             │
┌─────────────────────────────────────────────────────────────┐
│                         Backend                             │
│                    (FastAPI + Python)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  API Routes  │  │  Middleware  │  │  Auth/Deps   │    │
│  │  (Endpoints) │  │  (Logging)   │  │   (JWT)      │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│           │                                  │              │
│           ├──────────────────────────────────┤              │
│           │                                  │              │
│  ┌──────────────┐              ┌──────────────────┐        │
│  │  AI Layer    │              │   Database       │        │
│  │ (Providers)  │              │   Client         │        │
│  └──────────────┘              └──────────────────┘        │
│           │                              │                  │
└───────────┼──────────────────────────────┼──────────────────┘
            │                              │
     External LLM API              Supabase PostgreSQL
  (OpenAI/Compatible)              (with RLS enabled)
```

## Backend Architecture

### Layer Structure

1. **API Layer** (`/api`)
   - REST endpoints organized by resource
   - Request/response validation via Pydantic schemas
   - Middleware for logging and error handling
   - Dependency injection for authentication

2. **Core Layer** (`/core`)
   - Configuration management (environment variables)
   - Security utilities (JWT, password hashing)
   - Logging configuration (structured JSON)

3. **Database Layer** (`/db`)
   - Supabase client singleton
   - Row-level security enforcement
   - Transaction management

4. **AI Layer** (`/ai`)
   - Provider abstraction interface
   - Multiple provider implementations
   - Prompt engineering and context management

5. **Schema Layer** (`/schemas`)
   - Pydantic models for validation
   - Type definitions for API contracts

### Request Flow

```
1. HTTP Request → FastAPI App
2. Middleware (logging, request ID generation)
3. Route Handler
4. Authentication Dependency (JWT validation)
5. Authorization Dependency (ownership verification)
6. Business Logic
7. Database Operations (via Supabase client)
8. AI Operations (if needed)
9. Response Serialization
10. Logging + Return
```

### Authentication Flow

```
Registration:
1. User submits email + password
2. Password hashed with bcrypt
3. User record created in database
4. JWT token generated with user_id
5. Token + user info returned

Login:
1. User submits email + password
2. User fetched from database
3. Password verified against hash
4. JWT token generated
5. Token + user info returned

Protected Endpoints:
1. JWT token extracted from Authorization header
2. Token decoded and validated
3. User ID extracted from token payload
4. User ID available for request handling
```

### AI Provider Architecture

**Interface:**
```python
class LLMProvider(ABC):
    async def generate_clone_reply(
        clone_info: dict,
        memories: list,
        conversation_history: list,
        user_message: str,
        tone_config: dict
    ) -> str
```

**Implementations:**
- `DummyProvider`: Returns templated responses for testing
- `ExternalProvider`: Calls OpenAI-compatible APIs

**Prompt Construction:**
1. System prompt with clone description and personality
2. Selected memories (most relevant)
3. Recent conversation history (last 10 messages)
4. User's current message
5. Tone configuration applied

## Frontend Architecture

### Component Hierarchy

```
RootLayout (AuthProvider)
├── Page (redirect logic)
├── LoginPage
├── RegisterPage
└── AppLayout (authenticated)
    ├── DashboardPage
    │   ├── CloneCard (list)
    │   └── CloneForm (create)
    └── CloneDetailPage
        ├── MemoriesPage
        │   ├── MemoryList
        │   └── MemoryForm
        └── ChatPage
            └── ChatWindow
                └── MessageBubble (list)
```

### State Management

**Global State (Context):**
- `AuthContext`: User authentication, login/logout, loading state

**Local State (useState):**
- Component-specific data (forms, lists, UI state)
- API loading states
- Error messages

**Server State:**
- Fetched from backend via API client
- No client-side caching (fetch on mount)
- Optimistic updates where appropriate

### Data Flow

```
User Action
    ↓
Event Handler
    ↓
API Client (with logging)
    ↓
HTTP Request → Backend
    ↓
Response
    ↓
State Update
    ↓
React Re-render
```

## Database Schema Design

### Multi-Tenancy

All tables include `user_id` foreign keys and RLS policies ensure data isolation:

```sql
-- Example RLS policy
CREATE POLICY "Users can view own clones"
  ON clones FOR SELECT
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);
```

### Relationships

```
users (1) ──────── (n) clones
                        │
                        ├── (n) memories
                        └── (n) conversations
                                  │
                                  └── (n) messages
```

### Indexes

Strategic indexes on:
- Foreign keys (clone_id, user_id, conversation_id)
- Frequently queried columns (created_at)
- Improves query performance for lists and filters

## Security Architecture

### Authentication

- JWT tokens with expiration (7 days default)
- Tokens stored in localStorage (client-side)
- Bearer token authentication on protected endpoints
- Password hashing with bcrypt (10 rounds)

### Authorization

- Row-Level Security (RLS) on all tables
- User isolation enforced at database level
- Ownership verification in API dependencies
- No cross-user data access possible

### Data Protection

- Environment variables for secrets
- No sensitive data in logs
- CORS restricted to known origins
- Input validation on all endpoints

## Logging Architecture

### Backend Logging

**Format:** Structured JSON
```json
{
  "timestamp": "ISO8601",
  "level": "INFO|DEBUG|WARNING|ERROR",
  "logger_name": "module.path",
  "message": "EVENT_NAME",
  "request_id": "uuid",
  "file": "/path/to/file.py",
  "function": "function_name",
  "line": 123,
  ...custom_fields
}
```

**Log Events:**
- Module loading
- Request start/end with timing
- Authentication attempts
- Database operations
- AI provider calls with timing
- Error conditions with stack traces

### Frontend Logging

**Development:** Colored, grouped console output
**Production:** JSON format (optional remote logging)

**Events:**
- Component lifecycle
- User actions
- API calls with timing
- State changes
- Errors

## Scalability Considerations

### Current Limitations

- Single backend instance (no load balancing)
- No caching layer
- Sequential message processing
- In-memory request tracking

### Future Improvements

1. **Horizontal Scaling:**
   - Load balancer for multiple backend instances
   - Stateless design enables easy scaling
   - Session storage in Redis/database

2. **Caching:**
   - Redis for frequently accessed data
   - CDN for static frontend assets
   - API response caching

3. **Async Processing:**
   - Message queue for AI generation
   - Background jobs for memory processing
   - Webhook support for long-running operations

4. **Database Optimization:**
   - Read replicas for queries
   - Connection pooling
   - Query optimization and profiling

## Deployment Architecture

### Recommended Setup

```
Internet
    ↓
Load Balancer / Reverse Proxy (nginx)
    ↓
┌─────────────────┬─────────────────┐
│   Frontend      │    Backend      │
│   (Next.js)     │   (FastAPI)     │
│   Port 3000     │   Port 8000     │
└─────────────────┴─────────────────┘
         │                │
         └────────┬───────┘
                  ↓
          Supabase (managed)
                  │
                  ├── PostgreSQL
                  ├── Auth (optional)
                  └── Storage (future)
```

### Environment Separation

- **Development:** Local servers, dummy AI provider
- **Staging:** Production-like, test LLM API
- **Production:** Real LLM API, monitoring, backups

## Error Handling

### Backend

- HTTP status codes (400, 401, 404, 500)
- Consistent error response format
- Detailed logging of all errors
- Stack traces in development only

### Frontend

- User-friendly error messages
- Error boundary components
- Graceful degradation
- Retry logic for network errors

## Testing Strategy (Future)

### Backend
- Unit tests for business logic
- Integration tests for API endpoints
- Mock LLM provider for testing
- Database fixtures for test data

### Frontend
- Component unit tests (Jest + React Testing Library)
- Integration tests for user flows
- E2E tests with Playwright
- Visual regression tests

## Monitoring & Observability (Future)

### Metrics to Track
- API response times
- LLM call latency and success rate
- Database query performance
- User engagement metrics
- Error rates by endpoint

### Tools
- Application Performance Monitoring (APM)
- Log aggregation (ELK stack, DataDog)
- Uptime monitoring
- Alert system for critical errors

## Extension Points

### Adding New Features

1. **New API Endpoints:** Add routes in `backend/api/routes/`
2. **New UI Pages:** Add pages in `frontend/src/app/`
3. **New AI Providers:** Implement interface in `backend/ai/providers/`
4. **New Data Types:** Extend database schema and create migrations

### Plugin Architecture (Future)

- Memory importers (WhatsApp, Email, etc.)
- Custom AI behavior modules
- Third-party integrations
- Export/backup systems

---

## Phase 4: Multi-Tenant Platform Architecture

### Overview

Phase 4 transforms CloneMemoria into an enterprise-grade, multi-tenant SaaS platform with:
- Spaces (organizations/families) with role-based access
- Developer integration layer (API keys, webhooks)
- Content safety and comprehensive audit logging
- Platform administration tools

### Multi-Tenant Data Model

```
┌─────────────────────────────────────────────────────────────┐
│                    Multi-Tenant Structure                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  User (Personal)                                             │
│    └── Personal Clones (space_id = NULL, is_personal = true)│
│                                                              │
│  Space (Organization/Family)                                 │
│    ├── Owner (role = 'owner')                                │
│    ├── Admins (role = 'admin')                               │
│    ├── Members (role = 'member')                             │
│    └── Shared Clones (space_id = space.id, is_personal=false)│
│          ├── Memories (inherit space_id)                     │
│          ├── Documents (inherit space_id)                    │
│          └── Conversations (inherit space_id)                │
│                └── Messages (inherit space_id)               │
└─────────────────────────────────────────────────────────────┘
```

### Permission Model

**Space Roles:**

| Role | Create Clones | Manage Members | Delete Space | Manage Billing |
|------|--------------|----------------|--------------|----------------|
| Owner | ✅ | ✅ | ✅ | ✅ |
| Admin | ✅ | ✅ (except owner) | ❌ | ❌ |
| Member | ❌ | ❌ | ❌ | ❌ |

**Permission Helpers** (`backend/core/permissions.py`):
- `ensure_space_member()` - Verify user is in space
- `ensure_space_admin()` - Verify admin or owner role
- `ensure_space_owner()` - Verify owner role only
- `get_accessible_clone()` - Check clone access (personal or space-based)
- `ensure_platform_admin()` - Verify platform administrator

### Developer Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Developer Integration                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  API Keys                                                    │
│    ├── Scoped access (chat, read, write)                    │
│    ├── SHA-256 hashed storage                                │
│    ├── Per-user or per-space                                 │
│    └── Revocation support                                    │
│                                                              │
│  External API                                                │
│    ├── POST /api/external/chat                               │
│    │     └── Auth: X-API-Key header                          │
│    └── GET /api/external/clones                              │
│          └── Returns accessible clones                       │
│                                                              │
│  Webhooks                                                    │
│    ├── Event subscriptions                                   │
│    │     ├── clone.created                                   │
│    │     └── message.created                                 │
│    ├── HMAC-SHA256 signed payloads                           │
│    ├── Delivery tracking & logs                              │
│    └── Synchronous dispatch (Phase 4)                        │
└─────────────────────────────────────────────────────────────┘
```

### Content Safety Pipeline

```
User Input
    ↓
┌─────────────────────┐
│ Safety Check (Input)│
│ - Pattern matching  │
│ - Rule-based filter │
└─────────────────────┘
    ↓
  Safe? ─── No ──→ Log Safety Event → Block & Return Error
    │
   Yes
    ↓
┌─────────────────────┐
│ LLM Processing      │
│ - RAG retrieval     │
│ - Context building  │
│ - AI generation     │
└─────────────────────┘
    ↓
┌─────────────────────┐
│ Safety Wrap (Output)│
│ - Sanitize response │
│ - Check patterns    │
└─────────────────────┘
    ↓
  Safe? ─── No ──→ Log Safety Event → Replace with Safe Message
    │
   Yes
    ↓
Save to Database
    ↓
Trigger Webhooks
```

### Audit Logging Architecture

**Audit Events:**
- `login` - User authentication
- `gdpr.export` - Data export request
- `gdpr.delete` - Data deletion request
- `billing.plan.change` - Subscription changes
- `space.created` - New space created
- `api_key.created` - API key generated
- `webhook.created` - Webhook configured
- Content safety flags

**Audit Log Structure:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "space_id": "uuid (optional)",
  "event": "login",
  "resource_type": "user",
  "resource_id": "uuid",
  "metadata": {
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0..."
  },
  "created_at": "2025-12-09T10:30:00Z"
}
```

### Admin Console Architecture

```
Platform Admin User (is_platform_admin = true)
    │
    ├── GET /api/admin/users
    │     └── List all users with stats
    │
    ├── GET /api/admin/spaces
    │     └── List all spaces with metrics
    │
    ├── GET /api/admin/safety-events
    │     └── View content moderation logs
    │
    ├── GET /api/admin/audit-log
    │     └── View full audit trail
    │
    └── GET /api/admin/stats
          └── Platform-wide statistics
```

### Database Schema Extensions (Phase 4)

**New Tables (9):**
1. `spaces` - Organizations/families
2. `space_members` - Membership with roles
3. `space_invitations` - Email-based invitations
4. `api_keys` - Developer API keys
5. `webhooks` - Event subscriptions
6. `webhook_logs` - Delivery tracking
7. `safety_events` - Content moderation logs
8. `audit_log` - Compliance tracking
9. Helper functions (3): `is_space_member()`, `is_space_admin()`, `is_space_owner()`

**Extended Tables (7):**
- `users` → Added `is_platform_admin`
- `clones` → Added `space_id`, `is_personal`
- `memories` → Added `space_id`
- `conversations` → Added `space_id`
- `messages` → Added `space_id`
- `clone_documents` → Added `space_id`
- `clone_document_chunks` → Inherits space context

**RLS Policy Strategy:**
```sql
-- Personal data: user owns it
WHERE user_id = current_user_id

-- Space data: user is space member
WHERE space_id IN (
  SELECT space_id FROM space_members
  WHERE user_id = current_user_id
)

-- Admin data: user is platform admin
WHERE (SELECT is_platform_admin FROM users WHERE id = current_user_id)
```

### API Endpoint Summary (Phase 4)

**Spaces (9 endpoints):**
- `GET /api/spaces` - List user's spaces
- `POST /api/spaces` - Create space
- `GET /api/spaces/{id}` - Get space details
- `PATCH /api/spaces/{id}` - Update space
- `DELETE /api/spaces/{id}` - Delete space
- `POST /api/spaces/{id}/invite` - Invite member
- `POST /api/spaces/accept-invite` - Accept invitation
- `GET /api/spaces/{id}/members` - List members
- `DELETE /api/spaces/{id}/members/{user_id}` - Remove member

**API Keys (3 endpoints):**
- `GET /api/api-keys` - List keys
- `POST /api/api-keys` - Create key
- `DELETE /api/api-keys/{id}` - Revoke key

**Webhooks (6 endpoints):**
- `GET /api/webhooks` - List webhooks
- `POST /api/webhooks` - Create webhook
- `GET /api/webhooks/{id}` - Get webhook
- `PATCH /api/webhooks/{id}` - Update webhook
- `DELETE /api/webhooks/{id}` - Delete webhook
- `GET /api/webhooks/{id}/logs` - View logs

**Admin (5 endpoints):**
- `GET /api/admin/users` - List all users
- `GET /api/admin/spaces` - List all spaces
- `GET /api/admin/safety-events` - Safety logs
- `GET /api/admin/audit-log` - Audit trail
- `GET /api/admin/stats` - Platform stats

**External (2 endpoints):**
- `POST /api/external/chat` - API key chat
- `GET /api/external/clones` - List clones

**Enhanced:**
- `GET /api/clones?scope=personal|space|all&space_id={id}` - Filtered clone list
- `POST /api/clones?space_id={id}` - Create in space

### Service Layer (Phase 4)

**New Services:**

1. **Audit Service** (`backend/services/audit_service.py`)
   - `log_audit_event()` - Record sensitive operations
   - `get_user_audit_log()` - User's audit history
   - `get_all_audit_log()` - Admin full access

2. **Safety Service** (`backend/services/safety_service.py`)
   - `check_content_safety()` - Pattern matching
   - `check_input_safety()` - User message validation
   - `wrap_llm_output()` - Response sanitization
   - `log_safety_event()` - Event tracking
   - `get_safety_events()` - Query logs

3. **Webhook Service** (`backend/services/webhook_service.py`)
   - `dispatch_webhook()` - Send single webhook
   - `enqueue_event()` - Find and dispatch webhooks
   - `sign_payload()` - HMAC-SHA256 signing

### Security Enhancements (Phase 4)

1. **API Key Security**
   - Only hash stored (SHA-256)
   - Scope-based access control
   - Automatic expiration
   - Usage tracking
   - Revocation support

2. **Webhook Security**
   - HMAC-SHA256 payload signing
   - Timeout handling (10s)
   - Error logging
   - Active/inactive toggle

3. **Content Safety**
   - Input validation
   - Output sanitization
   - Pattern-based filtering
   - Safety event logging

4. **Multi-Tenant Isolation**
   - RLS enforces boundaries
   - Membership verification
   - Role-based permissions
   - Cascade delete protection

5. **Audit Compliance**
   - All sensitive ops logged
   - IP tracking
   - User agent recording
   - Admin-only access

### Backward Compatibility

Phase 4 maintains full compatibility with Phases 1-3:
- All existing endpoints unchanged
- Personal clones still default
- No breaking API changes
- Opt-in multi-tenancy
- Gradual migration path

### Performance Considerations

1. **Database Optimizations**
   - Indexes on all foreign keys
   - Indexes on space_id for multi-tenant queries
   - Composite indexes (user_id, space_id)
   - Optimized RLS policies

2. **Webhook Performance**
   - Asynchronous potential (currently sync)
   - 10-second timeout
   - Error handling
   - No blocking on failures

3. **Safety Performance**
   - Compiled regex patterns
   - Early exit on match
   - Minimal overhead (<5ms)

### Deployment Architecture (Phase 4)

```
Internet
    ↓
Load Balancer
    ↓
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
├──────────────────────┬──────────────────────────────────┤
│   Frontend (Next.js) │   Backend (FastAPI)              │
│   - Multi-tenant UI  │   - Spaces API                   │
│   - API key mgmt     │   - Webhook dispatcher           │
│   - Admin console    │   - Safety pipeline              │
│   - Space selector   │   - Audit logging                │
└──────────────────────┴──────────────────────────────────┘
    │                              │
    └──────────────┬───────────────┘
                   ↓
         Supabase PostgreSQL
                   │
    ┌──────────────┼──────────────┐
    │              │              │
 Tables (18)   RLS (35+)    Functions (3)
```

### Future Enhancements (Phase 5+)

1. **Advanced Webhooks**: Retry policies, background queue
2. **Enhanced Safety**: ML-based moderation, custom rules
3. **Analytics Dashboard**: Usage trends, engagement metrics
4. **Per-Space Billing**: Team pricing, usage-based billing
5. **Real-time Features**: WebSocket support, live updates
6. **Advanced Admin**: User impersonation, feature flags
