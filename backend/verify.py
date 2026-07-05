"""
End-to-end verification CLI for the Alma platform.

Runs platform (local), application (API), and UI (frontend) checks.

Usage:
    python -m backend.verify                          # platform + application checks
    python -m backend.verify --json
    python -m backend.verify --platform
    python -m backend.verify --application
    python -m backend.verify mail
    python -m backend.verify storage auth
    python -m backend.verify ui                       # UI verification
    python -m backend.verify ui --static              # static frontend analysis only
    python -m backend.verify ui --capabilities        # backend capability probe only
    python -m backend.verify ui --json --output report.json
"""

import argparse
import json
import os
import struct
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

REQUIRED_ENV_KEYS: list[str] = []
_TIMEOUT: int = 60

INFRASTRUCTURE = "infrastructure"
QUOTA = "quota"


# ── Platform checks (local) ──────────────────────────────────────────


def check_mail() -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "name": "mail",
        "label": "Mail",
        "group": "platform",
        "status": "fail",
    }
    t0 = time.time()
    try:
        from services import platform

        h = platform.mail.health()
        elapsed = round(time.time() - t0, 1)
        result["latency"] = elapsed
        if not h.config_valid:
            result["error"] = f"config invalid: {h.config_errors}"
            return result
        result["status"] = "pass"
        result["details"] = {
            "provider": h.provider,
            "templates": h.template_count,
            "queue": "running" if h.queue_running else "stopped",
        }
    except Exception as exc:
        elapsed = round(time.time() - t0, 1)
        result["latency"] = elapsed
        result["error"] = str(exc)
    return result


def check_auth() -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "name": "auth",
        "label": "Auth",
        "group": "platform",
        "status": "fail",
    }
    t0 = time.time()
    try:
        from services import platform

        h = platform.auth.health()
        elapsed = round(time.time() - t0, 1)
        result["latency"] = elapsed
        if not h.config_valid:
            result["error"] = f"config invalid: {h.config_errors}"
            return result
        result["status"] = "pass"
        result["details"] = {"provider": h.provider}
    except Exception as exc:
        elapsed = round(time.time() - t0, 1)
        result["latency"] = elapsed
        result["error"] = str(exc)
    return result


def check_storage() -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "name": "storage",
        "label": "Storage",
        "group": "platform",
        "status": "fail",
    }
    t0 = time.time()
    try:
        from services import platform

        h = platform.storage.health()
        elapsed = round(time.time() - t0, 1)
        result["latency"] = elapsed
        if not h.config_valid:
            result["error"] = f"config invalid: {h.config_errors}"
            return result
        result["status"] = "pass"
        result["details"] = {
            "provider": h.provider,
            "bucket": h.bucket,
            "healthy": h.healthy,
        }
    except Exception as exc:
        elapsed = round(time.time() - t0, 1)
        result["latency"] = elapsed
        result["error"] = str(exc)
    return result


def check_notifications() -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "name": "notifications",
        "label": "Notifications",
        "group": "platform",
        "status": "fail",
    }
    t0 = time.time()
    try:
        from services import platform

        h = platform.notifications.health()
        elapsed = round(time.time() - t0, 1)
        result["latency"] = elapsed
        if not h.enabled:
            result["warning"] = "notifications are disabled"
        result["status"] = "pass"
        result["details"] = {"channels": h.channels}
    except Exception as exc:
        elapsed = round(time.time() - t0, 1)
        result["latency"] = elapsed
        result["error"] = str(exc)
    return result


# ── Application checks (API) ─────────────────────────────────────────


def get_config() -> Dict[str, str]:
    missing = [k for k in REQUIRED_ENV_KEYS if not os.environ.get(k)]
    if missing:
        print(f"Missing required env vars: {', '.join(missing)}")
        sys.exit(1)
    base_url = os.environ.get("ALMA_BASE_URL", "http://localhost:5000").rstrip("/")
    return {
        "base_url": base_url,
        "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
        "google_cloud_project": os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
        "google_cloud_location": os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
    }


def api_post(
    url: str, payload: dict, timeout: Optional[int] = None
) -> Tuple[int, Any, Optional[Dict[str, str]]]:
    if timeout is None:
        timeout = _TIMEOUT
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        body = resp.read()
        content_type = resp.headers.get("Content-Type", "")
        headers = dict(resp.headers)
        if "application/json" in content_type:
            return resp.status, json.loads(body.decode("utf-8")), headers
        return resp.status, body, headers
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            parsed = json.loads(body.decode("utf-8"))
            return e.code, parsed, dict(e.headers)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return e.code, body.decode("utf-8", errors="replace"), dict(e.headers)
    except urllib.error.URLError as e:
        return 0, f"Connection error: {e.reason}", None


def api_get(
    url: str, timeout: Optional[int] = None
) -> Tuple[int, Any, Optional[Dict[str, str]]]:
    if timeout is None:
        timeout = _TIMEOUT
    req = urllib.request.Request(url, method="GET")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        body = resp.read()
        content_type = resp.headers.get("Content-Type", "")
        headers = dict(resp.headers)
        if "application/json" in content_type:
            return resp.status, json.loads(body.decode("utf-8")), headers
        return resp.status, body, headers
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            parsed = json.loads(body.decode("utf-8"))
            return e.code, parsed, dict(e.headers)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return e.code, body.decode("utf-8", errors="replace"), dict(e.headers)
    except urllib.error.URLError as e:
        return 0, f"Connection error: {e.reason}", None


def parse_image_dimensions(data: bytes) -> Tuple[int, int]:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        if len(data) >= 24:
            w, h = struct.unpack(">II", data[16:24])
            return w, h
    elif data[:2] == b"\xff\xd8":
        pos = 2
        while pos < len(data) - 1:
            if data[pos] != 0xFF:
                break
            marker = data[pos + 1]
            if marker == 0xC0 or marker == 0xC1 or marker == 0xC2:
                if pos + 9 < len(data):
                    h, w = struct.unpack(">HH", data[pos + 5 : pos + 9])
                    return w, h
                break
            if marker == 0xD9:
                break
            if (
                marker == 0xD0
                or marker == 0xD1
                or marker == 0xD2
                or marker == 0xD3
                or marker == 0xD4
                or marker == 0xD5
                or marker == 0xD6
                or marker == 0xD7
            ):
                pos += 2
            else:
                if pos + 3 < len(data):
                    length = struct.unpack(">H", data[pos + 2 : pos + 4])[0]
                    pos += 2 + length
                else:
                    break
    elif data[:6] in (b"GIF87a", b"GIF89a"):
        if len(data) >= 10:
            w, h = struct.unpack("<HH", data[6:10])
            return w, h
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        webp_data = data[12:]
        if len(webp_data) >= 4:
            if webp_data[:4] == b"VP8 ":
                if len(webp_data) >= 14:
                    w = struct.unpack("<H", webp_data[10:12])[0] & 0x3FFF
                    h = struct.unpack("<H", webp_data[12:14])[0] & 0x3FFF
                    return w, h
            elif webp_data[:4] == b"VP8L":
                if len(webp_data) >= 9:
                    bits = struct.unpack("<I", webp_data[5:9])[0]
                    w = (bits & 0x3FFF) + 1
                    h = ((bits >> 14) & 0x3FFF) + 1
                    return w, h
    return 0, 0


def classify_response(status: int, body: Any) -> str:
    if status == 429:
        return QUOTA
    if isinstance(body, dict):
        provider_status = body.get("provider_status", "")
        if provider_status == "quota_exceeded":
            return QUOTA
    # Gemini API key or quota issues should not count as infrastructure failures
    if status in (400, 403, 429):
        if isinstance(body, str):
            msg = body
        elif isinstance(body, dict):
            msg = str(body.get("error", ""))
        else:
            msg = ""
        if "API key" in msg or "api_key" in msg:
            return "config"
        if "PERMISSION_DENIED" in msg or "quota" in msg:
            return QUOTA
    # Flask wraps Gemini errors in HTTP 500 — check body for Gemini error codes
    if status == 500:
        err_msg = body
        if isinstance(body, dict):
            err_msg = str(body.get("error", ""))
        if isinstance(err_msg, str):
            if "API key" in err_msg or "api_key" in err_msg:
                return "config"
            if "PERMISSION_DENIED" in err_msg:
                return "config"
            if "quota" in err_msg.lower() or "RESOURCE_EXHAUSTED" in err_msg:
                return QUOTA
    return INFRASTRUCTURE


def check_health(config: Dict[str, str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "name": "health",
        "label": "Health",
        "group": "application",
        "category": INFRASTRUCTURE,
        "status": "fail",
    }
    t0 = time.time()
    status, body, headers = api_get(f"{config['base_url']}/api/health")
    elapsed = round(time.time() - t0, 1)
    result["latency"] = elapsed

    if status != 200:
        result["error"] = f"HTTP {status}: {body}"
        return result

    try:
        if body.get("status") != "ok":
            result["error"] = f"status is '{body.get('status')}', expected 'ok'"
            return result
    except AttributeError:
        result["error"] = f"unexpected response format: {body}"
        return result

    mail = body.get("mail", {})
    if not mail.get("config_valid"):
        result["error"] = f"mail config invalid: {mail}"
        return result

    result["status"] = "pass"
    result["details"] = {
        "mail_provider": mail.get("provider"),
        "from_email": mail.get("from_email"),
    }
    return result


def check_canvas(config: Dict[str, str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "name": "canvas",
        "label": "Canvas",
        "group": "application",
        "category": INFRASTRUCTURE,
        "status": "fail",
    }
    t0 = time.time()
    status, body, headers = api_post(
        f"{config['base_url']}/api/generate",
        {"prompt": "Say hello in one word."},
    )
    elapsed = round(time.time() - t0, 1)
    result["latency"] = elapsed

    if status != 200:
        err_detail = body
        if isinstance(body, dict):
            err_detail = body.get("error", body)
        result["error"] = f"HTTP {status}: {err_detail}"
        result["category"] = classify_response(status, body)
        return result

    if not isinstance(body, dict) or "response" not in body:
        result["error"] = f"missing 'response' key in body: {body}"
        return result

    if not body["response"] or not body["response"].strip():
        result["error"] = "empty response"
        return result

    result["status"] = "pass"
    result["details"] = {"model": "gemini-2.5-flash"}
    return result


def check_thinking(config: Dict[str, str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "name": "thinking",
        "label": "Thinking",
        "group": "application",
        "category": INFRASTRUCTURE,
        "status": "fail",
    }
    t0 = time.time()
    status, body, headers = api_post(
        f"{config['base_url']}/api/generate-with-thinking",
        {"prompt": "What is 2+2? Think step by step."},
    )
    elapsed = round(time.time() - t0, 1)
    result["latency"] = elapsed

    if status != 200:
        err_detail = body
        if isinstance(body, dict):
            err_detail = body.get("error", body)
        result["error"] = f"HTTP {status}: {err_detail}"
        result["category"] = classify_response(status, body)
        return result

    if not isinstance(body, dict):
        result["error"] = f"expected JSON object, got: {body}"
        return result

    if "response" not in body:
        result["error"] = f"missing 'response' key: {body}"
        return result

    if not body.get("response", "").strip():
        result["error"] = "empty response"
        return result

    thinking = body.get("thinking_summary", [])
    details: Dict[str, Any] = {
        "has_thinking_summary": len(thinking) > 0,
        "model": "gemini-2.5-flash",
    }

    result["status"] = "pass"
    result["details"] = details
    return result


def check_web(config: Dict[str, str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "name": "web",
        "label": "Web",
        "group": "application",
        "category": INFRASTRUCTURE,
        "status": "fail",
    }
    t0 = time.time()
    status, body, headers = api_post(
        f"{config['base_url']}/api/generate-with-url-context",
        {
            "prompt": "Summarize the content at https://example.com in one sentence.",
        },
    )
    elapsed = round(time.time() - t0, 1)
    result["latency"] = elapsed

    if status != 200:
        err_detail = body
        if isinstance(body, dict):
            err_detail = body.get("error", body)
        result["error"] = f"HTTP {status}: {err_detail}"
        result["category"] = classify_response(status, body)
        return result

    if not isinstance(body, dict) or "response" not in body:
        result["error"] = f"missing 'response' key: {body}"
        return result

    if not body["response"] or not body["response"].strip():
        result["error"] = "empty response"
        return result

    result["status"] = "pass"
    result["details"] = {"url_context": "ok", "model": "gemini-2.5-flash"}
    return result


def check_images(config: Dict[str, str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "name": "images",
        "label": "Images",
        "group": "application",
        "category": INFRASTRUCTURE,
        "status": "fail",
    }
    t0 = time.time()
    status, body_data, headers = api_post(
        f"{config['base_url']}/api/generate-image",
        {"prompt": "A simple red circle on white background"},
    )
    elapsed = round(time.time() - t0, 1)
    result["latency"] = elapsed

    if status != 200:
        err_detail = body_data
        if isinstance(body_data, dict):
            err_detail = body_data.get("error", body_data)
        result["error"] = f"HTTP {status}: {err_detail}"
        result["category"] = classify_response(status, body_data)
        if isinstance(body_data, dict):
            result["details"] = {
                "provider": body_data.get("provider", "unknown"),
                "provider_status": body_data.get("provider_status", "unknown"),
            }
        return result

    if isinstance(body_data, dict):
        result["error"] = (
            f"unexpected JSON response (expected image bytes): {body_data}"
        )
        return result

    content_type = (headers or {}).get("Content-Type", "unknown")
    w, h = parse_image_dimensions(body_data)
    if w == 0 or h == 0:
        result["error"] = (
            f"could not decode image dimensions"
            f" (Content-Type: {content_type}, size: {len(body_data)} bytes)"
        )
        return result

    result["status"] = "pass"
    result["details"] = {
        "content_type": content_type,
        "size_bytes": len(body_data),
        "dimensions": f"{w}x{h}",
        "model": "gemini-2.5-flash-image",
    }
    return result


# ── Check registry ───────────────────────────────────────────────────

PLATFORM_CHECKS: Dict[str, Any] = {
    "mail": check_mail,
    "auth": check_auth,
    "storage": check_storage,
    "notifications": check_notifications,
}

APPLICATION_CHECKS: Dict[str, Any] = {
    "health": check_health,
    "canvas": check_canvas,
    "thinking": check_thinking,
    "web": check_web,
    "images": check_images,
}

ALL_CHECKS: Dict[str, Any] = {**PLATFORM_CHECKS, **APPLICATION_CHECKS}


GROUP_LABELS = {
    "platform": "Platform",
    "application": "Application",
}


def run_checks(
    config: Dict[str, str],
    names: Optional[List[str]] = None,
    groups: Optional[List[str]] = None,
) -> Dict[str, Any]:
    check_map: Dict[str, Any] = {}

    if names:
        for n in names:
            if n in ALL_CHECKS:
                check_map[n] = ALL_CHECKS[n]
    elif groups:
        for g in groups:
            if g == "platform":
                check_map.update(PLATFORM_CHECKS)
            elif g == "application":
                check_map.update(APPLICATION_CHECKS)
    else:
        check_map = ALL_CHECKS

    results = []
    for name, fn in check_map.items():
        if name in APPLICATION_CHECKS:
            results.append(fn(config))
        else:
            results.append(fn())

    platform_results = [r for r in results if r.get("group") == "platform"]
    app_results = [r for r in results if r.get("group") == "application"]

    platform_pass = all(r["status"] == "pass" for r in platform_results)
    platform_quota = all(
        r.get("category") != QUOTA or r["status"] == "pass" for r in platform_results
    )

    infra_pass = all(
        r["status"] == "pass"
        for r in app_results
        if r.get("category") == INFRASTRUCTURE
    )
    quota_pass = all(
        r["status"] == "pass" for r in app_results if r.get("category") == QUOTA
    )

    return {
        "results": results,
        "passed": sum(1 for r in results if r["status"] == "pass"),
        "total": len(results),
        "platform_pass": platform_pass,
        "platform_quota": platform_quota,
        "infrastructure_pass": infra_pass,
        "quota_pass": quota_pass,
    }


# ── Output formatting ────────────────────────────────────────────────


STATUS_LABELS: Dict[str, str] = {
    "pass": "\N{CHECK MARK}",
    "fail": "\N{CROSS MARK}",
}


def format_human(results: Dict[str, Any]) -> str:
    lines: list[str] = []

    grouped: Dict[str, list] = {}
    for r in results["results"]:
        g = r.get("group", "application")
        grouped.setdefault(g, []).append(r)

    for group_name in ("platform", "application"):
        if group_name not in grouped:
            continue
        label = GROUP_LABELS.get(group_name, group_name)
        lines.append(f"{label}")
        lines.append("")

        for r in grouped[group_name]:
            marker = STATUS_LABELS.get(r["status"], "?")
            lines.append(f"  {marker} {r['label']}")

            if r.get("warning"):
                lines.append(f"    ⚠ {r['warning']}")
            if r.get("error"):
                lines.append(f"    {r['error']}")
            if r.get("details"):
                for k, v in r["details"].items():
                    lines.append(f"    {k}: {v}")
            if r.get("latency"):
                lines.append(f"    {r['latency']} s")
            lines.append("")

    lines.append("Summary")
    lines.append("")

    platform_group = results.get("platform_pass") is not None
    if platform_group:
        lines.append(
            f"  Platform:   {'PASS' if results['platform_pass'] else 'FAILED'}"
        )
    lines.append(
        f"  Application: {'PASS' if results.get('infrastructure_pass', False) else 'FAILED'}"
    )
    if results.get("quota_pass") is not None:
        lines.append(f"  Quota:      {'PASS' if results['quota_pass'] else 'FAILED'}")
    lines.append(f"  Total:      {results['passed']}/{results['total']} passed")
    lines.append("")

    quota_failures = [
        r
        for r in results["results"]
        if r.get("category") == QUOTA and r["status"] != "pass"
    ]
    if quota_failures:
        lines.append("Quota issues:")
        for r in quota_failures:
            lines.append(f"  - {r['label']}: {r.get('error', 'unknown')}")

    return "\n".join(lines)


def format_json(results: Dict[str, Any]) -> str:
    out: Dict[str, Any] = {}
    for r in results["results"]:
        out[r["name"]] = {
            "status": r["status"],
            "group": r.get("group", "application"),
            "error": r.get("error", ""),
            "latency": r.get("latency", 0),
        }
        if r.get("category"):
            out[r["name"]]["category"] = r["category"]
        if r.get("details"):
            out[r["name"]]["details"] = r["details"]

    summary: Dict[str, Any] = {
        "platform": "pass" if results.get("platform_pass") else "fail",
        "infrastructure": (
            "pass" if results.get("infrastructure_pass", False) else "fail"
        ),
        "passed": results["passed"],
        "total": results["total"],
    }
    if results.get("quota_pass") is not None:
        summary["quota"] = "pass" if results["quota_pass"] else "fail"
    out["_summary"] = summary
    return json.dumps(out, indent=2)


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    # Delegate to UI verifier when first arg is "ui"
    if len(sys.argv) > 1 and sys.argv[1] == "ui":
        from backend import verify_ui

        sys.argv.pop(1)  # remove "ui" so verify_ui gets the remaining args
        verify_ui.main()
        return

    parser = argparse.ArgumentParser(
        description="Verify Alma platform and application endpoints end-to-end. "
        "Use 'ui' subcommand for UI verification: python -m backend.verify ui --help",
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--platform",
        action="store_true",
        help="Run only platform checks (mail, auth, storage, notifications)",
    )
    group.add_argument(
        "--application",
        action="store_true",
        help="Run only application endpoint checks (health, canvas, thinking, web, images)",
    )

    parser.add_argument(
        "checks",
        nargs="*",
        metavar="CHECK",
        default=[],
        help="Specific checks to run (default: all); choices: "
        + ", ".join(sorted(ALL_CHECKS.keys())),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        metavar="FILE",
        help="Write JSON report to FILE (implies --json)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds (default: 60)",
    )

    args = parser.parse_args()

    global _TIMEOUT
    _TIMEOUT = args.timeout

    if args.checks:
        for c in args.checks:
            if c not in ALL_CHECKS:
                parser.error(
                    f"unknown check: {c!r}; choices: {', '.join(sorted(ALL_CHECKS.keys()))}"
                )

    config = get_config()

    names: Optional[List[str]] = None
    groups: Optional[List[str]] = None

    if args.platform:
        groups = ["platform"]
    elif args.application:
        groups = ["application"]
    elif args.checks:
        names = args.checks

    results = run_checks(config, names=names, groups=groups)

    use_json = args.json or args.output is not None
    output = format_json(results) if use_json else format_human(results)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
            f.write("\n")

    if args.output:
        print(f"Report written to {args.output}")
    else:
        print(output)

    overall = results.get("platform_pass", True) and results.get(
        "infrastructure_pass", True
    )
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    main()
