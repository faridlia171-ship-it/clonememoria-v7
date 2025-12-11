# CloneMemoria

An AI-powered application for creating conversational clones of real people, preserving their memories, personality, and communication style.

## Overview

CloneMemoria allows users to:
- Create multiple AI "clones" of people (loved ones, historical figures, or themselves)
- Store and organize memories for each clone
- Chat with clones that respond based on their personality configuration and memories
- Customize tone, warmth, humor, and formality for each clone

## What's New in Phase 5 🎉

**Phase 5 transforms CloneMemoria into a production-ready SaaS platform:**

### For End Users:
- ✨ **Complete AI Configuration** - Customize LLM, embeddings, and TTS providers per clone
- 📚 **Knowledge Base Management** - Upload and manage documents for RAG with chunk tracking
- 🖼️ **Avatar Upload** - Upload custom avatar images for your clones
- 📊 **Quota System** - Clear limits and usage tracking (FREE, STARTER, PRO plans)

### For Developers:
- 🔑 **API Keys** - Secure API keys with scopes and rate limiting
- 🔐 **Rate Limiting** - Built-in request throttling per API key
- 📈 **Usage Tracking** - Real-time usage statistics and quotas

### For Platform Admins:
- 👥 **Admin Console** - Platform-wide user and clone management
- 📊 **Analytics** - Platform statistics and metrics dashboard
- 🔒 **Role-Based Access** - Admin role for platform oversight

**All Phase 5 features work in dummy mode (no external API keys required).**

See [PHASE5_COMPLETE.md](./PHASE5_COMPLETE.md) for complete documentation.

## Architecture

This project uses a monorepo structure with separate backend and frontend:

```
/backend          → FastAPI REST API (Python)
/frontend         → Next.js 15 App Router (TypeScript + React)
```

### Tech Stack

**Backend:**
- Python 3.11+
- FastAPI (REST API framework)
- Supabase (PostgreSQL database)
- JWT authentication
- Provider-agnostic AI layer (supports Dummy mode or external LLMs like OpenAI)
- Comprehensive JSON logging

**Frontend:**
- Next.js 15 (App Router)
- TypeScript
- TailwindCSS (emotional, warm design system)
- React hooks & context
- Client-side logging

## Database Schema

The application uses Supabase PostgreSQL with the following tables:

- `users` - User accounts
- `clones` - AI clones with personality configuration
- `memories` - Text memories for each clone
- `conversations` - Chat sessions with clones
- `messages` - Individual messages in conversations

All tables have Row Level Security (RLS) enabled for multi-tenant isolation.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Supabase account (database is pre-configured)

### Backend Setup

1. **Create a virtual environment:**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Configure environment variables:**

The `.env` file in the project root is already configured with Supabase credentials. Key variables:

```env
# Supabase
SUPABASE_URL=https://fneudyfhoxlgwlvaxcxm.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# JWT
SECRET_KEY=clonememoria-secret-key-change-in-production-please
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# AI Provider Configuration
LLM_PROVIDER=dummy  # or "external" for OpenAI/other
LLM_API_URL=        # e.g., https://api.openai.com/v1/chat/completions
LLM_API_KEY=        # Your API key
LLM_MODEL=gpt-3.5-turbo

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

4. **Start the backend server:**

```bash
# From project root
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation (Swagger UI): `http://localhost:8000/docs`

### Frontend Setup

1. **Install dependencies:**

```bash
cd frontend
npm install
```

2. **Start the development server:**

```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## AI Provider Configuration

The backend uses a provider-agnostic AI architecture that supports multiple LLM backends.

### Dummy Provider (Default - No API Key Required)

The default configuration uses a `DummyProvider` that generates random responses for testing:

```env
LLM_PROVIDER=dummy
```

This is perfect for:
- Local development
- Testing the application flow
- Demos without incurring API costs

### External Provider (OpenAI or Compatible APIs)

To use a real LLM:

1. Set the provider type:
```env
LLM_PROVIDER=external
```

2. Configure your API endpoint and key:
```env
LLM_API_URL=https://api.openai.com/v1/chat/completions
LLM_API_KEY=sk-your-api-key-here
LLM_MODEL=gpt-3.5-turbo
```

The external provider works with any OpenAI-compatible API (OpenAI, Azure OpenAI, local models via LM Studio, etc.)

### Extending with New Providers

To add a new provider:

1. Create a new class in `backend/ai/providers/` that implements `LLMProvider`
2. Implement the `generate_clone_reply()` method
3. Register it in `backend/ai/factory.py`

## Project Structure

### Backend (`/backend`)

```
backend/
├── main.py                    # FastAPI app entry point
├── requirements.txt           # Python dependencies
├── core/
│   ├── config.py             # Settings & environment variables
│   ├── logging_config.py     # Logging setup (JSON format)
│   └── security.py           # JWT & password hashing
├── db/
│   └── client.py             # Supabase client singleton
├── api/
│   ├── middleware.py         # Request logging middleware
│   ├── deps.py               # Dependency injection (auth, ownership)
│   └── routes/
│       ├── auth.py           # Registration, login, me
│       ├── clones.py         # CRUD for clones
│       ├── memories.py       # CRUD for memories
│       └── conversations.py  # Conversations & chat
├── ai/
│   ├── llm_provider.py       # Base LLM provider interface
│   ├── factory.py            # Provider factory
│   └── providers/
│       ├── dummy.py          # Dummy provider for testing
│       └── external.py       # External API provider (OpenAI-compatible)
└── schemas/
    ├── user.py               # Pydantic schemas for users
    ├── clone.py              # Pydantic schemas for clones
    ├── memory.py             # Pydantic schemas for memories
    └── conversation.py       # Pydantic schemas for chat
```

### Frontend (`/frontend`)

```
frontend/
├── package.json
├── next.config.mjs
├── tailwind.config.ts
├── src/
│   ├── app/
│   │   ├── layout.tsx              # Root layout with AuthProvider
│   │   ├── page.tsx                # Home (redirects to login/dashboard)
│   │   ├── globals.css             # Global styles & Tailwind
│   │   ├── login/page.tsx          # Login page
│   │   ├── register/page.tsx       # Registration page
│   │   ├── dashboard/page.tsx      # Clone list & creation
│   │   └── clones/[id]/
│   │       ├── page.tsx            # Clone detail
│   │       ├── memories/page.tsx   # Memory management
│   │       └── chat/page.tsx       # Chat interface
│   ├── components/
│   │   ├── layout/
│   │   │   └── AppLayout.tsx       # Authenticated layout with header
│   │   ├── common/
│   │   │   └── ErrorBoundary.tsx   # Error boundary component
│   │   ├── clone/
│   │   │   └── CloneCard.tsx       # Clone card display
│   │   ├── forms/
│   │   │   ├── CloneForm.tsx       # Clone creation/edit form
│   │   │   └── MemoryForm.tsx      # Memory creation form
│   │   └── chat/
│   │       ├── ChatWindow.tsx      # Main chat interface
│   │       └── MessageBubble.tsx   # Individual message display
│   ├── contexts/
│   │   └── AuthContext.tsx         # Authentication context & hooks
│   ├── lib/
│   │   └── apiClient.ts            # HTTP client with logging
│   ├── utils/
│   │   └── logger.ts               # Frontend logging utility
│   └── types/
│       └── index.ts                # TypeScript type definitions
```

## Logging

### Backend Logging

The backend uses structured JSON logging for all operations:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "level": "INFO",
  "logger_name": "backend.api.routes.clones",
  "message": "CLONE_CREATED_SUCCESS",
  "file": "/path/to/file.py",
  "function": "create_clone",
  "line": 45,
  "request_id": "abc123...",
  "clone_id": "uuid...",
  "clone_name": "Papa"
}
```

**Key features:**
- Every request gets a unique `request_id`
- Logs include file, function, and line number
- Timing information for requests and LLM calls
- Detailed error logging with stack traces

**Log levels:** DEBUG, INFO, WARNING, ERROR, CRITICAL

Control via environment variable:
```env
LOG_LEVEL=INFO
```

### Frontend Logging

The frontend logger provides:
- Colored, grouped console output in development
- JSON format in production (optional)
- Event-based logging for user actions and API calls

Example usage:
```typescript
import { logger } from '@/utils/logger';

logger.info('UserAction', { action: 'create_clone', cloneName: 'Papa' });
logger.error('APIError', { endpoint: '/api/clones', error: 'Network error' });
```

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info (authenticated)

### Clones

- `GET /api/clones` - List user's clones (authenticated)
- `POST /api/clones` - Create new clone (authenticated)
- `GET /api/clones/{clone_id}` - Get clone details (authenticated)
- `PUT /api/clones/{clone_id}` - Update clone (authenticated)
- `DELETE /api/clones/{clone_id}` - Delete clone (authenticated)

### Memories

- `GET /api/clones/{clone_id}/memories` - List memories for clone (authenticated)
- `POST /api/clones/{clone_id}/memories` - Add memory to clone (authenticated)
- `DELETE /api/memories/{memory_id}` - Delete memory (authenticated)

### Conversations

- `GET /api/clones/{clone_id}/conversations` - List conversations (authenticated)
- `POST /api/clones/{clone_id}/conversations` - Create conversation (authenticated)
- `GET /api/conversations/{conversation_id}/messages` - Get messages (authenticated)
- `POST /api/conversations/{conversation_id}/messages` - Send message & get AI reply (authenticated)

## Design System

The frontend uses a warm, emotional design with:

**Color Palette:**
- Cream backgrounds: `#fdf7f0` (primary background)
- Rose accents: `#f78fb3` (buttons, highlights)
- Sage greens: For complementary elements
- No purple/violet tones (per design requirements)

**Typography:**
- Display font (headings): Georgia, serif
- Body font: Inter, sans-serif (light weight)

**Components:**
- Rounded corners: `rounded-2xl`, `rounded-3xl`
- Soft shadows: `shadow-soft`, `shadow-soft-lg`
- Warm, inviting feel with generous padding and spacing

## Security

- JWT-based authentication with bcrypt password hashing
- Row Level Security (RLS) on all database tables
- User isolation - users can only access their own data
- Environment variables for sensitive configuration
- CORS configured for frontend origin

## Development Tips

### Backend Development

**Hot reload:** The `--reload` flag enables auto-restart on code changes

**API Documentation:** Visit `http://localhost:8000/docs` for interactive API docs

**Database queries:** All queries go through Supabase client with RLS enforcement

**Adding endpoints:** Create route files in `backend/api/routes/` and register in `main.py`

### Frontend Development

**Hot Module Replacement:** Next.js automatically updates on file changes

**Type safety:** Use TypeScript types from `src/types/index.ts`

**State management:** Auth state is in `AuthContext`, component state uses `useState`

**API calls:** Always use `apiClient` from `lib/apiClient.ts` for automatic logging

## Production Deployment

### Backend

1. Set production environment variables (strong SECRET_KEY, real LLM credentials)
2. Set `LOG_LEVEL=WARNING` or `ERROR` in production
3. Use a production WSGI server (gunicorn with uvicorn workers)
4. Enable HTTPS
5. Configure CORS for production frontend domain

### Frontend

1. Build the production bundle:
```bash
cd frontend
npm run build
```

2. Start production server:
```bash
npm start
```

3. Configure `NEXT_PUBLIC_API_URL` to point to production backend

## Extending the Application

### Adding New Clone Data Sources

1. Add new `source_type` values in the `memories` table
2. Create import functions in backend
3. Add UI for bulk import in frontend

### Adding Audio/Video Support

1. Extend `memories` table with media URL columns
2. Implement file upload to storage (Supabase Storage)
3. Update AI provider to handle multimodal data
4. Add media player components in frontend

### Custom AI Behaviors

1. Extend `tone_config` JSON structure with new parameters
2. Update `LLMProvider._build_system_prompt()` to use new parameters
3. Add UI controls in `CloneForm` component

## Troubleshooting

### Backend won't start

- Check Python version: `python --version` (need 3.11+)
- Verify virtual environment is activated
- Check `.env` file exists and has required variables
- Look for import errors in logs

### Frontend build errors

- Delete `node_modules` and `.next`, reinstall: `rm -rf node_modules .next && npm install`
- Check Node.js version: `node --version` (need 18+)
- Verify `NEXT_PUBLIC_API_URL` is set correctly

### Authentication issues

- Check JWT `SECRET_KEY` is set and consistent
- Verify backend is running on correct port
- Check browser console for API errors
- Clear localStorage and try logging in again

### AI responses not working

- If using external provider, verify API key is correct
- Check `LLM_PROVIDER` setting matches your configuration
- Look for errors in backend logs with tag `LLM_API_ERROR`
- Try switching to `dummy` provider to test application flow

## License

Proprietary - All rights reserved

## Contact

For questions or support, please contact the development team.
