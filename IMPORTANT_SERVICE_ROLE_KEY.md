# ⚠️ ACTION REQUISE : Service Role Key Manquante

## Statut Actuel

Vos clés Supabase ont été configurées :
- ✅ **URL Supabase** : `https://gniuyicdmjmzbgwbnvmk.supabase.co`
- ✅ **Anon Key** : Configurée
- ❌ **Service Role Key** : **MANQUANTE**

## Pourquoi la Service Role Key est CRITIQUE

La **Service Role Key** est nécessaire pour que le backend puisse :
1. Contourner les RLS policies (Row Level Security)
2. Créer des utilisateurs dans la table `users`
3. Faire fonctionner `/login` et `/register`

**Sans cette clé, vous aurez des erreurs 500 sur toutes les routes d'authentification.**

## Comment Obtenir la Service Role Key

### Étape 1 : Aller dans Supabase Dashboard

1. Allez sur https://supabase.com/dashboard
2. Sélectionnez votre projet : **gniuyicdmjmzbgwbnvmk**
3. Cliquez sur **Settings** (⚙️) dans le menu de gauche
4. Cliquez sur **API**

### Étape 2 : Copier la Service Role Key

Dans la section **Project API keys**, vous verrez :

```
anon public
eyJhbGci... (déjà configurée ✅)

service_role secret
eyJhbGci... ← COPIEZ CETTE CLÉ
```

**⚠️ ATTENTION** : La service_role key est **secrète** et donne un accès total à votre base de données. Ne la partagez JAMAIS publiquement.

### Étape 3 : Ajouter la Clé dans .env

Ouvrez le fichier `.env` à la racine du projet et remplacez :

```env
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY_HERE
```

Par :

```env
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ey...  # Votre vraie clé
```

### Étape 4 : Faire la même chose dans .env.debug

Ouvrez `.env.debug` et faites la même modification :

```env
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ey...  # Votre vraie clé
```

## Test de Validation

Une fois la clé ajoutée, testez la connexion :

```bash
cd backend
python -c "from backend.db.client import get_db; db = get_db(); print('✅ Connected')"
```

Si vous voyez "✅ Connected", c'est bon !

Ensuite testez l'inscription :

```bash
cd backend
uvicorn main:app --reload

# Dans un autre terminal
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!","full_name":"Test User"}'
```

Si vous recevez un JSON avec un `access_token`, tout fonctionne ! 🎉

## Que Se Passe-t-il Sans Cette Clé ?

Sans la service_role key, vous verrez ces erreurs :

```bash
# Erreur 500 sur /register
{"detail":"Failed to create user"}

# Erreur 500 sur /login
{"detail":"Login failed: ..."}

# Dans les logs backend
ERROR | Failed to create Supabase client
ERROR | 401 Unauthorized
```

## Sécurité

La service_role key :
- ✅ Doit être dans `.env` (jamais commitée dans git)
- ✅ Doit rester secrète
- ✅ Contourne TOUTES les RLS policies
- ✅ Est nécessaire pour l'auth custom
- ❌ Ne doit JAMAIS être dans le code frontend
- ❌ Ne doit JAMAIS être partagée publiquement

Le fichier `.gitignore` exclut déjà `.env` pour votre sécurité.

## Checklist Finale

Avant de lancer le projet, vérifiez :

- [x] URL Supabase configurée
- [x] Anon Key configurée
- [ ] **Service Role Key configurée** ← FAITES CECI MAINTENANT
- [ ] Backend démarré avec succès
- [ ] Test d'inscription réussi
- [ ] Test de connexion réussi

## Support

Si vous avez des difficultés :

1. Vérifiez que vous êtes dans le bon projet Supabase (gniuyicdmjmzbgwbnvmk)
2. Vérifiez que vous copiez la **service_role** key, pas l'anon key
3. Activez le mode debug : `cp .env.debug .env`
4. Regardez les logs backend pour les erreurs détaillées

---

**Une fois la service_role key ajoutée, supprimez ce fichier ou déplacez-le ailleurs pour ne pas le commiter accidentellement avec la clé dedans.**
