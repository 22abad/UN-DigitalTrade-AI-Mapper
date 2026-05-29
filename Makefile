.PHONY: dev dev-backend dev-frontend dev-sidecar install install-frontend install-sidecar test db migrate-sidecar

dev:
	@echo "Starting backend, sidecar, and frontend..."
	@trap 'kill 0' EXIT; \
		python3 -m uvicorn main:app --reload --port 8000 --app-dir ai-service & \
		(cd extract_sidecar && cargo run) & \
		(cd rdtii-frontend && npx vite --host 0.0.0.0 --force) & \
		wait

dev-backend:
	python3 -m uvicorn main:app --reload --port 8000 --app-dir ai-service

dev-frontend:
	cd rdtii-frontend && npx vite --host 0.0.0.0 --force

dev-sidecar:
	cd extract_sidecar && cargo run

install:
	cd ai-service && pip3 install -r requirements.txt && playwright install chromium

install-sidecar:
	cd extract_sidecar && cargo build --release

migrate-sidecar:
	psql "$$DATABASE_URL" -f extract_sidecar/migrations/001_extracted_documents.sql


install-frontend:
	cd rdtii-frontend && npm install

test:
	cd ai-service && python -m pytest

db:
	docker compose up -d postgres redis

restart:
	docker compose down
	docker compose up -d postgres redis
	docker compose up -d
