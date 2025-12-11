# Contributing to CloneMemoria

This guide explains how to extend and customize CloneMemoria for your specific needs.

## Development Workflow

### 1. Setting Up Your Development Environment

```bash
# Clone the repository
git clone <your-repo>
cd clonememoria

# Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend setup (in new terminal)
cd frontend
npm install
```

### 2. Running in Development Mode

**Backend (Terminal 1):**
```bash
cd backend
source venv/bin/activate
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend (Terminal 2):**
```bash
cd frontend
npm run dev
```

## Extending the Backend

### Adding a New API Endpoint

1. **Create or modify a route file:**

```python
# backend/api/routes/your_feature.py
import logging
from fastapi import APIRouter, Depends
from supabase import Client

from backend.db.client import get_db
from backend.api.deps import get_current_user_id

logger = logging.getLogger(__name__)
logger.info("YOUR_FEATURE_ROUTES_LOADED", extra={"file": __file__})

router = APIRouter()

@router.get("/your-endpoint")
async def your_endpoint(
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
):
    logger.info("YOUR_ENDPOINT_CALLED", extra={"user_id": user_id})

    # Your logic here

    return {"message": "Success"}
```

2. **Register the router in `main.py`:**

```python
from backend.api.routes import your_feature

app.include_router(
    your_feature.router,
    prefix=f"{settings.API_V1_PREFIX}/your-feature",
    tags=["your-feature"]
)
```

### Adding a New Database Table

1. **Create a Supabase migration:**

Use the Supabase dashboard or CLI to add tables. Example:

```sql
CREATE TABLE IF NOT EXISTS your_table (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  data jsonb,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX idx_your_table_user_id ON your_table(user_id);

ALTER TABLE your_table ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own data"
  ON your_table FOR SELECT
  TO authenticated
  USING (user_id = (current_setting('app.current_user_id'))::uuid);
```

2. **Create Pydantic schemas:**

```python
# backend/schemas/your_model.py
from pydantic import BaseModel
from datetime import datetime

class YourModelBase(BaseModel):
    data: dict

class YourModelCreate(YourModelBase):
    pass

class YourModelResponse(YourModelBase):
    id: str
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True
```

### Creating a Custom AI Provider

1. **Create a new provider file:**

```python
# backend/ai/providers/custom.py
import logging
from backend.ai.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

class CustomProvider(LLMProvider):
    async def generate_clone_reply(
        self,
        clone_info: dict,
        memories: list,
        conversation_history: list,
        user_message: str,
        tone_config: dict = None
    ) -> str:
        logger.info("CUSTOM_PROVIDER_GENERATING")

        # Your custom AI logic
        # Could be:
        # - Local model inference
        # - Custom API call
        # - Rule-based system
        # - Hybrid approach

        return "Your generated response"
```

2. **Register in the factory:**

```python
# backend/ai/factory.py
from backend.ai.providers.custom import CustomProvider

def get_llm_provider() -> LLMProvider:
    provider_type = settings.LLM_PROVIDER.lower()

    if provider_type == "custom":
        return CustomProvider()
    # ... existing providers
```

## Extending the Frontend

### Adding a New Page

1. **Create the page file:**

```typescript
// frontend/src/app/your-feature/page.tsx
'use client';

import { useEffect } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { logger } from '@/utils/logger';

export default function YourFeaturePage() {
  useEffect(() => {
    logger.info('YourFeaturePage loaded');
  }, []);

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-display text-gray-900 mb-8">
          Your Feature
        </h1>
        {/* Your content */}
      </div>
    </AppLayout>
  );
}
```

### Creating a New Component

```typescript
// frontend/src/components/your-feature/YourComponent.tsx
'use client';

import React from 'react';

interface YourComponentProps {
  data: any;
  onAction: () => void;
}

export function YourComponent({ data, onAction }: YourComponentProps) {
  return (
    <div className="card">
      <h3 className="text-xl font-display text-gray-900 mb-4">
        {data.title}
      </h3>
      <button onClick={onAction} className="btn-primary">
        Do Something
      </button>
    </div>
  );
}
```

### Adding API Integration

```typescript
// In your component or page
import { apiClient } from '@/lib/apiClient';
import { logger } from '@/utils/logger';

const fetchData = async () => {
  try {
    logger.info('Fetching your data');
    const data = await apiClient.get('/api/your-endpoint', true);
    logger.info('Data fetched successfully');
    return data;
  } catch (error) {
    logger.error('Failed to fetch data', {
      error: error instanceof Error ? error.message : 'Unknown'
    });
    throw error;
  }
};
```

## Code Style Guidelines

### Backend (Python)

- Use type hints for function parameters and returns
- Log all significant operations
- Use Pydantic for validation
- Follow PEP 8 style guide
- Add docstrings for complex functions

**Example:**

```python
async def complex_operation(
    user_id: str,
    data: Dict[str, Any]
) -> ComplexResult:
    """
    Performs a complex operation.

    Args:
        user_id: The user's unique identifier
        data: Operation data

    Returns:
        ComplexResult with operation outcome

    Raises:
        ValueError: If data is invalid
    """
    logger.info("COMPLEX_OPERATION_STARTED", extra={
        "user_id": user_id,
        "data_keys": list(data.keys())
    })

    # Implementation

    logger.info("COMPLEX_OPERATION_COMPLETED")
    return result
```

### Frontend (TypeScript)

- Use TypeScript strictly (no `any` unless absolutely necessary)
- Use functional components with hooks
- Log user actions and API calls
- Follow Tailwind utility-first approach
- Keep components focused and small

**Example:**

```typescript
interface DataItem {
  id: string;
  name: string;
  created_at: string;
}

export function DataList({ items }: { items: DataItem[] }) {
  const handleItemClick = (id: string) => {
    logger.info('Item clicked', { id });
    // Handle click
  };

  return (
    <div className="space-y-4">
      {items.map((item) => (
        <div
          key={item.id}
          onClick={() => handleItemClick(item.id)}
          className="card cursor-pointer hover:shadow-soft-lg transition-shadow"
        >
          <h3 className="text-lg font-display">{item.name}</h3>
        </div>
      ))}
    </div>
  );
}
```

## Testing

### Backend Testing

Create test files in `backend/tests/`:

```python
# backend/tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_register_user():
    response = client.post(
        "/api/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpass123"
        }
    )
    assert response.status_code == 201
    assert "access_token" in response.json()
```

Run tests:
```bash
cd backend
pytest
```

### Frontend Testing

Create test files alongside components:

```typescript
// frontend/src/components/YourComponent.test.tsx
import { render, screen } from '@testing-library/react';
import { YourComponent } from './YourComponent';

describe('YourComponent', () => {
  it('renders correctly', () => {
    render(<YourComponent data={{ title: 'Test' }} onAction={() => {}} />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });
});
```

Run tests:
```bash
cd frontend
npm test
```

## Common Customizations

### 1. Changing the Design System

Modify `frontend/tailwind.config.ts`:

```typescript
theme: {
  extend: {
    colors: {
      primary: {
        50: '#...',
        // ... your colors
      },
    },
  },
},
```

Update `frontend/src/app/globals.css` for component styles.

### 2. Adding Memory Import Features

1. Create a new API endpoint for imports
2. Parse the imported data format (WhatsApp, etc.)
3. Bulk create memories
4. Add UI for file upload

### 3. Adding Audio/Video Support

1. Extend database schema with media columns
2. Set up Supabase Storage
3. Add upload endpoints
4. Create media player components
5. Update AI prompts to reference media

### 4. Implementing Memory Search

1. Add full-text search to PostgreSQL
2. Create search endpoint with query parameter
3. Add search UI component
4. Optionally: Implement semantic search with embeddings

### 5. Multi-Language Support

**Backend:**
- Use `gettext` or similar for message translation
- Store user language preference

**Frontend:**
- Use `next-intl` or `react-i18next`
- Create translation files
- Detect browser language

## Debugging Tips

### Backend Debugging

1. **Enable DEBUG logging:**
```env
LOG_LEVEL=DEBUG
```

2. **Use Python debugger:**
```python
import pdb; pdb.set_trace()
```

3. **Check logs for request_id:**
All logs for a request share the same `request_id`.

### Frontend Debugging

1. **Check browser console:**
All logs appear in development mode.

2. **Use React DevTools:**
Inspect component state and props.

3. **Network tab:**
Monitor API calls and responses.

## Performance Optimization

### Backend

- Add database indexes for frequently queried columns
- Implement caching (Redis) for hot data
- Use connection pooling
- Optimize AI provider calls (batch, cache)

### Frontend

- Use Next.js Image component for optimization
- Implement lazy loading for components
- Add pagination for long lists
- Memoize expensive computations

## Documentation

When adding new features:

1. Update `README.md` if user-facing
2. Add technical details to `ARCHITECTURE.md`
3. Update API documentation (FastAPI auto-generates this)
4. Add inline code comments for complex logic
5. Update this `CONTRIBUTING.md`

## Questions or Issues?

- Review the existing codebase for patterns
- Check the logs for detailed error information
- Refer to framework documentation (FastAPI, Next.js)
- Test incrementally as you build

---

Happy coding! Build amazing memory-preserving experiences with CloneMemoria.
