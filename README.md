# dynamics

Automative OS MVP for an Ohio electrical contractor.

## What is included

- FastAPI + SQLite backend in `backend/`
- React dashboard/portal (single-page app) in `frontend/index.html`
- Endpoints for:
  - AI lead intake
  - missed-call text-back
  - estimate follow-up automation
  - technician dispatch dashboard
  - maintenance reminders
  - solar proposal workflow
  - permit/document automation
  - quote generation assistance
  - KPI dashboard

## Setup

```bash
python3 -m pip install --user --break-system-packages -r requirements.txt
```

## Run

```bash
APP_DB_PATH=backend/data/live.sqlite3 python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open:

- http://127.0.0.1:8000/

## Test

Automated tests:

```bash
python3 -m pytest -q
```

Live API smoke test (server must be running):

```bash
python3 scripts/smoke_test.py
```
