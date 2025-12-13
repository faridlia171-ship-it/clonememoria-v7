#!/bin/bash

echo "Starting CloneMemoria Frontend (Production Mode)..."

# Vérification des dépendances
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm ci --omit=dev
fi

# Build de production
echo "Building Next.js..."
npm run build

# Lancement du serveur
echo "Starting Next.js server on port 3000..."
npm run start
