## AniList integration

This app supports connecting an AniList account to import your existing ANIME/MANGA lists.

- Click "Add AniList account" in the top-right after logging in.
- Authorize in the popup, then click "Import from AniList" to import your lists.

Configurable settings (override via .env):

- ANILIST_CLIENT_ID (default 29366)
- ANILIST_CLIENT_SECRET
- ANILIST_REDIRECT_URI (default http://localhost:8000/api/anilist/callback)
# Anime & Manga Tracker (MVP)

A lightweight FastAPI-based tracker inspired by Tachiyomi/Mihon concepts. Includes JWT auth, a simple library with CRUD, mock sources, and a minimal static frontend.

## Features
- Auth: password login (demo user), JWT bearer
- Library: add/list/get/update/delete items with status and progress
- Sources: list hardcoded sources and mock search
- Frontend: simple HTML to login and manage library
- Tests: API smoke tests

## Quickstart

### 1) Create venv and install deps
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Run the API
```bash
uvicorn app.main:app --reload
```
- API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs

### 3) Open frontend
Serve `frontend/` via any static server, or open `frontend/index.html` directly and set apiBase accordingly.

## Notes
- This MVP uses in-memory storage; restart clears data. Swap to a DB via SQLModel.
- The demo user is `demo` / `demo1234`.
- Replace SECRET_KEY and add proper user management for production.
