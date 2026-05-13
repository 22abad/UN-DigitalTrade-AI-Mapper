#!/usr/bin/env bash
# Run this script from the project root:
#   cd UN-DigitalTrade-AI-Mapper && bash scripts/setup-and-run.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== SENTINEL — Docker Environment Setup ==="

# 1. Create .env from template if not exists
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example ..."
    cp .env.example .env
    echo ">>> Edit .env to set your API keys, then re-run this script."
    exit 1
fi

# 2. Start everything
echo "Building and starting all services..."
docker compose up -d --build

echo ""
echo "=== All services started ==="
echo "  Frontend:  http://localhost:5173"
echo "  API:       http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "Useful commands:"
echo "  docker compose logs -f      # follow all logs"
echo "  docker compose down         # stop everything"
echo "  docker compose restart      # restart services"
