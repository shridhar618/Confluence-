#!/bin/bash
set -e

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   SecureAI — Setup Script                ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Backend
echo "→ Setting up backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt --quiet
cp -n .env.example .env 2>/dev/null || true
echo "✓ Backend ready"

# Frontend
cd ../frontend
echo "→ Installing frontend dependencies..."
npm install --silent
echo "✓ Frontend ready"

cd ..
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Setup complete!                        ║"
echo "║                                          ║"
echo "║   1. Edit backend/.env (add API key)     ║"
echo "║   2. Run: ./run.sh                       ║"
echo "╚══════════════════════════════════════════╝"
echo ""
