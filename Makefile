.PHONY: dev dev-backend dev-frontend dev-sidecar install install-frontend install-sidecar test db migrate-sidecar image

PYTHON := /opt/homebrew/bin/python3.11

dev:
	@DB_IP=$$(docker inspect rdtii-postgres --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 2>/dev/null); \
	if [ -n "$$DB_IP" ]; then \
		sed -i '' "s|DATABASE_URL=.*|DATABASE_URL=postgresql://rdtii_user:rdtii_password@$$DB_IP:5432/rdtii|" .env; \
		echo "Postgres at $$DB_IP:5432"; \
	else \
		echo "Warning: rdtii-postgres not running, run 'make db' first"; \
	fi
	@echo "Starting backend, sidecar, and frontend..."
	@trap 'kill 0' EXIT; \
		$(PYTHON) -m uvicorn main:app --reload --port 8000 --app-dir ai-service --log-level info & \
		(export DATABASE_URL=$$(grep '^DATABASE_URL=' .env | cut -d= -f2-) && cd extract_sidecar && cargo run) & \
		(cd rdtii-frontend && npx vite --host 0.0.0.0 --force) & \
		wait

dev-backend:
	$(PYTHON) -m uvicorn main:app --reload --port 8000 --app-dir ai-service --log-level info

dev-frontend:
	cd rdtii-frontend && npx vite --host 0.0.0.0 --force

dev-sidecar:
	cd extract_sidecar && cargo run

install:
	cd ai-service && $(PYTHON) -m pip install -r requirements.txt && $(PYTHON) -m playwright install webkit

install-sidecar:
	cd extract_sidecar && cargo build --release

migrate-sidecar:
	psql "$$DATABASE_URL" -f extract_sidecar/migrations/001_extracted_documents.sql


install-frontend:
	cd rdtii-frontend && npm install

test:
	cd ai-service && $(PYTHON) -m pytest

db:
	docker compose up -d postgres redis

image:
	docker compose down
	cd rdtii-frontend && npm run build
	docker compose build --no-cache frontend extract-sidecar ai-service
	docker compose up -d
