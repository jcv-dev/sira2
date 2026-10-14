# SIRA personal

A personal, read-only toolkit for Universidad del Valle's SIRA academic registry: a **FastAPI backend** that exposes your student data as JSON, and a **React frontend** that makes it pleasant to look at.

```
sira2/
├── backend/    # FastAPI + httpx scraper (read-only) for sira1.univalle.edu.co
└── frontend/   # React 19 + Vite + Tailwind 4 + shadcn/ui + TanStack Query
```

> **Solo lectura.** The backend only performs the same queries the SIRA web UI does when viewing your grades, enrollment and profile. It never submits forms that modify anything.

## Quickstart

**1. Backend** (needs Python 3.11+ and [uv](https://docs.astral.sh/uv/)):

```bash
cd backend
cp .env.example .env        # add your SIRA username/password
uv sync
uv run uvicorn app.main:app --port 8000
```

API docs at <http://127.0.0.1:8000/docs>.

**2. Frontend** (needs Node 20+):

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The dev server proxies `/api` to the backend, so no CORS setup is needed.

## What you get

| | |
|---|---|
| Backend | `/me`, `/me/contact`, `/program`, `/grades`, `/grades/periods/{code}`, `/enrollment`, `/equivalences`, `/session/*` |
| Frontend | Resumen (period spine + GPA), Calificaciones, Matrícula, Programa (prerequisites), Equivalencias, Contacto — light/dark, deep-linkable state |

Details live in [`backend/README.md`](backend/README.md) and [`frontend/README.md`](frontend/README.md).

## Deploying the frontend elsewhere

Build with `npm run build` and serve `dist/`. Point the app at the API with `VITE_API_URL` (e.g. `https://api.example.com`) and allow the frontend origin in the backend with `SIRA_CORS_ORIGINS`.

## Caveats

- Personal use: respect Universidad del Valle's terms of service; this is an unofficial client for your own account.
- SIRA allows one active session per user: using the API logs out your browser session (and vice versa). Both sides recover automatically.
- Responses are cached briefly (default 5 min) to avoid load on the production server.
