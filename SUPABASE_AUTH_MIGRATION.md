# Migration vers Supabase Auth Natif

## Problème Identifié

Le projet utilise actuellement :
- ❌ Table `users` custom avec `password_hash`
- ❌ JWTs custom créés avec `python-jose`
- ❌ Gestion manuelle des mots de passe avec bcrypt
- ❌ SECRET_KEY locale pour les tokens

## Architecture Cible (Supabase Natif)

### 1. Authentification Supabase Auth

Supabase fournit nativement :
- ✅ `auth.users` - Table système gérée par Supabase
- ✅ JWTs signés par Supabase
- ✅ Gestion complète des mots de passe, réinitialisation, email confirmation
- ✅ Sessions et refresh tokens

### 2. Nouvelle Structure de Données

```sql
-- auth.users (géré par Supabase, ne PAS créer)
-- Contient: id, email, encrypted_password, created_at, etc.

-- user_profiles (notre extension)
CREATE TABLE user_profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name text,
  billing_plan text DEFAULT 'free',
  is_platform_admin boolean DEFAULT false,
  -- Tous les champs GDPR de Phase 3
  consent_data_processing boolean DEFAULT true,
  consent_voice_processing boolean DEFAULT false,
  -- etc.
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
```

### 3. Changements dans les Tables Existantes

Toutes les FK vers `users.id` deviennent des FK vers `user_profiles.id` :
- `clones.user_id` → `user_profiles.id`
- `memories.user_id` → `user_profiles.id`
- `conversations.user_id` → `user_profiles.id`
- etc.

**Note** : `user_profiles.id` = `auth.users.id` (même UUID)

### 4. Backend Changes

**Avant** :
```python
# Custom JWT
from jose import jwt
token = create_access_token({"sub": user_id})
```

**Après** :
```python
# Supabase Auth
from supabase import Client
auth_response = supabase.auth.sign_in_with_password({
    "email": email,
    "password": password
})
# JWT fourni par Supabase dans auth_response.session.access_token
```

### 5. Frontend Changes

**Avant** :
```typescript
// Custom fetch avec token local
const response = await fetch('/api/auth/login', {
  headers: { Authorization: `Bearer ${token}` }
})
```

**Après** :
```typescript
// SDK Supabase
import { createClient } from '@supabase/supabase-js'
const { data, error } = await supabase.auth.signInWithPassword({
  email,
  password
})
// Token automatiquement géré par le SDK
```

## Plan de Migration

### Phase 1 : Nouvelles Migrations
1. Créer `user_profiles` avec FK vers `auth.users`
2. Migrer données de `users` vers `user_profiles` (si données existantes)
3. Supprimer l'ancienne table `users`
4. Mettre à jour toutes les FK

### Phase 2 : Backend Refactor
1. Supprimer `core/security.py` (password hashing custom)
2. Refactorer `api/routes/auth.py` pour utiliser `supabase.auth`
3. Mettre à jour `api/deps.py` pour valider les JWTs Supabase
4. Mettre à jour tous les endpoints pour utiliser `user_profiles`

### Phase 3 : Frontend Refactor
1. Installer `@supabase/supabase-js`
2. Créer `lib/supabase.ts` avec le client
3. Mettre à jour `AuthContext` pour utiliser Supabase Auth
4. Mettre à jour toutes les requêtes API

### Phase 4 : RLS Policies
1. Utiliser `auth.uid()` au lieu de `current_setting('app.current_user_id')`
2. Mettre à jour toutes les policies

## Avantages de Supabase Auth

1. **Sécurité** : Gestion professionnelle des mots de passe
2. **Features** : Email confirmation, password reset, magic links gratuits
3. **Performance** : JWTs optimisés et cachés
4. **Simplicité** : Moins de code à maintenir
5. **Conformité** : GDPR-ready par défaut

## Migration Immédiate Requise

Le projet DOIT migrer vers Supabase Auth natif car :
- ❌ L'approche actuelle ne tire pas parti de Supabase
- ❌ Doublon de fonctionnalités (Supabase Auth + auth custom)
- ❌ Potentiels conflits entre les deux systèmes
- ❌ Code de sécurité custom = risques
- ❌ Pas d'accès aux features Supabase (email confirmation, etc.)

## Status

🔴 **Migration non effectuée** - Le projet utilise toujours l'auth custom

Je vais maintenant procéder à la migration complète.
