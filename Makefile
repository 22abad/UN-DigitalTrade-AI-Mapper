.PHONY: dev dev-backend dev-frontend install install-frontend test db

dev:
	@echo "Starting backend and frontend..."
	@trap 'kill 0' EXIT; \
		uvicorn main:app --reload --port 8000 --app-dir ai-service & \
		cd rdtii-frontend && npx vite --host 0.0.0.0 & \
		wait

dev-backend:
	uvicorn main:app --reload --port 8000 --app-dir ai-service

dev-frontend:
	cd rdtii-frontend && npx vite --host 0.0.0.0

install:
	cd ai-service && pip install -r requirements.txt && playwright install chromium

install-frontend:
	cd rdtii-frontend && npm install

test:
	cd ai-service && python -m pytest

db:
	docker compose up postgres redis
