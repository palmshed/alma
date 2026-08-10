#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUTPUT_DIR="$PROJECT_ROOT/output"
APP_BUNDLE="$OUTPUT_DIR/Alma.app"
DMG_RESOURCES="$(dirname "$0")/dmg-resources"

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

PYENV_ROOT="$PROJECT_ROOT/.build-dsstore"
rm -rf "$PYENV_ROOT"
python3 -m venv "$PYENV_ROOT"
"$PYENV_ROOT/bin/pip" install ds_store mac_alias -q 2>/dev/null
# Patch mac_alias to use 64-bit Q format for CNID path entries.
# APFS inode numbers exceed 32-bit range on macOS 15;
# the shipped v2.2.3 uses I (32-bit) and struct.pack fails.
# Use Python to discover and patch the installed path — avoids
# brittle globs across Python releases and shell escaping issues.
"$PYENV_ROOT/bin/python3" -c "
import mac_alias, pathlib, shutil
pkg_dir = pathlib.Path(mac_alias.__file__).resolve().parent
# Wipe any compiled bytecode so Python recompiles from patched source
for cache in pkg_dir.glob('__pycache__'):
    shutil.rmtree(cache)
    print(f'  Cleared cache: {cache}')
patched = 0
for f in pkg_dir.glob('*.py'):
    content = f.read_text()
    if '>%uI\"' not in content:
        continue
    content = content.replace('>%uI\"', '>%uQ\"')
    content = content.replace('length // 4', 'length // 8')
    f.write_text(content)
    print(f'  Patched: {f}')
    patched += 1
if not patched:
    print('  No files needed patching')
"

STAGING_DIR="$OUTPUT_DIR/.staging-$$"
RW_IMAGE="$OUTPUT_DIR/.Alma-$VERSION-rw.dmg"
DMG_PATH="$OUTPUT_DIR/Alma-$VERSION.dmg"
VOLUME_NAME="Alma"
trap 'rm -rf "$STAGING_DIR" "$RW_IMAGE"' EXIT

# Stage the bundle, Applications symlink, and DMG resources
mkdir -p "$STAGING_DIR"
cp -R "$APP_BUNDLE" "$STAGING_DIR/Alma.app"
ln -s /Applications "$STAGING_DIR/Applications"

if [ -f "$DMG_RESOURCES/background.png" ]; then
    cp "$DMG_RESOURCES/background.png" "$STAGING_DIR/background.png"
    echo "  Background: staged"
fi

# Generate a pristine .DS_Store that includes background image bookmark,
# window settings, and icon positions — no AppleScript required.
"$PYENV_ROOT/bin/python3" "$DMG_RESOURCES/../generate-dsstore.py" "$STAGING_DIR"
echo "  .DS_Store: generated"

if [ -f "$STAGING_DIR/background.png" ]; then
    SetFile -a V "$STAGING_DIR/background.png" 2>/dev/null || true
fi

# Step 1: Read-write DMG from staging
rm -f "$RW_IMAGE"
hdiutil create \
    -volname "$VOLUME_NAME" \
    -srcfolder "$STAGING_DIR" \
    -ov \
    -format UDRW \
    "$RW_IMAGE" \
    2>/dev/null

# Step 2: Mount to embed volume icon
MOUNT_POINT="/Volumes/$VOLUME_NAME"
if [ -d "$MOUNT_POINT" ]; then
    hdiutil detach "$MOUNT_POINT" -force 2>/dev/null || true
    sleep 1
fi
if hdiutil attach "$RW_IMAGE" -mountpoint "$MOUNT_POINT" 2>/dev/null; then
    if [ -f "$OUTPUT_DIR/Alma.icns" ]; then
        cp "$OUTPUT_DIR/Alma.icns" "$MOUNT_POINT/.VolumeIcon.icns"
        SetFile -a C "$MOUNT_POINT" 2>/dev/null || true
        echo "  Volume icon: embedded"
    fi
    hdiutil detach "$MOUNT_POINT" 2>/dev/null || true
fi
rm -rf "$MOUNT_POINT"

# Step 3: Convert to compressed UDZO
rm -f "$DMG_PATH"
hdiutil convert "$RW_IMAGE" \
    -format UDZO \
    -o "$DMG_PATH" \
    2>/dev/null

echo "=== Alma.dmg packaged at $DMG_PATH ==="
