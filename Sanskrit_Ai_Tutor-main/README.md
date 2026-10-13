# SanskritAI - Modern Architecture

Intelligent Sanskrit Language Revival Through Adaptive Learning.
Migrated from Streamlit to a full-stack Next.js + FastAPI architecture.

## Folder Structure

- `/frontend`: Next.js app with TypeScript and React.
- `/backend`: FastAPI Python server with core logic modules.

## Getting Started

The backend and frontend use different package managers, so their dependencies are
listed separately: Python packages in `backend/requirements.txt` and JavaScript
packages in `frontend/package.json` (locked by `frontend/package-lock.json`).
From the repository root, `pip install -r requirements.txt` installs the backend
dependencies as a convenience; it includes `backend/requirements.txt`.

### Backend
1. `cd backend`
2. `pip install -r requirements.txt`
3. `python main.py`

The backend listens on `http://127.0.0.1:8005` by default. Keep it running in
its own terminal while using the frontend. To use a different backend URL, copy
`frontend/.env.example` to `frontend/.env.local`, edit `NEXT_PUBLIC_API_URL`,
and restart the frontend.

### Frontend
1. `cd frontend`
2. `npm install`
3. `npm run dev`

Navigate to `http://localhost:3000` to use the application.
Backend API documentation is available at `http://localhost:8005/docs`.
