#!/bin/bash

# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT

# Setup script for Gemini AI Search
# Installs all required tools and dependencies

set -e

echo "Setting up Gemini AI Search..."

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install required tools
echo "Installing tools..."
brew install uv node typescript go

# Install uv (if not already)
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Set up Python environment
echo "Setting up Python environment..."
uv venv
source .venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
uv sync

# Compile TypeScript
echo "Compiling TypeScript..."
npx tsc --project deploy/static/static/ts

# Set up Go service (optional)
if command -v go &> /dev/null && [ -f go/src/main.go ]; then
    echo "Starting Go text processing service..."
    cd go/src
    go run main.go &
    GO_PID=$!
    cd ../..

    # Wait a moment for Go service to start
    sleep 2

    # Test Go service
    if curl -s http://localhost:8080/process -d "text=test" > /dev/null; then
        echo "Go service started successfully on port 8080"
    else
        echo "Warning: Go service may not have started properly"
    fi
else
    echo "Go not available or not needed. API will use Python fallback for text processing."
fi

echo "Setup complete."
echo "Services running:"
echo "  - Go text processing service: http://localhost:8080"
echo "  - Flask API: will start on http://localhost:5000"
echo ""
echo "Run: source .venv/bin/activate && make run"
echo "For development: make lint, make format, make test"
