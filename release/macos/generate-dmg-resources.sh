#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RESOURCES_DIR="$(dirname "$0")/dmg-resources"

echo "=== Generating DMG resources ==="

# Render background at 2x for retina
INPUT_SVG="$RESOURCES_DIR/background.svg"
OUTPUT_PNG="$RESOURCES_DIR/background.png"

if [ ! -f "$INPUT_SVG" ]; then
    echo "Error: $INPUT_SVG not found"
    exit 1
fi

# Render at 2x (1320x840) so Finder uses the right resolution on retina displays
rsvg-convert -w 1320 -h 840 "$INPUT_SVG" -o "$OUTPUT_PNG"

echo "  Background: $OUTPUT_PNG ($(stat -f%z "$OUTPUT_PNG") bytes)"

echo "=== Done ==="
