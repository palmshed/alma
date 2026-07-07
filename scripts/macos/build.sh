#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT/swift"

RELEASE_TAG="${1:-}"
VERSION="${RELEASE_TAG#v}"
if [ -z "$VERSION" ]; then
    VERSION="0.0.0-dev"
fi

OUTPUT_DIR="$PROJECT_ROOT/output"
mkdir -p "$OUTPUT_DIR"

echo "=== Building Alma.app (version $VERSION) ==="

swift build -c release

APP_BUNDLE="$OUTPUT_DIR/Alma.app"
rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

cp ".build/release/Alma" "$APP_BUNDLE/Contents/MacOS/Alma"
chmod +x "$APP_BUNDLE/Contents/MacOS/Alma"

cat > "$APP_BUNDLE/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>Alma</string>
    <key>CFBundleIdentifier</key>
    <string>ai.palmshed.Alma</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>Alma</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>$VERSION</string>
    <key>CFBundleVersion</key>
    <string>$VERSION</string>
    <key>LSMinimumSystemVersion</key>
    <string>15.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

if [ -d "Sources/Alma/Assets.xcassets" ]; then
    xcrun actool "Sources/Alma/Assets.xcassets" \
        --compile "$APP_BUNDLE/Contents/Resources" \
        --platform macosx \
        --minimum-deployment-target 15.0 \
        --output-format human-readable-text \
        2>&1 | grep -v "^/* com\.apple\.actool"
fi

echo "=== Alma.app built at $APP_BUNDLE ==="
