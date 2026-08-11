# SPDX-FileCopyrightText: Copyright (c) 2026 Palmshed
# SPDX-License-Identifier: MIT
#
# This Makefile provides commands for linting, formatting, testing,
# and running the Gemini AI Search application.

.PHONY: dev lint format test verify build run run-static verify-e2e run-all

dev:
	./scripts/dev.sh

lint:
	uv run ruff check .

format:
	uv run black .

test:
	GEMINI_API_KEY=dummy PYTHONPATH=src/backend uv run pytest src/backend/tests/

verify:
	uv run python -m backend.verify e2e

build:
	cd src/frontend && npm run build

run:
	uv run python src/backend/app.py

run-static:
	uv run python src/backend/static_app.py

verify-e2e:
	uv run python -m backend.verify e2e

run-all:
	@echo "Starting both interfaces..."
	uv run python src/backend/static_app.py &
	sleep 2
	uv run python src/backend/app.py &
	@echo "React interface: http://localhost:8000"
	@echo "Static interface: http://localhost:5000"
	@echo "Press Ctrl+C to stop all services"
	wait
