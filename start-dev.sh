#!/bin/bash

echo "Starting EcofulChat Knowledge Base System..."
echo

echo "[1/4] Installing frontend dependencies..."
npm install
if [ $? -ne 0 ]; then
    echo "Failed to install frontend dependencies"
    exit 1
fi

echo "[2/4] Creating environment files..."
if [ ! -f .env ]; then
    echo "VITE_API_BASE_URL=http://localhost:8080/api/v1" > .env
    echo "Created .env file"
fi

if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "Created backend/.env file - please configure your API keys"
fi

echo "[3/4] Starting frontend development server..."
npm run dev &
FRONTEND_PID=$!

echo "[4/4] Instructions for backend:"
echo
echo "To complete the setup, please run in another terminal:"
echo "1. Install Python dependencies: cd backend && pip install -r requirements.txt"
echo "2. Start Docker services: cd backend && docker-compose up -d"
echo "3. Initialize database: cd backend && python manage_db.py create-db && python manage_db.py upgrade"
echo "4. Start backend: cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload"
echo
echo "Frontend will be available at: http://localhost:3000"
echo "Backend API will be available at: http://localhost:8080"
echo
echo "Press Ctrl+C to stop the frontend server"

# Wait for frontend process
wait $FRONTEND_PID