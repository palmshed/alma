#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUTPUT_DIR="$PROJECT_ROOT/output"
APP_BUNDLE="$OUTPUT_DIR/Alma.app"

if [ ! -d "$APP_BUNDLE" ]; then
    echo "Error: Alma.app not found at $APP_BUNDLE"
    echo "Run build.sh first."
    exit 1
fi

VERSION=""
if [ -f "$APP_BUNDLE/Contents/Info.plist" ]; then
    VERSION=$(/usr/libexec/PlistBuddy -c "Print CFBundleShortVersionString" "$APP_BUNDLE/Contents/Info.plist" 2>/dev/null || echo "0.0.0")
fi

echo "=== Packaging Alma-$VERSION.dmg ==="

STAGING_DIR=$(mktemp -d)
trap 'rm -rf "$STAGING_DIR"' EXIT

cp -R "$APP_BUNDLE" "$STAGING_DIR/Alma.app"
ln -s /Applications "$STAGING_DIR/Applications"

DMG_PATH="$OUTPUT_DIR/Alma-$VERSION.dmg"
rm -f "$DMG_PATH"

hdiutil create \
    -volname "Alma $VERSION" \
    -srcfolder "$STAGING_DIR" \
    -ov \
    -format UDZO \
    "$DMG_PATH" \
    2>/dev/null

echo "=== Alma.dmg packaged at $DMG_PATH ==="
