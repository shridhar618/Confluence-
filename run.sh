#!/bin/bash

echo ""
echo "┌─────────────────────────────────────────┐"
echo "│  SecureAI — Starting servers            │"
echo "└─────────────────────────────────────────┘"

# Start backend
echo "→ Starting backend on :5001 ..."
cd backend
if [ -f venv311/bin/activate ]; then
  source venv311/bin/activate
elif [ -f venv/bin/activate ]; then
  source venv/bin/activate
elif [ -f venv/Scripts/activate ]; then
  source venv/Scripts/activate
fi
PORT=5001 python app.py &
BACKEND_PID=$!

# Give backend a moment to start
sleep 2

# Start frontend
echo "→ Starting frontend on :3000 ..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✓ Backend  → http://localhost:5001"
echo "✓ Frontend → http://localhost:3000"
echo ""
echo "Demo logins:"
echo "  Admin:  admin / admin123"
echo "  HR:     hr_jane / hr123"
echo "  Intern: intern_bob / intern123"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait and handle Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped.'; exit 0" INT
wait
