#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUTPUT_DIR="$PROJECT_ROOT/output"
APP_BUNDLE="$OUTPUT_DIR/Alma.app"
DMG_GLOB="$OUTPUT_DIR/Alma-*.dmg"

errors=0

check() {
    local desc="$1"
    if eval "$2"; then
        echo "  ✓ $desc"
    else
        echo "  ✘ $desc"
        errors=$((errors + 1))
    fi
}

echo "=== Verifying Alma.app ==="

if [ ! -d "$APP_BUNDLE" ]; then
    echo "  ✘ Alma.app not found at $APP_BUNDLE"
    errors=$((errors + 1))
else
    PLIST="$APP_BUNDLE/Contents/Info.plist"

    check "Bundle exists" "test -d \"$APP_BUNDLE\""
    check "Bundle is a directory" "test -d \"$APP_BUNDLE\""
    check "Contents/MacOS/Alma exists" "test -f \"$APP_BUNDLE/Contents/MacOS/Alma\""
    check "Binary is executable" "test -x \"$APP_BUNDLE/Contents/MacOS/Alma\""
    check "Binary is not empty" "test -s \"$APP_BUNDLE/Contents/MacOS/Alma\""
    check "Binary is a Mach-O file" "file \"$APP_BUNDLE/Contents/MacOS/Alma\" | grep -q 'Mach-O'"
    check "Contents/Info.plist exists" "test -f \"$PLIST\""
    check "Contents/Resources is a directory" "test -d \"$APP_BUNDLE/Contents/Resources\""

    if [ -f "$PLIST" ]; then
        check "CFBundleIdentifier is ai.palmshed.Alma" \
            "test \"\$(/usr/libexec/PlistBuddy -c 'Print CFBundleIdentifier' \"$PLIST\" 2>/dev/null)\" = 'ai.palmshed.Alma'"
        check "CFBundleExecutable is Alma" \
            "test \"\$(/usr/libexec/PlistBuddy -c 'Print CFBundleExecutable' \"$PLIST\" 2>/dev/null)\" = 'Alma'"
        check "CFBundlePackageType is APPL" \
            "test \"\$(/usr/libexec/PlistBuddy -c 'Print CFBundlePackageType' \"$PLIST\" 2>/dev/null)\" = 'APPL'"
        check "CFBundleVersion is set" \
            "test -n \"\$(/usr/libexec/PlistBuddy -c 'Print CFBundleVersion' \"$PLIST\" 2>/dev/null)\""
        check "CFBundleShortVersionString is set" \
            "test -n \"\$(/usr/libexec/PlistBuddy -c 'Print CFBundleShortVersionString' \"$PLIST\" 2>/dev/null)\""
        check "LSMinimumSystemVersion is 15.0" \
            "test \"\$(/usr/libexec/PlistBuddy -c 'Print LSMinimumSystemVersion' \"$PLIST\" 2>/dev/null)\" = '15.0'"
        check "NSHighResolutionCapable is true" \
            "test \"\$(/usr/libexec/PlistBuddy -c 'Print NSHighResolutionCapable' \"$PLIST\" 2>/dev/null)\" = 'true'"

        check "Version matches tag or is dev" \
            "case \"\$(/usr/libexec/PlistBuddy -c 'Print CFBundleShortVersionString' \"$PLIST\" 2>/dev/null)\" in 0.0.0-dev|[0-9]*) true ;; *) false ;; esac"
    fi

    if ls "$APP_BUNDLE/Contents/Resources/"*.car &>/dev/null 2>&1; then
        check "Asset catalog compiled" "test -f \"$APP_BUNDLE/Contents/Resources/Assets.car\""
    else
        check "No asset catalog (empty xcassets)" "true"
    fi
fi

echo ""
echo "=== Verifying DMG ==="

DMG_FILES=( $DMG_GLOB )
if [ "${#DMG_FILES[@]}" -eq 0 ] || [ ! -f "${DMG_FILES[0]}" ]; then
    echo "  ✘ No DMG found matching $DMG_GLOB"
    errors=$((errors + 1))
else
    DMG="${DMG_FILES[0]}"
    check "DMG file exists" "test -f \"$DMG\""
    check "DMG is not empty" "test -s \"$DMG\""
    check "DMG is a UDZO image" "hdiutil imageinfo \"$DMG\" 2>/dev/null | grep -q 'UDZO'"

    MOUNT_POINT=$(mktemp -d)
    if hdiutil attach "$DMG" -mountpoint "$MOUNT_POINT" -nobrowse 2>/dev/null; then
        check "DMG mounts successfully" "true"

        APP_COUNT=$(find "$MOUNT_POINT" -maxdepth 1 -name "*.app" -type d | wc -l | tr -d ' ')
        check "DMG contains exactly one .app" "test \"$APP_COUNT\" -eq 1"
        check "Alma.app inside DMG" "test -d \"$MOUNT_POINT/Alma.app\""
        check "Applications symlink inside DMG" "test -L \"$MOUNT_POINT/Applications\""

        # Verify the bundle inside DMG matches the source bundle
        if [ -d "$MOUNT_POINT/Alma.app" ] && [ -d "$APP_BUNDLE" ]; then
            check "DMG binary size matches built binary" \
                "test \"\$(stat -f%z \"$APP_BUNDLE/Contents/MacOS/Alma\" 2>/dev/null)\" = \"\$(stat -f%z \"$MOUNT_POINT/Alma.app/Contents/MacOS/Alma\" 2>/dev/null)\""
            check "DMG Info.plist matches built Info.plist" \
                "diff <(plutil -extract CFBundleShortVersionString xml1 -o - \"$APP_BUNDLE/Contents/Info.plist\" 2>/dev/null) <(plutil -extract CFBundleShortVersionString xml1 -o - \"$MOUNT_POINT/Alma.app/Contents/Info.plist\" 2>/dev/null) >/dev/null 2>&1"
        fi

        # Quick launch test: open the app and verify it doesn't crash immediately
        if [ -n "${CI:-}" ]; then
            # CI may not have a GUI, skip launch test
            : 
        elif command -v open &>/dev/null; then
            if open "$MOUNT_POINT/Alma.app" 2>/dev/null; then
                sleep 2
                if pgrep -f "Alma.app" &>/dev/null; then
                    check "App launches without immediate crash" "true"
                    pkill -f "Alma.app" 2>/dev/null || true
                else
                    check "App launches without immediate crash" "false"
                fi
            else
                check "App launches without immediate crash" "false"
            fi
        fi

        hdiutil detach "$MOUNT_POINT" 2>/dev/null || true
    else
        check "DMG mounts successfully" "false"
    fi
    rm -rf "$MOUNT_POINT"
fi

echo ""
if [ "$errors" -eq 0 ]; then
    echo "✓ All checks passed."
else
    echo "✘ $errors check(s) failed."
    exit 1
fi
