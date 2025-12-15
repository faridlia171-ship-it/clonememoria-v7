#!/usr/bin/env bash
set -e

BACKEND_URL="https://clonememoria-backend.onrender.com"
FRONTEND_URL="https://clonememoria-frontend.onrender.com"

echo "=============================="
echo "🔍 CLONEMEMORIA FULL CHECK"
echo "=============================="

echo ""
echo "1️⃣ Backend root"
curl -s -o /dev/null -w "HTTP %{http_code}\n" "$BACKEND_URL/"

echo ""
echo "2️⃣ Backend health"
curl -s -o /dev/null -w "HTTP %{http_code}\n" "$BACKEND_URL/health"

echo ""
echo "3️⃣ Backend OpenAPI"
curl -s -o /dev/null -w "HTTP %{http_code}\n" "$BACKEND_URL/openapi.json"

echo ""
echo "4️⃣ CORS preflight (register)"
curl -s -X OPTIONS \
  -H "Origin: $FRONTEND_URL" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  -D - \
  "$BACKEND_URL/api/auth/register" | grep -i access-control || true

echo ""
echo "5️⃣ Auth routes availability"
curl -s -o /dev/null -w "REGISTER %{http_code}\n" "$BACKEND_URL/api/auth/register"
curl -s -o /dev/null -w "LOGIN %{http_code}\n" "$BACKEND_URL/api/auth/login"

echo ""
echo "6️⃣ Frontend reachability"
curl -s -o /dev/null -w "HTTP %{http_code}\n" "$FRONTEND_URL"

echo ""
echo "=============================="
echo "✅ CHECK FINISHED"
echo "=============================="
