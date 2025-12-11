# Setup Supabase pour CloneMemoria

Ce guide vous montre comment configurer CloneMemoria avec votre base Supabase **déjà connectée**.

---

## ✅ Étape 1 : Récupérer vos Clés API Supabase

Votre base Supabase est déjà connectée à : `https://gniuyicdmjmzbgwbnvmk.supabase.co`

Vous devez maintenant récupérer vos clés API :

1. Allez sur [https://supabase.com](https://supabase.com)
2. Ouvrez votre projet : `gniuyicdmjmzbgwbnvmk`
3. Cliquez sur **Settings** (⚙️) dans la sidebar
4. Cliquez sur **API**

Vous verrez deux sections :

### Project URL
```
https://gniuyicdmjmzbgwbnvmk.supabase.co
```
✅ Déjà configurée dans le projet !

### API Keys

Vous avez deux clés importantes :

**1. `anon` `public` key**
- Utilisée par le frontend
- Sûre à exposer publiquement
- Commence par `eyJhbGc...`

**2. `service_role` `secret` key**
- ⚠️ **CRITIQUE** : Utilisée par le backend
- **NE JAMAIS EXPOSER PUBLIQUEMENT**
- Donne accès complet à la base
- Commence par `eyJhbGc...`

Cliquez sur **"Reveal"** pour voir les clés complètes.

---

## ⚙️ Étape 2 : Configurer le fichier .env

Ouvrez le fichier `.env` à la racine du projet et remplacez :

```bash
# Remplacez ces lignes :
VITE_SUPABASE_ANON_KEY=AJOUTEZ-VOTRE-ANON-KEY-ICI
SUPABASE_ANON_KEY=AJOUTEZ-VOTRE-ANON-KEY-ICI
SUPABASE_SERVICE_ROLE_KEY=AJOUTEZ-VOTRE-SERVICE-ROLE-KEY-ICI

# Par vos vraies clés :
VITE_SUPABASE_ANON_KEY=eyJhbGc...VOTRE-ANON-KEY-COMPLETE...
SUPABASE_ANON_KEY=eyJhbGc...VOTRE-ANON-KEY-COMPLETE...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...VOTRE-SERVICE-ROLE-KEY-COMPLETE...
```

**⚠️ IMPORTANT** :
- Copiez les clés COMPLÈTES (pas juste le début)
- Pas d'espaces avant/après
- La `service_role_key` est **OBLIGATOIRE** pour que le backend fonctionne

---

## 🗄️ Étape 3 : Appliquer les Migrations SQL

Vos tables n'existent pas encore dans Supabase. Vous devez appliquer les migrations.

### Via l'Interface Supabase (Recommandé)

1. Dans votre dashboard Supabase, cliquez sur **SQL Editor** (icône </>)
2. Cliquez sur **"New query"**
3. Appliquez chaque migration **dans l'ordre** :

#### Migration 1 : Phase 1 (Core)
```bash
Fichier : supabase/migrations/20251209004951_create_clonememoria_schema.sql
```
- Ouvrez ce fichier dans un éditeur
- Copiez TOUT le contenu
- Collez dans Supabase SQL Editor
- Cliquez sur **"Run"** (ou F5)
- Vérifiez qu'il n'y a pas d'erreurs (message de succès en vert)

#### Migration 2 : Phase 2 (RAG/AI)
```bash
Fichier : supabase/migrations/20251209032627_extend_clonememoria_schema_phase2.sql
```
- Même processus

#### Migration 3 : Phase 3 (GDPR)
```bash
Fichier : supabase/migrations/20251211021802_20251209053100_phase3_gdpr_and_extensions.sql
```
- Même processus

#### Migration 4 : Phase 4 (Workspaces)
```bash
Fichier : supabase/migrations/20251211021936_20251209180000_phase4_collaborative_workspaces.sql
```
- Même processus

#### Migration 5 : Phase 5 (Production)
```bash
Fichier : supabase/migrations/20251211022043_20251210024820_phase5_production_features_v2.sql
```
- Même processus

### Vérifier les Tables

Après avoir appliqué toutes les migrations :

1. Allez dans **Table Editor** (icône tableau)
2. Vous devriez voir ces tables :
   - ✅ `users`
   - ✅ `clones`
   - ✅ `memories`
   - ✅ `conversations`
   - ✅ `messages`
   - ✅ `documents`
   - ✅ `document_chunks`
   - ✅ `ai_config`
   - ✅ `usage_metrics`
   - ✅ `billing_quotas`
   - ✅ `workspaces`
   - ✅ `workspace_members`
   - ✅ `space_invitations`
   - ✅ `api_keys`
   - ✅ `webhooks`
   - ✅ `webhook_logs`
   - ✅ `safety_events`
   - ✅ `audit_log`
   - ✅ `avatars`

Si vous voyez toutes ces tables, les migrations sont appliquées avec succès ! ✅

---

## 🚀 Étape 4 : Lancer le Projet

### Backend

```bash
cd backend

# Créer environnement virtuel (si pas déjà fait)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Installer dépendances
pip install -r requirements.txt

# Lancer le serveur
python -m uvicorn main:app --reload --log-level debug
```

Le backend sera sur : **http://localhost:8000**

Vérifiez que vous voyez ces logs :
```
INFO: SETTINGS_LOADED
INFO: SUPABASE_CLIENT_CREATED
INFO: Application startup complete
```

Si vous voyez `SUPABASE_CLIENT_CREATED`, c'est que la connexion fonctionne ! ✅

### Frontend

Dans un **nouveau terminal** :

```bash
cd frontend

# Installer dépendances (si pas déjà fait)
npm install

# Lancer le serveur
npm run dev
```

Le frontend sera sur : **http://localhost:3000**

---

## ✅ Étape 5 : Tester

### Test 1 : Health Check Backend

Ouvrez votre navigateur :
```
http://localhost:8000/api/health
```

Vous devriez voir :
```json
{
  "status": "healthy",
  "timestamp": "...",
  "database": "connected"
}
```

### Test 2 : Créer un Compte

1. Allez sur `http://localhost:3000/register`
2. Remplissez le formulaire :
   - Email : `test@example.com`
   - Nom : `Test User`
   - Password : `password123`
3. Cliquez sur **"Créer un compte"**

**Si ça marche** : Vous serez redirigé vers le dashboard ✅

**Si erreur 500** : Vérifiez que `SUPABASE_SERVICE_ROLE_KEY` est bien configurée dans `.env`

### Test 3 : Vérifier dans Supabase

1. Retournez dans Supabase → **Table Editor**
2. Cliquez sur la table `users`
3. Vous devriez voir votre utilisateur `test@example.com` ✅

---

## 🐛 Dépannage

### Erreur 500 sur /api/auth/register ou /api/auth/login

**Cause** : `SUPABASE_SERVICE_ROLE_KEY` non configurée ou invalide

**Solution** :
1. Vérifiez `.env` ligne 15
2. Assurez-vous que la clé est complète (commence par `eyJhbGc...`)
3. Pas d'espaces, pas de quotes
4. Redémarrez le backend

### Erreur "relation users does not exist"

**Cause** : Migrations SQL non appliquées

**Solution** :
1. Allez dans Supabase → SQL Editor
2. Appliquez les 5 migrations dans l'ordre
3. Vérifiez dans Table Editor que les tables existent

### Backend ne démarre pas

**Cause** : Dépendances Python non installées

**Solution** :
```bash
cd backend
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Frontend ne démarre pas

**Cause** : node_modules manquant

**Solution** :
```bash
cd frontend
rm -rf node_modules .next
npm install
npm run dev
```

### CORS Errors dans le navigateur

**Cause** : Backend pas lancé ou sur mauvais port

**Solution** :
- Backend DOIT être sur `http://localhost:8000`
- Frontend DOIT être sur `http://localhost:3000`
- Vérifiez que les deux serveurs tournent

---

## 📋 Checklist Finale

Avant de considérer le setup complet :

- [ ] Clés Supabase ajoutées dans `.env`
- [ ] 5 migrations appliquées dans Supabase SQL Editor
- [ ] 19 tables visibles dans Table Editor
- [ ] Backend démarre sans erreur
- [ ] Frontend démarre sans erreur
- [ ] Health check retourne `"database": "connected"`
- [ ] Peut créer un compte
- [ ] Utilisateur visible dans table `users`

Si tous les items sont cochés : **Setup complet !** ✅

---

## 🎯 Architecture Technique

Le projet utilise :

- **Backend** : FastAPI (Python) avec authentification JWT + bcrypt custom
- **Frontend** : Next.js 15 (React + TypeScript)
- **Base de données** : Supabase PostgreSQL (votre base connectée)
- **Auth** : Custom (PAS Supabase Auth natif)

Le backend utilise `SUPABASE_SERVICE_ROLE_KEY` pour :
- Bypasser les RLS policies PostgreSQL
- Gérer l'authentification au niveau applicatif
- Avoir un contrôle total sur les requêtes

**⚠️ C'est pourquoi cette clé est CRITIQUE.**

---

## 📚 Documentation Complète

- `README.md` - Vue d'ensemble du projet
- `QUICKSTART.md` - Guide de démarrage général
- `ARCHITECTURE.md` - Architecture technique détaillée
- `MIGRATION_STATUS.md` - État des migrations
- `CORRECTIONS_ET_VERIFICATIONS.md` - Corrections appliquées

---

## 🆘 Besoin d'Aide ?

1. Activez les logs debug dans `.env` :
   ```bash
   LOG_LEVEL=DEBUG
   LOG_FORMAT=debug
   ```
2. Redémarrez le backend
3. Lisez les logs colorés dans le terminal
4. Les logs montreront exactement où l'erreur se produit

---

**Bon déploiement ! 🚀**
