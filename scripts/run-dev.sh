#!/bin/bash

# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

# Alma Development Services Manager
# Usage: ./run-dev.sh [all|backend|frontend|static|go|interfaces]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PYTHON=${PYTHON:-"$REPO_ROOT/.venv/bin/python"}
SERVICE=${1:-"help"}

show_help() {
    echo "Alma Development Services Manager"
    echo "================================="
    echo ""
    echo "Usage: ./run-dev.sh [SERVICE]"
    echo ""
    echo "Supported targets:"
    echo "  all         - Start all services"
    echo "  backend     - Start the Flask API (port 8000)"
    echo "  frontend    - Start the React development server (port 3000)"
    echo "  static      - Start the static web interface (port 5001)"
    echo "  go          - Start the Go service (port 8080)"
    echo "  interfaces  - Start the backend and static interface"
    echo "  help        - Show this help message"
    echo ""
}

check_env() {
    local env_file="$REPO_ROOT/.env"
    if [ ! -f "$env_file" ]; then
        echo "Error: .env file not found at $env_file"
        echo "Please create .env file with GEMINI_API_KEY=your-key"
        exit 1
    fi
    if ! grep -q "GEMINI_API_KEY=" "$env_file"; then
        echo "Error: GEMINI_API_KEY not found in .env file!"
        exit 1
    fi
}

free_port() {
    local port="$1"
    local pids
    pids=$(lsof -ti :"$port" 2>/dev/null)
    if [ -n "$pids" ]; then
        kill $pids 2>/dev/null
        sleep 1
    fi
}

wait_for_port() {
    local host="$1" port="$2" timeout="$3" elapsed=0
    while [ $elapsed -lt "$timeout" ]; do
        curl -s -o /dev/null "http://$host:$port" 2>/dev/null && return 0
        sleep 1
        elapsed=$((elapsed + 1))
    done
    return 1
}

find_frontend_port() {
    local timeout="$1" elapsed=0 port
    while [ $elapsed -lt "$timeout" ]; do
        for port in {3000..3010}; do
            curl -s -o /dev/null "http://localhost:$port" 2>/dev/null && echo "$port" && return 0
        done
        sleep 1
        elapsed=$((elapsed + 1))
    done
    return 1
}

start_backend() {
    free_port 8000
    "$PYTHON" "$REPO_ROOT/backend/app.py" &
    BACKEND_PID=$!
    if wait_for_port "127.0.0.1" 8000 10; then
        echo "✓ Backend    http://localhost:8000"
    else
        echo "✗ Backend    failed to start on port 8000"
        exit 1
    fi
}

start_frontend() {
    local frontend_dir="$REPO_ROOT/frontend"
    if [ ! -d "$frontend_dir" ]; then
        echo "✗ Frontend   directory not found at $frontend_dir"
        exit 1
    fi
    for port in {3000..3010}; do free_port "$port"; done
    (
        cd "$frontend_dir" || exit 1
        npm start
    ) &
    FRONTEND_PID=$!
    local port
    port=$(find_frontend_port 15)
    if [ -n "$port" ]; then
        echo "✓ Frontend   http://localhost:$port"
    else
        echo "✗ Frontend   failed to start"
        exit 1
    fi
}

start_static() {
    free_port 5001
    "$PYTHON" "$REPO_ROOT/backend/static_app.py" &
    STATIC_PID=$!
    if wait_for_port "127.0.0.1" 5001 10; then
        echo "✓ Static     http://localhost:5001"
    else
        echo "✗ Static     failed to start on port 5001"
        exit 1
    fi
}

start_go() {
    if ! command -v go &> /dev/null || [ ! -f "$REPO_ROOT/go/src/main.go" ]; then
        return 0
    fi
    free_port 8080
    (
        cd "$REPO_ROOT/go/src" || exit 1
        go run main.go
    ) &
    GO_PID=$!
    if wait_for_port "127.0.0.1" 8080 10; then
        echo "✓ Go         http://localhost:8080"
    else
        echo "✗ Go         failed to start on port 8080"
        exit 1
    fi
}

cleanup() {
    echo ""
    echo "Shutting down services..."
    for pid in "$GO_PID" "$BACKEND_PID" "$FRONTEND_PID" "$STATIC_PID"; do
        [ -n "$pid" ] && kill "$pid" 2>/dev/null
    done
    wait
    exit 0
}

trap cleanup SIGINT SIGTERM

case $SERVICE in
    "interfaces")
        echo "Starting backend and static interface..."
        check_env
        start_static
        start_backend
        echo ""
        echo "All requested services are ready."
        echo "Press Ctrl+C to stop them."
        wait
        ;;

    "all")
        echo "Starting all Alma services..."
        check_env
        start_go
        start_static
        start_backend
        start_frontend
        echo ""
        echo "All requested services are ready."
        echo "Press Ctrl+C to stop them."
        wait
        ;;

    "backend")
        echo "Starting backend..."
        check_env
        start_backend
        echo ""
        echo "All requested services are ready."
        echo "Press Ctrl+C to stop them."
        wait
        ;;

    "frontend")
        echo "Starting frontend..."
        start_frontend
        echo ""
        echo "All requested services are ready."
        echo "Press Ctrl+C to stop them."
        wait
        ;;

    "static")
        echo "Starting static interface..."
        check_env
        start_static
        echo ""
        echo "All requested services are ready."
        echo "Press Ctrl+C to stop them."
        wait
        ;;

    "go")
        echo "Starting Go service..."
        start_go
        echo ""
        echo "All requested services are ready."
        echo "Press Ctrl+C to stop them."
        wait
        ;;

    "help"|*)
        show_help
        ;;
esac
