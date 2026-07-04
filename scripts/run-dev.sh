#!/bin/bash

# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

# Vortai Development Services Manager
# Usage: ./run-dev.sh [all|backend|frontend|go]

SERVICE=${1:-"help"}

show_help() {
    echo "🚀 Vortai Development Services Manager"
    echo "======================================="
    echo ""
    echo "Usage: ./run-dev.sh [SERVICE]"
    echo ""
    echo "Services:"
    echo "  all         - Start all services (backend + frontend + go)"
    echo "  backend     - Start React backend only (port 8000)"
    echo "  static      - Start static web interface only (port 5001)"
    echo "  frontend    - Start React frontend only (port 3000)"
    echo "  go          - Start Go text processing service only (port 8080)"
    echo "  interfaces  - Start both web interfaces (React + Static)"
    echo "  help        - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run-dev.sh all         # Start everything"
    echo "  ./run-dev.sh interfaces  # Start both web UIs"
    echo "  ./run-dev.sh backend     # React backend development"
    echo "  ./run-dev.sh static      # Static web interface"
    echo ""
}

check_env() {
    if [ ! -f ".env" ]; then
        echo "❌ Error: .env file not found!"
        echo "Please create .env file with GEMINI_API_KEY=your-key"
        exit 1
    fi

    if ! grep -q "GEMINI_API_KEY=" .env; then
        echo "❌ Error: GEMINI_API_KEY not found in .env file!"
        exit 1
    fi

    echo "✅ Environment check passed"
}

start_go() {
    if command -v go &> /dev/null && [ -f go/src/main.go ]; then
        echo "🐹 Starting Go text processing service..."
        cd go/src
        go run main.go &
        GO_PID=$!
        cd ../..
        echo "⏳ Waiting for Go service to start..."
        sleep 2
        echo "✅ Go Service: http://localhost:8080"
    else
        echo "🐹 Go service not available. API will use Python fallback for text processing."
    fi
}

start_backend() {
    echo "🔧 Starting React backend..."
    uv run python app.py &
    BACKEND_PID=$!
    echo "⏳ Waiting for backend to start..."
    sleep 3
    echo "✅ React Backend: http://localhost:8000"
}

start_static() {
    echo "🌐 Starting static web interface..."
    uv run python static_app.py &
    STATIC_PID=$!
    echo "⏳ Waiting for static interface to start..."
    sleep 2
    echo "✅ Static Interface: http://localhost:5001"
}

start_frontend() {
    echo "🎨 Starting React frontend..."
    cd frontend
    npm start &
    FRONTEND_PID=$!
    cd ..
    echo "✅ Frontend: http://localhost:3000"
}

cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $GO_PID $BACKEND_PID $FRONTEND_PID $STATIC_PID 2>/dev/null
    exit 0
}

# Main service handling logic
case $SERVICE in
    "interfaces")
        echo "🌐 Starting Both Web Interfaces"
        echo "==============================="
        check_env
        trap cleanup SIGINT SIGTERM
        start_static && start_backend
        echo ""
        echo "✅ Both interfaces started!"
        echo "🌐 Static Interface: http://localhost:5001"
        echo "🔧 React Interface: http://localhost:8000"
        echo ""
        echo "Press Ctrl+C to stop interfaces"
        wait
        ;;

    "all")
        echo "🚀 Starting ALL Vortai Services"
        echo "==============================="
        check_env
        trap cleanup SIGINT SIGTERM
        start_go && start_static && start_backend && start_frontend
        echo ""
        echo "✅ All services started!"
        echo "🐹 Go Service: http://localhost:8080"
        echo "🌐 Static Interface: http://localhost:5001"
        echo "🔧 React Backend: http://localhost:8000"
        echo "📱 React Frontend: http://localhost:3000"
        echo ""
        echo "Press Ctrl+C to stop all services"
        wait
        ;;

    "backend")
        echo "🔧 Starting React Backend Only"
        echo "=============================="
        check_env
        trap cleanup SIGINT SIGTERM
        start_backend
        echo ""
        echo "Press Ctrl+C to stop backend"
        wait
        ;;

    "static")
        echo "🌐 Starting Static Web Interface Only"
        echo "====================================="
        check_env
        trap cleanup SIGINT SIGTERM
        start_static
        echo ""
        echo "Press Ctrl+C to stop static interface"
        wait
        ;;

    "frontend")
        echo "🎨 Starting React Frontend Only"
        echo "==============================="
        trap cleanup SIGINT SIGTERM
        start_frontend
        echo ""
        echo "Press Ctrl+C to stop frontend"
        wait
        ;;

    "go")
        echo "🐹 Starting Go Service Only"
        echo "==========================="
        trap cleanup SIGINT SIGTERM
        start_go
        echo ""
        echo "Press Ctrl+C to stop Go service"
        wait
        ;;

    "help"|*)
        show_help
        ;;
esac
