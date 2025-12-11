# CloneMemoria - Complete Project Structure

This document lists all files in the CloneMemoria project.

## Root Directory

```
/
├── .env                           # Environment variables (configured)
├── .env.example                   # Example environment configuration
├── .gitignore                     # Git ignore rules
├── README.md                      # Main documentation
├── ARCHITECTURE.md                # Technical architecture details
├── QUICKSTART.md                  # Quick start guide
├── PROJECT_STRUCTURE.md           # This file
├── backend/                       # Python FastAPI backend
└── frontend/                      # Next.js TypeScript frontend
```

## Backend (`/backend`)

### Core Application Files

```
backend/
├── main.py                        # FastAPI app entry point & route registration
├── requirements.txt               # Python dependencies
├── start.sh                       # Startup script (executable)
└── .gitignore                     # Backend-specific ignore rules
```

### Core Module (`/backend/core`)

```
backend/core/
├── __init__.py
├── config.py                      # Settings & environment variables
├── logging_config.py              # JSON logging configuration
└── security.py                    # JWT & password hashing utilities
```

### Database Module (`/backend/db`)

```
backend/db/
├── __init__.py
└── client.py                      # Supabase client singleton
```

### API Module (`/backend/api`)

```
backend/api/
├── __init__.py
├── middleware.py                  # Request logging middleware
└── deps.py                        # Dependency injection (auth, ownership)
```

### API Routes (`/backend/api/routes`)

```
backend/api/routes/
├── __init__.py
├── auth.py                        # Register, login, get current user
├── clones.py                      # CRUD operations for clones
├── memories.py                    # CRUD operations for memories
└── conversations.py               # Conversations & chat with AI
```

### AI Module (`/backend/ai`)

```
backend/ai/
├── __init__.py
├── llm_provider.py                # Base LLM provider interface
└── factory.py                     # Provider factory function
```

### AI Providers (`/backend/ai/providers`)

```
backend/ai/providers/
├── __init__.py
├── dummy.py                       # Dummy provider (no API calls)
└── external.py                    # External API provider (OpenAI-compatible)
```

### Schemas Module (`/backend/schemas`)

```
backend/schemas/
├── __init__.py
├── user.py                        # User Pydantic schemas
├── clone.py                       # Clone Pydantic schemas
├── memory.py                      # Memory Pydantic schemas
└── conversation.py                # Conversation & message Pydantic schemas
```

## Frontend (`/frontend`)

### Configuration Files

```
frontend/
├── package.json                   # Node.js dependencies & scripts
├── next.config.mjs                # Next.js configuration
├── tsconfig.json                  # TypeScript configuration
├── tailwind.config.ts             # Tailwind CSS configuration
├── postcss.config.mjs             # PostCSS configuration
├── .eslintrc.json                 # ESLint configuration
├── start.sh                       # Startup script (executable)
└── .gitignore                     # Frontend-specific ignore rules
```

### App Directory (`/frontend/src/app`)

```
frontend/src/app/
├── layout.tsx                     # Root layout with AuthProvider
├── page.tsx                       # Home page (redirect logic)
├── globals.css                    # Global styles & Tailwind utilities
├── login/
│   └── page.tsx                   # Login page
├── register/
│   └── page.tsx                   # Registration page
├── dashboard/
│   └── page.tsx                   # Dashboard (clone list & creation)
└── clones/
    └── [id]/
        ├── page.tsx               # Clone detail page
        ├── memories/
        │   └── page.tsx           # Memories management page
        └── chat/
            └── page.tsx           # Chat interface page
```

### Components (`/frontend/src/components`)

```
frontend/src/components/
├── layout/
│   └── AppLayout.tsx              # Authenticated app layout with header
├── common/
│   └── ErrorBoundary.tsx          # Error boundary component
├── clone/
│   └── CloneCard.tsx              # Clone display card
├── forms/
│   ├── CloneForm.tsx              # Clone creation/edit form
│   └── MemoryForm.tsx             # Memory creation form
└── chat/
    ├── ChatWindow.tsx             # Main chat interface
    └── MessageBubble.tsx          # Individual message display
```

### Contexts (`/frontend/src/contexts`)

```
frontend/src/contexts/
└── AuthContext.tsx                # Authentication context & hooks
```

### Library (`/frontend/src/lib`)

```
frontend/src/lib/
└── apiClient.ts                   # HTTP client with logging
```

### Utils (`/frontend/src/utils`)

```
frontend/src/utils/
└── logger.ts                      # Frontend logging utility
```

### Types (`/frontend/src/types`)

```
frontend/src/types/
└── index.ts                       # TypeScript type definitions
```

## Database (Supabase)

The database schema is created via Supabase migrations:

**Tables:**
- `users` - User accounts
- `clones` - AI clones with personality config
- `memories` - Text memories for clones
- `conversations` - Chat sessions
- `messages` - Individual messages

**Security:**
- Row Level Security (RLS) enabled on all tables
- User isolation policies
- Cascade delete relationships

## Total File Count

### Backend: 24 files
- Main files: 3
- Core module: 4
- Database module: 2
- API module: 2
- API routes: 5
- AI module: 2
- AI providers: 3
- Schemas module: 6

### Frontend: 28 files
- Config files: 7
- App pages: 8
- Components: 8
- Contexts: 1
- Library: 1
- Utils: 1
- Types: 1

### Documentation & Config: 7 files
- Root documentation: 4
- Environment: 2
- Git: 1

**Total: 59 files** (excluding node_modules, venv, and generated files)

## Key Technologies

**Backend:**
- FastAPI 0.109.0
- Supabase Python Client 2.3.4
- Python-JOSE (JWT)
- Passlib (bcrypt)
- Python-JSON-Logger

**Frontend:**
- Next.js 15
- React 18
- TypeScript 5
- TailwindCSS 3
- Lucide React (icons)

**Database:**
- Supabase (PostgreSQL)
- Row Level Security (RLS)

## Architecture Patterns

- **Backend:** Layered architecture (API → Business Logic → Database)
- **Frontend:** Component-based with Context for global state
- **Authentication:** JWT tokens with RLS enforcement
- **Logging:** Structured JSON logging throughout
- **AI:** Provider pattern for swappable LLM backends
