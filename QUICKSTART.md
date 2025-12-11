# CloneMemoria - Quick Start Guide (Phase 4 Platform)

Get CloneMemoria running locally in 5 minutes with multi-tenant spaces, developer integrations, and enterprise-grade platform features.

## Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- Supabase account (database is pre-configured)

## Step 1: Environment Setup

The `.env` file is already configured with Supabase credentials. No changes needed for local development.

**Phase 3 runs in "dummy mode" by default** - all AI, TTS, and billing features work without external API keys.

**Optional:** To use real external providers:

```bash
# Edit .env and configure:
LLM_PROVIDER=external
LLM_API_KEY=your-openai-api-key
TTS_DEFAULT_PROVIDER=external
TTS_API_KEY=your-elevenlabs-api-key
BILLING_PROVIDER=stripe
STRIPE_API_KEY=your-stripe-key
```

## Step 2: Start the Backend

### Option A: Using the startup script (Linux/Mac)

```bash
cd backend
./start.sh
```

### Option B: Manual setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start server
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at: **http://localhost:8000**

API docs: **http://localhost:8000/docs**

## Step 3: Start the Frontend

Open a new terminal:

### Option A: Using the startup script (Linux/Mac)

```bash
cd frontend
./start.sh
```

### Option B: Manual setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at: **http://localhost:3000**

## Step 4: Create Your First Clone

1. **Register an account:**
   - Open http://localhost:3000
   - Click "Create one" to register
   - Enter your email and password

2. **Create a clone:**
   - Click "+ New Clone"
   - Enter a name (e.g., "Papa", "Best Friend")
   - Write a personality description
   - Adjust tone sliders (warmth, humor, formality)
   - Click "Create Clone"

3. **Add memories:**
   - Click on your clone card
   - Click "Memories"
   - Click "+ Add Memory"
   - Write about experiences, conversations, or characteristics
   - The more memories, the better the AI understands the person

4. **Start chatting:**
   - Go back to your clone detail
   - Click "Chat"
   - Start a conversation!
   - Click the speaker icon on assistant messages to hear them as audio (TTS)

## Phase 3 New Features

### 1. GDPR Compliance & Privacy

**Manage Consents:**
- Click "Account & Privacy" from the dashboard
- Toggle consent preferences:
  - Voice Processing (required for TTS)
  - Video Processing (for future avatar features)
  - Third-Party APIs (to use external AI providers)
  - Data Processing (core functionality)
- Click "Save Consent Preferences"

**Export Your Data:**
- Go to "Account & Privacy"
- Click "Export Data" to download all your data as JSON
- Includes: profile, clones, memories, conversations, messages

**Delete Your Data:**
- Go to "Account & Privacy"
- Click "Delete All Data" (with confirmation)
- Soft-deletes all your data for GDPR compliance

### 2. Billing & Usage Tracking

**View Usage:**
- Click "Billing & Usage" from the dashboard
- See current plan (Free, Pro, or Enterprise)
- Monitor usage: clones, messages, documents
- View today's activity: messages, tokens, TTS requests

**Upgrade Plan (Demo Mode):**
- Click "Upgrade" on any plan
- Demo mode returns a dummy checkout URL
- Configure `BILLING_PROVIDER=stripe` for real billing

### 3. Text-to-Speech (TTS)

**Play Messages as Audio:**
- In any chat, click the speaker icon next to assistant messages
- Audio is generated using the TTS provider (dummy mode by default)
- Requires `consent_voice_processing` to be enabled in Account settings

### 4. API Features

**New Endpoints:**
- `/metrics` - View application metrics (Prometheus-compatible)
- `/api/v1/gateway/health` - Health check for all services
- `/api/v1/auth/me/consent` - Manage GDPR consents
- `/api/v1/auth/me/export` - Export user data
- `/api/v1/auth/me/data` - Delete user data
- `/api/v1/billing/plan` - Current billing plan
- `/api/v1/billing/usage` - Usage statistics
- `/api/v1/audio/tts/{clone_id}` - Generate TTS audio
- `/api/v1/avatar/generate/{clone_id}` - Avatar generation (stub)

Visit http://localhost:8000/docs to explore all endpoints.

## Phase 4 Platform Features (NEW!)

### 1. Multi-Tenant Spaces

**Create a Space (Organization/Family):**
```bash
# Via API
curl -X POST http://localhost:8000/api/spaces \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Family", "description": "Family memories space"}'
```

**Or via UI:**
- Navigate to `/spaces` (link from dashboard)
- Click "Create New Space"
- Enter name and description
- You become the owner automatically

**Invite Members:**
```bash
# Via API
curl -X POST http://localhost:8000/api/spaces/{space_id}/invite \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "member@example.com", "role": "member"}'
```

**Accept Invitation:**
```bash
curl -X POST http://localhost:8000/api/spaces/accept-invite \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"token": "invitation_token_from_email"}'
```

**Share Clones in Space:**
- When creating a clone, select "Space" scope
- Choose which space to share it in
- All space members can now chat with this clone

### 2. API Keys & Developer Integration

**Create an API Key:**
```bash
curl -X POST http://localhost:8000/api/api-keys \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My App", "scopes": ["chat", "read"]}'
```

**Response includes raw key (shown only once):**
```json
{
  "id": "...",
  "name": "My App",
  "key_prefix": "cmk_abc123...",
  "raw_key": "cmk_abc123...full_key_here",
  "warning": "This is the only time the full API key will be shown. Store it securely."
}
```

**Use API Key for External Chat:**
```bash
curl -X POST http://localhost:8000/api/external/chat \
  -H "X-API-Key: cmk_your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "clone_id": "your_clone_id",
    "message": "Hello from external app!"
  }'
```

**List Accessible Clones:**
```bash
curl http://localhost:8000/api/external/clones \
  -H "X-API-Key: cmk_your_api_key_here"
```

### 3. Webhooks

**Create a Webhook:**
```bash
curl -X POST http://localhost:8000/api/webhooks \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.com/webhook",
    "events": ["clone.created", "message.created"],
    "is_active": true
  }'
```

**Webhook Payload Format:**
```json
{
  "event": "message.created",
  "timestamp": "2025-12-09T10:30:00Z",
  "data": {
    "clone_id": "...",
    "message_id": "...",
    "content": "Message preview..."
  }
}
```

**Webhook headers include:**
- `X-Webhook-Event`: Event name
- `X-Webhook-Signature`: HMAC-SHA256 signature for verification

### 4. Admin Console

**Enable Platform Admin:**
```sql
-- Connect to your Supabase database
UPDATE users
SET is_platform_admin = true
WHERE email = 'admin@example.com';
```

**Access Admin Console:**
- Navigate to `/admin` (only accessible to platform admins)
- View all users, spaces, safety events, and audit logs
- Monitor platform-wide statistics

**Admin API Endpoints:**
```bash
# Get platform stats
curl http://localhost:8000/api/admin/stats \
  -H "Authorization: Bearer ADMIN_TOKEN"

# List all users
curl http://localhost:8000/api/admin/users \
  -H "Authorization: Bearer ADMIN_TOKEN"

# View safety events
curl http://localhost:8000/api/admin/safety-events \
  -H "Authorization: Bearer ADMIN_TOKEN"

# View audit log
curl http://localhost:8000/api/admin/audit-log \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### 5. Content Safety

Content safety is automatically applied to all conversations:
- Input messages are checked before processing
- LLM outputs are sanitized before saving
- Safety events are logged for admin review
- Unsafe content is blocked with user-friendly messages

**View Your Safety Events:**
```bash
curl http://localhost:8000/api/admin/safety-events?user_id=YOUR_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 6. Audit Logging

All sensitive operations are logged:
- Login attempts
- GDPR data exports/deletions
- Billing plan changes
- Space operations
- API key creation/revocation
- Content safety events

**View Audit Log:**
- Platform admins can view full audit log at `/admin`
- Users can view their own audit entries via API

## Testing Without API Costs

By default, CloneMemoria uses a `DummyProvider` that generates random responses without calling external APIs. This is perfect for:

- Local development
- Testing the application
- Demos

The dummy responses will be contextual but templated. To get AI-generated responses, configure an external LLM provider (see `.env` configuration).

## Project Structure

```
/backend          → FastAPI API (Python)
/frontend         → Next.js UI (TypeScript/React)
/README.md        → Full documentation
/ARCHITECTURE.md  → Technical architecture
/QUICKSTART.md    → This file
```

## Common Issues

### Backend won't start

**Error:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:** Activate the virtual environment and install dependencies:
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend build errors

**Error:** `Cannot find module 'next'`

**Solution:** Install dependencies:
```bash
cd frontend
rm -rf node_modules .next
npm install
```

### Can't login after registration

**Solution:** Check that the backend is running on port 8000 and accessible. Check browser console for errors.

## Next Steps

- Read the [full README](README.md) for detailed information
- Explore [ARCHITECTURE.md](ARCHITECTURE.md) for complete architecture
- Review [PHASE4_COMPLETE.md](PHASE4_COMPLETE.md) for Phase 4 features
- Create spaces and invite team members
- Generate API keys for external integrations
- Set up webhooks for event notifications
- Customize AI providers for better responses (LLM, TTS, embeddings)
- Add more memories to improve clone accuracy
- Experiment with different tone configurations
- Try TTS playback in chat
- Manage your privacy settings in Account page
- Monitor usage in Billing page

## Need Help?

- Check the logs in the terminal running the backend (structured JSON logs)
- Visit http://localhost:8000/docs for API documentation
- Review the README.md for troubleshooting tips

---

Enjoy preserving your cherished memories with CloneMemoria!
