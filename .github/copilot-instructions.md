# Copilot Instructions for this Repo

This repo is a small FastAPI application (MVP) for tracking Anime & Manga, inspired by Tachiyomi/Mihon. It includes a backend API with JWT auth, a per-user library persisted in SQLite via SQLModel (the demo user is auto-provisioned in the DB so choices are saved across restarts), basic mock “sources,” a minimal static frontend, and API tests.

## Architecture (big picture)
- App entry: `app/main.py`
  - FastAPI app with CORS and a lifespan hook that initializes the DB (`init_db`).
  - Routers mounted under `/api/*` and static frontend served from `/` (directory `frontend/`).
- Configuration: `app/config.py`
  - Settings via `pydantic-settings` (env-file: `.env`). Keys: `secret_key`, `algorithm`, `access_token_expire_minutes`, `database_url`.
  - AniList: `anilist_client_id`, `anilist_client_secret`, `anilist_redirect_uri`.
- Persistence: `app/db.py`, `app/models.py`
  - SQLModel models: `User`, `LibraryItem`. SQLite database file at `./app.db` by default.
  - `init_db()` creates tables; also called lazily in `get_session()` to keep tests robust.
- Routers:
  - `app/routers/auth.py`: OAuth2 password login -> JWT, `/register` to create DB users, `/me` returns current user. A built-in demo user (`demo/demo1234`) exists and is persisted in the DB on first login.
  - `app/routers/library.py`: CRUD for library items, persisted to SQLite for all users (demo included). Also exposes `/summary` with simple counts.
  - `app/routers/sources.py`: Hardcoded sources and mock search results.
  - `app/routers/anilist.py`: OAuth connect/callback/status/import endpoints; uses service `app/services/anilist_oauth.py`. Requires JWT and stores AniList tokens per-username in-memory (MVP).
- Frontend: `frontend/index.html` is a basic static page that logs in and manages the library via fetch calls.
- Tests: `tests/test_api.py` exercises health, auth + library CRUD, and sources.

## Key workflows
- Create and activate venv, install deps, run server:
  - `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
  - `uvicorn app.main:app --reload`
- Run tests:
  - `pytest -q` (see `pytest.ini` for PYTHONPATH config)
- Authenticate in dev:
  - Use demo: `demo` / `demo1234` -> POST `/api/auth/token` (OAuth2 form)
  - Or register a DB user via `POST /api/auth/register` then login.

## Conventions and patterns
- API shape:
  - Auth under `/api/auth/*`, Library under `/api/library/*`, Sources under `/api/sources/*`.
  - Bearer JWT is required for library/sources routes (see `get_current_user`).
- Storage model for library:
  - All users (including demo) persist to the SQLite DB via `LibraryItem`. This ensures choices are saved across restarts.
- Datetimes are timezone-aware (UTC) using `datetime.now(timezone.utc)` in models.
- DB init safety:
  - `get_session()` calls `init_db()` to avoid missing-table errors during tests or ad-hoc scripts.
- Static frontend served at `/`. When changing routes, keep CORS permissive or update fetch calls in `frontend/index.html`.

## Integration points
- JWT issuance/validation via `python-jose` and `passlib` (bcrypt).
- SQLModel/SQLAlchemy with SQLite; consider Alembic if you add migrations.
- Sources are mock-only; real integrations (AniList/MangaDex) should live under a new `app/services/` or `app/sources/` package and be invoked from the sources router.

## Examples from codebase
- Add a library item (DB path):
  - `POST /api/library/items` with `{title, type: "anime"|"manga", source, cover_url?, status?}`
  - See `add_item()` in `app/routers/library.py` for the DB vs fallback branching.
- Issue a token:
  - `POST /api/auth/token` (OAuth2 form fields), see `login()` in `app/routers/auth.py`.

## What to be careful with
- Don’t break the demo flow: the tests assume the `demo` user and in-memory library return an empty list initially, then CRUD works without registering.
- Keep `/api/*` routes stable; the frontend is coupled to these endpoints.
- If you modify model fields, update pydantic schemas in routers accordingly.
- If you change DB URL or secrets, document it in `README.md` and `.env`.

## Future-friendly notes
- Prefer adding new routers under `app/routers/` and new DB entities in `app/models.py`.
- For real source integrations, add thin service functions and keep routers mostly orchestration.
- If introducing migrations, wire an Alembic CLI workflow and document it here.

## PDF requirements alignment (Project 3 - Custom Management System)
Source of truth: CST182 - Programming Foundations, Project 3. Requirements tracked and mapped here.

Requirements (pasted):
- Apply Object-Oriented Programming; use classes/objects.
- Reusable functions/modules.
- Robust error handling and input validation.
- Test typical cases (or manual examples).
- Optional: Data visualisation and API integration.
- Data input and storage (memory or file I/O/persistence).
- User interactions for retrieval/update/delete.
- Categorisation of information.
- Clear, structured code with comments.

Implementation mapping:
- OOP: `User`, `LibraryItem` in `app/models.py` (SQLModel classes with attributes and relationship).
- Reuse: Shared DB/session utils in `app/db.py`; AniList service in `app/services/anilist_oauth.py`.
- Error handling: HTTP 4xx with messages; try/except for external API failures.
- Tests: `tests/test_api.py` covers health, auth, CRUD, sources.
- Visualisation: `/api/library/summary` aggregates counts (can be graphed in frontend if desired).
- API integration: AniList OAuth + import endpoints.
- Persistence: SQLite `app.db`; demo user auto-provisioned to persist choices.
- Interactions: CRUD under `/api/library/*`; search under `/api/sources/search`.
- Categorisation: `type` (anime/manga), `status`, `source` fields.
- Clarity: routers/services modular, commented.

Verification checklist:
- App boots and auto-creates tables.
- Library writes persist across restarts (SQLite).
- Demo login works (`demo/demo1234`); registered users work too.
- CRUD endpoints and `/summary` respond correctly.
- `/docs` shows endpoints; tests pass when environment has pytest installed.
