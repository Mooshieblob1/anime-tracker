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

<!-- Configuration section intentionally omitted for MVP simplicity. Autocomplete and max lookups don’t require OAuth; AniList import is optional. -->

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

## Roadmap

Below are proposed next steps that are not yet implemented. Each item includes a brief methodology to reach the milestone.

1) Persist “max” chapter/episode values in the DB
   - Goal: Show consistent “progress X of N” without re-querying AniList every time and support offline viewing.
   - Methodology:
     - Schema: add `max_progress: int | None` to `LibraryItem` (nullable). Create an Alembic migration.
     - Write path: on add via autocomplete, include the fetched max in the POST payload; store it.
     - Backfill: add a one-off admin endpoint/script to query AniList and populate `max_progress` for existing rows.
     - UI: always render “of N” from DB when present; allow manual override.
     - Tests: unit test create/update, and a backfill script test with mocked AniList.

2) Store AniList media IDs and enrich metadata
   - Goal: Link items to canonical AniList entries for better accuracy and future sync.
   - Methodology:
     - Schema: add `anilist_id: int | None` and optional fields like `format`, `site_url`.
     - Create: when selecting from autocomplete, save the `anilist_id` along with title/cover.
     - Enrich: add an endpoint to refresh metadata for an item (cover/title/format) from AniList.
     - Tests: ensure ID persists and enrichment updates fields safely.

3) Two-way AniList sync (statuses and progress)
   - Goal: Keep local library and AniList in sync (import + push updates).
   - Methodology:
     - OAuth: persist AniList tokens securely (DB table) and implement refresh-token handling.
     - Mapping: define status/progress mapping between local and AniList (Reading↔CURRENT, Completed↔COMPLETED, Dropped↔DROPPED, Planning↔PLANNING; episodes/chapters to progress).
     - Push: on local PATCH, enqueue a job to update AniList via GraphQL mutation for linked `anilist_id`.
     - Pull: extend import to upsert by `anilist_id`; add a “Sync now” endpoint to fetch updates.
     - Background: add a simple task runner or APScheduler for periodic sync; handle retries/backoff.
     - Conflict: last-write-wins with a `synced_at` timestamp; surface conflicts in logs.
     - Tests: mock GraphQL; verify both push and pull paths.

4) Caching and rate-limit handling for AniList queries
   - Goal: Reduce latency and avoid rate-limit hits.
   - Methodology:
     - Add a small cache (SQLite table or in-memory with TTL) keyed by query and variables.
     - Respect AniList error codes; implement exponential backoff and minimal retry.
     - Log cache hit/miss metrics; expose debug stats endpoint.
     - Tests: cache TTL and backoff behavior with mocked time.

5) Additional source integrations (e.g., MangaDex)
   - Goal: Search and add from non-AniList sources.
   - Methodology:
     - Create `app/services/mangadex.py` with thin search/details functions.
     - Add `/api/sources/mangadex/search` and corresponding frontend wiring.
     - Normalize result shape to current autocomplete model; store `source` accordingly.
     - Tests: mock search results; verify add flow.

6) UX improvements for the library
   - Goal: Faster updates and better browsing.
   - Methodology:
     - Increment/decrement buttons next to progress; optional keyboard shortcuts.
     - Filters (type/status) and sort (updated_at, title); pagination for large libraries.
     - Toast notifications for save/remove; loading indicators for autocomplete.
     - Tests: basic UI smoke via Playwright (optional) or DOM checks in unit tests.

7) User management enhancements
   - Goal: Improve beyond the demo.
   - Methodology:
     - Registration refinements and basic profile editing.
     - Password reset flow (token email mock or local code entry for dev environments).
     - Tests: auth flows and edge cases.

8) Migrations with Alembic
   - Goal: Safely evolve the schema.
   - Methodology:
     - Initialize Alembic; configure SQLModel metadata target.
     - Generate migration for `max_progress` and `anilist_id` changes.
     - Document migration commands; add a small helper script to apply on startup in dev.
     - Tests: migration up/down on a temp DB.
