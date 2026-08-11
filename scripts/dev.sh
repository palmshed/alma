#!/bin/bash

# SPDX-FileCopyrightText: Copyright (c) 2026 Palmshed
# SPDX-License-Identifier: MIT

# Alma local development launcher.
#
# Default: React frontend (:3000) + Flask backend (:8000), the only
# services a normal Alma developer needs.
#
# Static interface and Go service are optional and never started by default.
# Press Ctrl+C to stop everything cleanly.

set -e
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-$REPO_ROOT/.venv/bin/python}"
MODE="${1:-app}"

BACKEND_PID=""
FRONTEND_PID=""
STATIC_PID=""
GO_PID=""
FRONTEND_PORT=""

show_help() {
    cat <<'EOF'
Alma development launcher

Usage:
  ./scripts/dev.sh             Start React (:3000) + backend (:8000)
  ./scripts/dev.sh static      Also start the static interface (:5001)
  ./scripts/dev.sh go          Also start the Go service (:8080)
  ./scripts/dev.sh all         Start every service
  ./scripts/dev.sh help        Show this help

The React app is served at http://localhost:3000 and requires the
backend on :8000. Static and Go services are optional and never
started by default. Press Ctrl+C to stop everything.
EOF
}

check_prereqs() {
    if [ ! -f "$REPO_ROOT/.env" ]; then
        echo "Error: .env not found at $REPO_ROOT/.env" >&2
        echo "Create it with: GEMINI_API_KEY=your-key" >&2
        exit 1
    fi
    if [ ! -x "$PYTHON" ]; then
        echo "Error: virtualenv python not found at $PYTHON" >&2
        echo "Run: uv sync" >&2
        exit 1
    fi
    if ! command -v npm >/dev/null 2>&1; then
        echo "Error: npm not found in PATH" >&2
        exit 1
    fi
}

free_port() {
    local port="$1"
    local pids
    pids=$(lsof -ti :"$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        kill $pids 2>/dev/null || true
        sleep 1
    fi
}

wait_for_backend() {
    local timeout="$1" elapsed=0
    while [ "$elapsed" -lt "$timeout" ]; do
        if curl -s -o /dev/null "http://localhost:8000/api/health" 2>/dev/null; then
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    return 1
}

wait_for_frontend() {
    local timeout="$1" elapsed=0 port
    while [ "$elapsed" -lt "$timeout" ]; do
        for port in {3000..3010}; do
            if curl -s -o /dev/null "http://localhost:$port" 2>/dev/null; then
                FRONTEND_PORT="$port"
                return 0
            fi
        done
        sleep 1
        elapsed=$((elapsed + 1))
    done
    return 1
}

start_backend() {
    free_port 8000
    "$PYTHON" "$REPO_ROOT/src/backend/app.py" &
    BACKEND_PID=$!
    if ! wait_for_backend 15; then
        echo "✗ Backend failed to become ready on :8000" >&2
        exit 1
    fi
}

start_frontend() {
    local frontend_dir="$REPO_ROOT/src/frontend"
    if [ ! -d "$frontend_dir" ]; then
        echo "✗ Frontend directory not found at $frontend_dir" >&2
        exit 1
    fi
    for port in {3000..3010}; do free_port "$port"; done
    (
        cd "$frontend_dir" || exit 1
        npm start
    ) &
    FRONTEND_PID=$!
    if ! wait_for_frontend 20; then
        echo "✗ Frontend failed to become ready on :3000" >&2
        exit 1
    fi
}

start_static() {
    if [ ! -x "$PYTHON" ]; then
        echo "⚠ Static interface skipped: python not found at $PYTHON" >&2
        return 0
    fi
    free_port 5001
    "$PYTHON" "$REPO_ROOT/src/backend/static_app.py" &
    STATIC_PID=$!
    if ! curl -s -o /dev/null --max-time 15 --retry 15 --retry-delay 1 --retry-connrefused "http://localhost:5001" 2>/dev/null; then
        echo "✗ Static interface failed to become ready on :5001" >&2
        exit 1
    fi
}

start_go() {
    if ! command -v go >/dev/null 2>&1 || [ ! -f "$REPO_ROOT/src/go/main.go" ]; then
        echo "⚠ Go service skipped: go not found or src/go/main.go missing" >&2
        return 0
    fi
    free_port 8080
    (
        cd "$REPO_ROOT/src/go" || exit 1
        go run main.go
    ) &
    GO_PID=$!
    if ! curl -s -o /dev/null --max-time 15 --retry 15 --retry-delay 1 --retry-connrefused "http://localhost:8080" 2>/dev/null; then
        echo "✗ Go service failed to become ready on :8080" >&2
        exit 1
    fi
}

print_banner() {
    echo ""
    echo "Alma"
    echo "────────────────────────"
    echo "Frontend   http://localhost:$FRONTEND_PORT"
    echo "Backend    http://localhost:8000"
    if [ -n "$STATIC_PID" ]; then
        echo "Static     http://localhost:5001"
    fi
    if [ -n "$GO_PID" ]; then
        echo "Go         http://localhost:8080"
    fi
    echo "Status     Ready"
    echo "────────────────────────"
    echo "Press Ctrl+C to stop."
}

cleanup() {
    echo ""
    echo "Shutting down Alma services..."
    for pid in "$BACKEND_PID" "$FRONTEND_PID" "$STATIC_PID" "$GO_PID"; do
        if [ -n "$pid" ]; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    for port in 3000 8000 5001 8080; do
        local pids
        pids=$(lsof -ti :"$port" 2>/dev/null || true)
        if [ -n "$pids" ]; then
            kill $pids 2>/dev/null || true
        fi
    done
    wait 2>/dev/null || true
    echo "Stopped."
    exit 0
}

trap cleanup SIGINT SIGTERM

case "$MODE" in
    "help"|"-h"|"--help")
        show_help
        exit 0
        ;;
esac

check_prereqs

case "$MODE" in
    "static")
        start_static
        start_backend
        start_frontend
        ;;
    "go")
        start_go
        start_backend
        start_frontend
        ;;
    "all")
        start_go
        start_static
        start_backend
        start_frontend
        ;;
    "app"|"")
        start_backend
        start_frontend
        ;;
    *)
        echo "Unknown mode: $MODE" >&2
        show_help
        exit 1
        ;;
esac

print_banner
wait
