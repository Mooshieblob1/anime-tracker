# Anime & Manga Tracker (MVP)

A small FastAPI app for tracking manga/anime progress. It uses JWT auth, persists your library in SQLite via SQLModel, integrates with AniList for OAuth import and search, and ships with a minimal static frontend served by FastAPI.

## What’s included
- Auth: password login (built-in demo user) with JWT bearer tokens
- Persistence: SQLite database (`app.db`) with SQLModel; items survive restarts
- Library: add/list/get/update/delete items; status and progress fields; summary endpoint
- Sources:
  - Hardcoded sources list and mock search
  - Autocomplete powered by AniList GraphQL (no OAuth required)
  - “Max” episodes/chapters lookup per title
- AniList OAuth: connect/import your lists (tokens stored in-memory per user for MVP)
- Frontend: single static page served from `/`
- Tests: API tests for health, auth+library CRUD, and sources

## Quickstart

1) Create venv and install deps
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Run the server
```bash
uvicorn app.main:app --reload
```
- App + Frontend: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs

3) Sign in
- Demo user: `demo` / `demo1234`
- Or register via the Register button in the login modal (POST `/api/auth/register`).

4) Use it
- Search: start typing in the “Search title…” box; pick a suggestion (max chapters/episodes will show)
- Add: set type, optional progress, and click Add to save to your library
- Edit: change status (Planning, Reading/Watching, Dropped, Completed) and adjust progress inline; Save
- Remove: click Remove on an item
- AniList (optional):
  - Click “Add AniList account” after logging in; authorize in the popup
  - “Import from AniList” to pull your lists into the library

## API overview
- Auth
  - POST `/api/auth/token` (OAuth2 password form) → JWT
  - POST `/api/auth/register` → create a user
  - GET `/api/auth/me` → current user
- Library
  - GET `/api/library/items` → list
  - POST `/api/library/items` → create `{title, type, source, cover_url?, status?, progress?}`
  - GET `/api/library/items/{id}` → read
  - PATCH `/api/library/items/{id}` → update `{status?, progress?}`
  - DELETE `/api/library/items/{id}` → delete
  - GET `/api/library/summary` → simple counts
- Sources
  - GET `/api/sources/` → hardcoded sources
  - GET `/api/sources/search?q=&type=` → mock search (tests)
  - GET `/api/sources/autocomplete?q=&type=` → AniList-backed suggestions
  - GET `/api/sources/max?q=&type=` → max episodes/chapters for a title
- AniList
  - GET `/api/anilist/connect-url` → begin OAuth
  - GET `/api/anilist/callback` → OAuth redirect (server endpoint)
  - GET `/api/anilist/status` → connected?
  - POST `/api/anilist/import` → import lists (requires OAuth)

## Configuration (.env)
Settings are loaded via `pydantic-settings` from `.env`:

- App
  - `secret_key` (default: dev-secret-change-me)
  - `algorithm` (default: HS256)
  - `access_token_expire_minutes` (default: 1440)
  - `database_url` (default: sqlite:///./app.db)
- AniList
  - `anilist_client_id` (default: 29366)
  - `anilist_client_secret`
  - `anilist_redirect_uri` (default: http://127.0.0.1:8000/api/anilist/callback)

Note: Autocomplete and max lookups don’t require OAuth, but AniList import does.

## Dev and tests
- DB is auto-initialized on startup.
- When running tests, a separate `app_test.db` is used automatically.
- Run tests:
```bash
pytest -q
```

## Implementation notes
- Tokens for AniList OAuth are stored in-memory keyed by username (MVP only).
- Datetimes are stored as UTC.
- CORS is permissive for the MVP; tighten for production.

## Roadmap (nice-to-haves)
- Persist max chapter/episode values in the DB
- Real sources integrations beyond AniList (e.g., MangaDex)
- Better user management and password reset
- Alembic migrations
