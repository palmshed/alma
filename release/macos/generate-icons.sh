#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CANONICAL_SVG="$PROJECT_ROOT/frontend/src/logo.svg"
OUTPUT_PNG="$PROJECT_ROOT/frontend/public/logo-1024.png"
APPICON_DIR="$PROJECT_ROOT/swift/Sources/Alma/Assets.xcassets/AppIcon.appiconset"

echo "=== Generating macOS icon formats from $CANONICAL_SVG ==="

if [ ! -f "$CANONICAL_SVG" ]; then
    echo "Error: canonical icon not found at $CANONICAL_SVG"
    exit 1
fi

# 1. Render 1024x1024 PNG from the SVG
rsvg-convert -w 1024 -h 1024 "$CANONICAL_SVG" -o "$OUTPUT_PNG"

# 2. macOS icon sizes
ICON_SPECS=(
  "16@1x:16"
  "16@2x:32"
  "32@1x:32"
  "32@2x:64"
  "128@1x:128"
  "128@2x:256"
  "256@1x:256"
  "256@2x:512"
  "512@1x:512"
  "512@2x:1024"
)

mkdir -p "$APPICON_DIR"

build_contents_json() {
    local dir="$1"
    local json_file="$dir/Contents.json"
    > "$json_file"
    echo "{" >> "$json_file"
    echo '  "images" : [' >> "$json_file"
    local first=true
    for spec in "${ICON_SPECS[@]}"; do
        key="${spec%%:*}"
        size="${key%%@*}"
        scale_suffix="${key##*@}"
        filename="icon_${size}x${size}@${scale_suffix}.png"
        if [ "$first" = false ]; then
            echo "    }," >> "$json_file"
        fi
        cat >> "$json_file" <<ENDCAT
    {
      "filename" : "$filename",
      "idiom" : "mac",
      "scale" : "${scale_suffix}",
      "size" : "${size}x${size}"
ENDCAT
        first=false
    done
    echo "    }" >> "$json_file"
    echo '  ],' >> "$json_file"
    echo '  "info" : {' >> "$json_file"
    echo '    "author" : "generate-icons.sh",' >> "$json_file"
    echo '    "version" : 1' >> "$json_file"
    echo '  }' >> "$json_file"
    echo "}" >> "$json_file"
}

for spec in "${ICON_SPECS[@]}"; do
    key="${spec%%:*}"
    pixels="${spec##*:}"
    size="${key%%@*}"
    scale_suffix="${key##*@}"
    filename="icon_${size}x${size}@${scale_suffix}.png"
    sips -z "$pixels" "$pixels" "$OUTPUT_PNG" --out "$APPICON_DIR/$filename" &>/dev/null
done

build_contents_json "$APPICON_DIR"

echo "=== Done ==="
echo "  Source: $CANONICAL_SVG"
echo "  AppIcon: $APPICON_DIR"
