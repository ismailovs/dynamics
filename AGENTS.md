# AGENTS.md

## Cursor Cloud specific instructions

This repository now contains a working Automative OS MVP for an electrical contractor.

### Repository state

- Backend: `backend/app/main.py` (FastAPI), SQLite persistence in `backend/data/`.
- Frontend: `frontend/index.html` (React via CDN, served by FastAPI).
- Tests: `tests/test_mvp.py` (pytest).
- Smoke script: `scripts/smoke_test.py`.

### Development notes

- Install dependencies:
  - `python3 -m pip install --user --break-system-packages -r requirements.txt`
- Run app:
  - `APP_DB_PATH=backend/data/live.sqlite3 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
- Run tests:
  - `python3 -m pytest -q`
- Run live smoke test (server must already be running):
  - `python3 scripts/smoke_test.py`
