# H-Engineers Enterprise — WhatsApp Customer Service Bot

Phase 1: Project Setup ✅

## Folder structure

```
h-engineers-whatsapp-bot/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI entrypoint
│   ├── config.py            # Settings loaded from .env
│   ├── logging_config.py    # Console + rotating file logging
│   └── core/
│       ├── __init__.py
│       └── exceptions.py    # Custom exception classes
├── .env.example              # Template — copy to .env, fill in real values
├── .gitignore
├── requirements.txt
└── README.md
```

## 1. Set up your virtual environment

A virtual environment is an isolated Python install just for THIS project, so
its dependencies never clash with other projects on your machine.

```bash
cd h-engineers-whatsapp-bot
python3 -m venv venv

# Activate it (do this every time you work on the project):
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

You'll know it worked because your terminal prompt will show `(venv)`.

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Set up environment variables

```bash
cp .env.example .env
```

Nothing to fill in yet for Phase 1 — the defaults in config.py work as-is.
You'll fill in WhatsApp/OpenAI/Paystack keys in later phases.

## 4. Run the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- `--reload` restarts the server automatically when you edit code (dev only —
  never use this flag in production).
- Visit `http://localhost:8000/health` — you should see:
  ```json
  {"status": "ok", "app": "H-Engineers Enterprise WhatsApp Bot", "environment": "development"}
  ```
- Visit `http://localhost:8000/docs` — FastAPI auto-generates interactive API
  docs (Swagger UI) for every endpoint you build. You'll use this constantly
  to test endpoints before wiring WhatsApp to them.

## 5. Initialize Git

```bash
git init
git add .
git commit -m "Phase 1: project setup, config, logging, error handling"
```

Then create a repo on GitHub and push:

```bash
git remote add origin <your-repo-url>
git branch -M main
git push -u origin main
```

`.gitignore` already excludes `.env`, `venv/`, and `logs/` — never commit
secrets or your virtual environment.

## Assignment (do this before Phase 2)

1. Get the server running locally and confirm `/health` and `/docs` both work.
2. Open `app/main.py` and add a new test endpoint `/ping` that returns
   `{"pong": true}`.
3. Deliberately break something (e.g. `raise NotFoundException("test")` inside
   the `/ping` route) and confirm you get a clean JSON 404 response, not a
   stack trace in the browser.
4. Push your work to GitHub.

## Common mistakes to avoid

- Forgetting to activate `venv` before installing packages (they'll install
  globally instead, causing "works on my machine" bugs later).
- Committing `.env` to Git — it's already git-ignored, but double check with
  `git status` before your first commit.
- Putting business logic directly in `main.py` — from Phase 3 onward, every
  feature gets its own router file; `main.py` only assembles them.

## What's next — Phase 2

Database design: Customers, Subscriptions, Plans, Payments, Support Tickets,
Engineers, Appointments, Activity Logs, Notifications — with SQLAlchemy
models and our first Alembic migration.
"# h-engineers-whatsapp-bot" 
