# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

Three independent runnable apps share this monorepo:

- `backend/` — FastAPI + SQLAlchemy + PyTorch. Real (and partly placeholder) AI service.
- `frontend/` — React 19 + Vite + TypeScript + Tailwind + shadcn/ui. Wraps the app inside a `PhoneShell` (mobile mockup) and routes through `RequireAuth` (mock localStorage auth, see `frontend/src/lib/auth.ts`).
- `mock-server/` — Express server on the **same port 8000** as the FastAPI backend. Serves the frontend with deterministic fake data when the Python backend isn't running. Only one of `backend` or `mock-server` can run at a time.

The repository is organized by **sprint phases (Sprint 1 → Sprint 4)**, and every backend sprint adds new routers, services, and singleton model stores. New endpoints are bolted onto `backend/app/main.py` rather than refactored — preserve that pattern when adding to a new sprint.

## Common commands

### Backend (run from `backend/`)
```bash
python -m venv venv
venv\Scripts\activate              # Windows; or: source venv/bin/activate
pip install -r requirements.txt
python check_setup.py              # validates packages, .env, DB connectivity, imports
uvicorn app.main:app --reload      # http://localhost:8000  (Swagger at /docs)
python train_risk_model.py         # regenerate models/risk_model.pkl + meta.json
```

The backend defaults to **SQLite** (`USE_SQLITE=True` in `.env` or default), file `backend/plant_health.db`. Set `USE_SQLITE=False` plus `DB_*` vars to use PostgreSQL. There are no Alembic migrations — `Base.metadata.create_all(bind=engine)` runs at startup and creates any missing tables. **New SQLAlchemy models must be imported in `app/main.py`** (look for the `# noqa: F401` block) or their tables will not be created.

### Frontend (run from `frontend/`)
```bash
npm install
npm run dev            # Vite on http://localhost:8080 (NOT 5173 — see vite.config.ts)
npm run build
npm run lint
npm run test           # vitest run
npm run test:watch
npx vitest run path/to/file.test.ts   # single test file
npx playwright test                   # E2E (uses lovable-agent-playwright-config preset)
```

The API base URL is `import.meta.env.VITE_API_URL || "http://localhost:8000"` (see `frontend/src/services/api.ts`).

### Mock server (run from `mock-server/`)
```bash
npm install
npm run dev            # node --watch server.js → http://localhost:8000
```

Use this when working on frontend features without standing up the Python+ML stack. Note `start-app.bat` at repo root references hardcoded paths from a previous machine and will not work as-is.

## Backend architecture

### Lifespan and the singleton model stores
`backend/app/main.py` uses an `@asynccontextmanager` lifespan to **load every ML model exactly once at startup** and unload them on shutdown. Models are large (PyTorch / Ultralytics / GNN) and re-loading per request is unacceptable. The pattern, repeated across sprints:

1. A service module owns a module-level singleton (e.g. `model_store`, `risk_v2_store`, `multimodal_store`, `digital_twin_store`, `yolo_detector`, `global_gnn_store`, `retraining_service`, `analytics_service`, `model_update_service`).
2. `lifespan()` in `main.py` calls `.load()` / `.load_all()` / `.initialize()` on each.
3. Routes import the singleton directly and read `.is_loaded` to decide between serving a real prediction and returning HTTP 503.
4. **Failures are isolated per model**: each `.load()` is wrapped so one missing weight file doesn't break the whole API. Only Sprint 2's primary `model_store.load_all()` is treated as critical (logs a warning and lets the app start with AI endpoints disabled).

When adding a new model:
- Build a `*Store` class with `load()` / `unload()` / `is_loaded`.
- Expose a module-level singleton instance.
- Wire `load()` into `lifespan()` and `unload()` into the shutdown half — both inside its own try/except.
- Optionally surface a reference on `model_store` (Sprint 3 and Sprint 4 both do this for centralized status reporting; see `core/model_manager.py`).

### Sprint-based router layering
Each sprint adds a router (or several) registered in `main.py` via `app.include_router(...)`. Don't try to consolidate them; the Sprint 4 router (`ai_sprint4.py`) explicitly mounts under `/api/v4` while older routers stay at root paths. The grouping in `main.py` (Sprint 2/3/4 with comments) is the canonical map for finding endpoints.

### Model weight files
- Lives under `models/` (repo root) and `backend/app/models/` (for `risk_model.pkl`).
- All `*.pt`, `*.pth`, `*.pkl` are gitignored — share weights out-of-band.
- `core/model_manager.py` falls back to base pretrained YOLOv8 / EfficientNet weights if custom `.pt` files are missing, so the API can still come up for development.
- **`DEFAULT_CLASS_NAMES` in `core/model_manager.py` must match the order used during EfficientNet training** — update it whenever a retraining changes the label set.

### Database
- `app/database/connection.py` exposes `engine`, `SessionLocal`, `Base`, and the `get_db()` FastAPI dependency. Use `Depends(get_db)` in routes.
- The SQLite default exists for dev convenience; PostgreSQL is the intended production target. SQLite path adds `check_same_thread=False`; PostgreSQL goes through `psycopg2-binary`.
- `Base.metadata.create_all(bind=engine)` at startup means **schema changes require dropping the dev DB**, not migrating it.

### Placeholder vs. real AI
The README is correct that `/ai/*` was originally a placeholder, but Sprints 2–4 introduced real model code. Treat each `/ai*` endpoint individually — check the corresponding service to see whether it returns mock data or runs a real model. The fallbacks in `core/model_manager.py` mean an endpoint can return real-looking predictions from a base pretrained model rather than the project's fine-tuned weights.

## Frontend architecture

- `App.tsx` is the routing root: every authenticated route goes through `Shell` → `RequireAuth` (redirects to `/login` if no `agri_user` in localStorage) → `AppShell` (chrome) → page. `PhoneShell` wraps the entire app with a phone-frame layout.
- `services/api.ts` is the single chokepoint for backend calls — extend the typed wrappers there rather than calling `fetch` directly from components.
- `components/ui/` is shadcn/ui (Radix + Tailwind). Use existing primitives; configuration is in `components.json`.
- Path alias `@/*` → `./src/*` (Vite + tsconfig).
- Vitest setup is `src/test/setup.ts` (jsdom + jest-dom).

## Conventions to know

- Code comments and log messages are largely in **Turkish**. Match the local style (Turkish docstrings, English identifiers) when editing existing files; new top-level docs can be either, but be consistent within a file.
- New SQLAlchemy models **must** be imported in `app/main.py` (the `# noqa: F401` block) — otherwise `create_all` won't see them and the table is silently missing.
- The mock server and FastAPI both bind to **port 8000**. Stop one before starting the other.
- Vite dev server uses **port 8080**, not the Vite default 5173 — CORS in `backend/app/config/settings.py` already allows it.
