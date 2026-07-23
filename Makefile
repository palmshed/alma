# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
#
# This Makefile provides commands for linting, formatting, testing,
# and running the Gemini AI Search application.

.PHONY: lint format test run

lint:
	uv run ruff check .

format:
	uv run black .

test:
	GEMINI_API_KEY=dummy PYTHONPATH=backend uv run pytest backend/tests/

run:
	uv run python backend/app.py

run-static:
	uv run python backend/static_app.py

verify-e2e:
	uv run python -m backend.verify e2e

run-all:
	@echo "Starting both interfaces..."
	uv run python backend/static_app.py &
	sleep 2
	uv run python backend/app.py &
	@echo "React interface: http://localhost:8000"
	@echo "Static interface: http://localhost:5000"
	@echo "Press Ctrl+C to stop all services"
	wait
