# CloneMemoria - Migration Status & Sequence

**Last Updated**: December 11, 2025
**Status**: ✅ All Migrations Applied and Verified

---

## Migration Sequence (Chronological Order)

### Phase 1: Core Schema
**File**: `20251209004951_create_clonememoria_schema.sql`
**Status**: ✅ Applied

Creates foundational tables:
- `users` - User accounts
- `clones` - AI clones
- `memories` - Clone memories
- `conversations` - Chat conversations
- `messages` - Individual messages

### Phase 2: AI Configuration & RAG
**File**: `20251209032627_extend_clonememoria_schema_phase2.sql`
**Status**: ✅ Applied

Adds AI configuration and knowledge base:
- Extended `clones` with AI provider configuration
- `clone_documents` - Knowledge base documents
- `clone_document_chunks` - Vector embeddings for RAG

### Phase 3: GDPR & Billing Infrastructure
**Files**:
- `20251209055501_20251209053100_phase3_gdpr_and_extensions_v2.sql` (auto-applied)
- `20251211021802_20251209053100_phase3_gdpr_and_extensions.sql` (exported)

**Status**: ✅ Applied (both idempotent versions)

Adds GDPR compliance and billing:
- Extended `users` with:
  - GDPR consent fields (data, voice, video, third-party, whatsapp)
  - Billing fields (plan, period dates, customer_id)
  - `is_platform_admin` flag
  - `last_data_export_at`
- `usage_metrics` table - Daily usage tracking
- Soft delete columns (`deleted_at`) on all major tables
- Enhanced `clone_documents` with language and metadata

### Phase 4: Collaborative Workspaces
**Files**:
- `20251209204140_phase4_multitenant_platform.sql` (auto-applied)
- `20251211021936_20251209180000_phase4_collaborative_workspaces.sql` (exported)

**Status**: ✅ Applied (both idempotent versions)

Adds multi-tenant workspace features:
- `spaces` - Team workspaces
- `space_members` - Workspace membership
- `space_invitations` - Token-based invitations
- `audit_log` - Activity tracking
- `webhooks` + `webhook_logs` - Event integrations
- `safety_events` - Content moderation tracking
- Extended all major tables with `space_id` column
- Added `is_personal` flag to `clones`

### Phase 5: Production Features
**Files**:
- `20251210024820_phase5_production_features.sql` (original, has role column issue)
- `20251211022043_20251210024820_phase5_production_features_v2.sql` (corrected)

**Status**: ✅ Applied (v2 is the authoritative version)

Adds production-ready features:
- `api_keys` - Developer API keys with hashing
- `api_key_usage` - Rate limiting tracking
- `billing_quotas` - Plan limits (free/pro/enterprise)
- Extended `clones` with `avatar_image_url`
- Helper functions for quota enforcement

**Important**: Phase 5 v2 uses `is_platform_admin` (from Phase 3) instead of a custom `role` column to avoid conflicts with Supabase Auth.

---

## Migration Safety

### Idempotency
All migrations use safe patterns:
- `CREATE TABLE IF NOT EXISTS`
- `DO $$ BEGIN IF NOT EXISTS... END $$` for column additions
- `DROP POLICY IF EXISTS` before creating policies
- `ON CONFLICT DO UPDATE` for initial data inserts

### Re-run Safety
All migrations can be safely re-run without:
- Data loss
- Duplicate errors
- Constraint violations

This is why duplicate migrations (auto-applied vs. exported) coexist without issues.

---

## Database Schema Overview

### Core Tables (Phase 1)
- users, clones, memories, conversations, messages

### AI & Knowledge (Phase 2)
- clone_documents, clone_document_chunks

### GDPR & Billing (Phase 3)
- usage_metrics

### Workspaces (Phase 4)
- spaces, space_members, space_invitations
- audit_log, webhooks, webhook_logs, safety_events

### Production (Phase 5)
- api_keys, api_key_usage, billing_quotas

**Total**: 16 tables + numerous helper functions

---

## Key Schema Design Decisions

### 1. Admin Access
**Uses**: `is_platform_admin` boolean (Phase 3)
**Not**: Custom `role` text column (conflicts with Supabase Auth)

Backend dependency: `get_current_admin()` checks `is_platform_admin`

### 2. Soft Deletes
All major tables have `deleted_at timestamptz` for:
- Data retention and audit trails
- GDPR compliance (mark as deleted without losing history)
- Graceful recovery

### 3. Multi-Tenancy
Resources can be:
- **Personal**: `space_id IS NULL` and `is_personal = true`
- **Shared**: `space_id IS NOT NULL` and `is_personal = false`

### 4. Row Level Security (RLS)
All tables have comprehensive RLS policies:
- User isolation (can only access own data)
- Space-aware access control
- Admin overrides where appropriate

---

## Verification Queries

### Check All Tables Exist
```sql
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

Expected: 16 tables + auth tables from Supabase

### Check Phase 3 GDPR Columns
```sql
SELECT
  consent_data_processing,
  consent_voice_processing,
  is_platform_admin,
  billing_plan
FROM users LIMIT 1;
```

### Check Phase 4 Workspace Tables
```sql
SELECT COUNT(*) FROM spaces;
SELECT COUNT(*) FROM space_members;
SELECT COUNT(*) FROM space_invitations;
```

### Check Phase 5 Production Tables
```sql
SELECT COUNT(*) FROM api_keys;
SELECT COUNT(*) FROM billing_quotas;  -- Should be 3 plans
```

---

## Migration Files Exported

All phase migrations are now present in the project:

```
supabase/migrations/
├── 20251209004951_create_clonememoria_schema.sql (Phase 1)
├── 20251209032627_extend_clonememoria_schema_phase2.sql (Phase 2)
├── 20251211021802_20251209053100_phase3_gdpr_and_extensions.sql (Phase 3)
├── 20251211021936_20251209180000_phase4_collaborative_workspaces.sql (Phase 4)
└── 20251211022043_20251210024820_phase5_production_features_v2.sql (Phase 5)
```

**Note**: Older auto-applied versions also exist but are superseded by the exported versions. All are idempotent and safe.

---

## Backend Compatibility

### Admin Check Pattern
```python
from backend.api.deps import get_current_admin

@router.get("/admin/endpoint")
async def admin_only(
    admin: dict = Depends(get_current_admin)
):
    # admin["is_platform_admin"] == True guaranteed
    ...
```

### Quota Check Pattern
```python
from backend.services.quota_service import check_clone_creation_quota

is_allowed, error = await check_clone_creation_quota(db, user_id, billing_plan)
if not is_allowed:
    raise HTTPException(status_code=402, detail=error)
```

---

## Documentation Files

- ✅ `PHASE2_COMPLETE.md` - Phase 2 documentation
- ✅ `PHASE3_COMPLETE.md` - Phase 3 documentation (auto-generated)
- ✅ `PHASE4_COMPLETE.md` - Phase 4 documentation (newly created)
- ✅ `PHASE5_COMPLETE.md` - Phase 5 documentation (updated for v2)
- ✅ `MIGRATION_STATUS.md` - This file

---

## Next Steps

### For Deployment
1. All migrations are already applied to the current Supabase instance
2. For new environments, migrations will apply in chronological order automatically
3. Idempotency ensures safe re-application

### For Development
1. Backend is fully compatible with the schema
2. All admin endpoints use `is_platform_admin`
3. Quota enforcement is active and tested
4. Frontend types match the schema

---

## Summary

✅ **Phase 1**: Core schema (users, clones, memories, conversations, messages)
✅ **Phase 2**: AI config + RAG (documents, embeddings)
✅ **Phase 3**: GDPR + billing (consents, usage_metrics, is_platform_admin)
✅ **Phase 4**: Workspaces (spaces, members, invitations, audit, webhooks, safety)
✅ **Phase 5**: Production (api_keys, billing_quotas, avatar uploads)

**All migrations**: Idempotent, RLS-enabled, well-documented, and production-ready.

**Database Status**: 100% synchronized and consistent.

---

**Migration Status**: Complete and Verified ✅
