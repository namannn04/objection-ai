# Objection AI — local development
SHELL := /bin/bash
PY := backend/.venv/bin/python

.PHONY: setup infra migrate seed backend worker frontend dev test e2e lint build clean

setup: ## Install everything (Python venv + npm)
	cd backend && python3 -m venv .venv && .venv/bin/pip install -q -r requirements-dev.txt
	cd frontend && npm install
	cd frontend && npx playwright install chromium
	[ -f .env ] || cp .env.example .env

infra: ## Postgres (5434) + Redis (6381) in Docker
	docker compose up -d postgres redis

migrate:
	cd backend && .venv/bin/alembic upgrade head

seed: ## Showcase case + curated cases with cached mock audio
	cd backend && .venv/bin/python -m app.seed

backend:
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

worker: ## Only needed if RUN_WORKER_IN_PROCESS=false
	cd backend && .venv/bin/python -m app.worker

frontend:
	cd frontend && npm run dev

dev: infra migrate seed ## Everything, in one terminal (Ctrl+C stops both)
	@trap 'kill 0' EXIT; \
	(cd backend && .venv/bin/uvicorn app.main:app --port 8000) & \
	(cd frontend && npm run dev) & \
	wait

test: ## Backend tests (SQLite, mock providers, no network)
	cd backend && .venv/bin/python -m pytest -q

e2e: ## Playwright journey (needs `make dev` running)
	cd frontend && npx playwright test

lint:
	cd frontend && npx eslint src && npx tsc --noEmit

build:
	cd frontend && npm run build

clean:
	rm -rf storage frontend/.next
