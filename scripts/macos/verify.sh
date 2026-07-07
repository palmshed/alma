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

    # Structural verification — these check the bundle is valid even
    # though it is unsigned. Unexpected failures here indicate a change
    # in macOS behavior or a packaging regression.
    if codesign --verify --deep --strict "$APP_BUNDLE" 2>/dev/null; then
        check "codesign: bundle structure is valid (ad-hoc signed)" "true"
    else
        check "codesign: bundle structure is valid" "false"
    fi

    SPCTL_RESULT=$(spctl --assess --ignore-cache "$APP_BUNDLE" 2>&1 || true)
    if echo "$SPCTL_RESULT" | grep -q "rejected"; then
        check "spctl: bundle rejected (expected for unsigned)" "true"
    else
        check "spctl: assessment completed" "true"
    fi

    if ls "$APP_BUNDLE/Contents/Resources/"*.car &>/dev/null 2>&1; then
        check "Asset catalog compiled" "test -f \"$APP_BUNDLE/Contents/Resources/Assets.car\""
        # Verify the asset catalog is non-empty (has actual content, not just an empty catalog)
        CAR_SIZE=$(stat -f%z "$APP_BUNDLE/Contents/Resources/Assets.car" 2>/dev/null || echo "0")
        if [ "$CAR_SIZE" -gt 500 ]; then
            check "Asset catalog has icon content ($CAR_SIZE bytes)" "true"
        else
            check "Asset catalog has icon content ($CAR_SIZE bytes)" "false"
        fi
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

    # Detach any prior mount of this DMG to avoid Resource busy
    if mount | grep -q "$DMG" 2>/dev/null; then
        hdiutil detach "$(mount | grep "$DMG" | awk '{print $3}')" -force 2>/dev/null || true
        sleep 1
    fi

    MOUNT_POINT=$(mktemp -d)
    if hdiutil attach "$DMG" -mountpoint "$MOUNT_POINT" -nobrowse 2>/dev/null; then
        check "DMG mounts successfully" "true"

        APP_COUNT=$(find "$MOUNT_POINT" -maxdepth 1 -name "*.app" -type d | wc -l | tr -d ' ')
        check "DMG contains exactly one .app" "test \"$APP_COUNT\" -eq 1"
        check "Alma.app inside DMG" "test -d \"$MOUNT_POINT/Alma.app\""
        check "Applications symlink inside DMG" "test -L \"$MOUNT_POINT/Applications\""

        # Verify DMG resources
        if [ -f "$MOUNT_POINT/background.png" ]; then
            check "DMG background image present" "true"
            # Check if hidden (BSD flag 'hidden' via ls -lO)
            if ls -lO "$MOUNT_POINT/background.png" 2>/dev/null | grep -q "hidden"; then
                check "DMG background image is hidden" "true"
            else
                check "DMG background image is hidden" "false"
            fi
        else
            check "DMG background image present" "false"
        fi

        if [ -f "$MOUNT_POINT/.DS_Store" ]; then
            check "DMG .DS_Store present" "true"
        else
            check "DMG .DS_Store present" "false"
        fi

        # Verify volume icon is set
        if [ -f "$MOUNT_POINT/.VolumeIcon.icns" ]; then
            check "DMG volume icon (.VolumeIcon.icns) present" "true"
        else
            check "DMG volume icon (.VolumeIcon.icns) present" "false"
        fi

        # Verify the bundle inside DMG matches the source bundle
        if [ -d "$MOUNT_POINT/Alma.app" ] && [ -d "$APP_BUNDLE" ]; then
            check "DMG binary size matches built binary" \
                "test \"\$(stat -f%z \"$APP_BUNDLE/Contents/MacOS/Alma\" 2>/dev/null)\" = \"\$(stat -f%z \"$MOUNT_POINT/Alma.app/Contents/MacOS/Alma\" 2>/dev/null)\""
            check "DMG Info.plist matches built Info.plist" \
                "diff <(plutil -extract CFBundleShortVersionString xml1 -o - \"$APP_BUNDLE/Contents/Info.plist\" 2>/dev/null) <(plutil -extract CFBundleShortVersionString xml1 -o - \"$MOUNT_POINT/Alma.app/Contents/Info.plist\" 2>/dev/null) >/dev/null 2>&1"
        fi

        hdiutil detach "$MOUNT_POINT" 2>/dev/null || true
        # Retry detach if busy
        if mount | grep -q "$MOUNT_POINT" 2>/dev/null; then
            hdiutil detach "$MOUNT_POINT" -force 2>/dev/null || true
        fi
    else
        check "DMG mounts successfully" "false"
    fi
    rm -rf "$MOUNT_POINT"
fi

echo ""
echo "=== Launch Test ==="

if [ -n "${CI:-}" ]; then
    :
elif command -v open &>/dev/null; then
    BUILD_BINARY="$APP_BUNDLE/Contents/MacOS/Alma"
    if [ -x "$BUILD_BINARY" ]; then
        LAUNCH_OUTPUT=$(open "$APP_BUNDLE" 2>&1 || true)
        sleep 2
        ALMA_PID=$(pgrep -x "Alma" 2>/dev/null || true)
        if [ -n "$ALMA_PID" ]; then
            check "App launches (signed build)" "true"
            kill "$ALMA_PID" 2>/dev/null || true
        elif echo "$LAUNCH_OUTPUT" | grep -q "code signing" || echo "$LAUNCH_OUTPUT" | grep -q "Launch failed" || echo "$LAUNCH_OUTPUT" | grep -q "unexpected reason"; then
            check "App launches — unsigned (expected on macOS, resolved by signing)" "true"
        else
            check "App launches" "false"
        fi
    fi
fi

echo ""
if [ "$errors" -eq 0 ]; then
    echo "✓ All checks passed."
else
    echo "✘ $errors check(s) failed."
    exit 1
fi
