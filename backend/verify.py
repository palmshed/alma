"""
End-to-end verification CLI for the Alma backend.

Validates every mode endpoint against the deployed API.

Usage:
    python -m backend.verify
    python -m backend.verify --json
    python -m backend.verify canvas thinking
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

REQUIRED_ENV_KEYS = ["ALMA_BASE_URL"]
TIMEOUT = 60


def get_config() -> Dict[str, str]:
    missing = [k for k in REQUIRED_ENV_KEYS if not os.environ.get(k)]
    if missing:
        print(f"Missing required env vars: {', '.join(missing)}")
        sys.exit(1)
    return {
        "base_url": os.environ["ALMA_BASE_URL"].rstrip("/"),
        "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
        "google_cloud_project": os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
        "google_cloud_location": os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
    }


def api_post(
    url: str, payload: dict, timeout: int = TIMEOUT
) -> Tuple[int, Any, Optional[Dict[str, str]]]:
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
    url: str, timeout: int = TIMEOUT
) -> Tuple[int, Any, Optional[Dict[str, str]]]:
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


def check_health(config: Dict[str, str]) -> Dict[str, Any]:
    result = {"name": "health", "label": "Health", "status": "fail"}
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
    result = {"name": "canvas", "label": "Canvas", "status": "fail"}
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
        if status == 429:
            result["details"] = {"note": "quota exhausted on free tier for this model"}
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
    result = {"name": "thinking", "label": "Thinking", "status": "fail"}
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
        if status == 429:
            result["details"] = {"note": "quota exhausted on free tier for this model"}
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
    result = {"name": "web", "label": "Web", "status": "fail"}
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
        if status == 429:
            result["details"] = {"note": "quota exhausted on free tier for this model"}
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
    result = {"name": "images", "label": "Images", "status": "fail"}
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
        if status == 429:
            result["details"] = {
                "note": "image generation quota exhausted on free tier"
            }
        return result

    if isinstance(body_data, dict):
        result["error"] = (
            f"unexpected JSON response (expected image bytes): {body_data}"
        )
        return result

    if not isinstance(body_data, bytes) or len(body_data) == 0:
        result["error"] = "empty response body"
        return result

    content_type = (headers or {}).get("Content-Type", "unknown")
    w, h = parse_image_dimensions(body_data)
    if w == 0 or h == 0:
        result["error"] = (
            f"could not decode image dimensions (Content-Type: {content_type}, size: {len(body_data)} bytes)"
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


CHECKS = {
    "health": check_health,
    "canvas": check_canvas,
    "thinking": check_thinking,
    "web": check_web,
    "images": check_images,
}


def run_checks(
    config: Dict[str, str], names: Optional[List[str]] = None
) -> Dict[str, Any]:
    if names:
        check_map = {n: CHECKS[n] for n in names if n in CHECKS}
    else:
        check_map = CHECKS

    results = []
    for name, fn in check_map.items():
        results.append(fn(config))

    passed = sum(1 for r in results if r["status"] == "pass")
    return {"results": results, "passed": passed, "total": len(results)}


def format_human(results: Dict[str, Any]) -> str:
    lines = []
    for r in results["results"]:
        if r["status"] == "pass":
            lines.append(f"\N{CHECK MARK} {r['label']}")
        else:
            lines.append(f"\N{CROSS MARK} {r['label']}")

        if r.get("error"):
            lines.append(f"  {r['error']}")
        if r.get("details"):
            for k, v in r["details"].items():
                lines.append(f"  {k}: {v}")
        if r.get("latency"):
            lines.append(f"  {r['latency']} s")
        lines.append("")

    lines.append("Summary")
    lines.append(f"{results['passed']}/{results['total']} passed")
    return "\n".join(lines)


def format_json(results: Dict[str, Any]) -> str:
    out = {}
    for r in results["results"]:
        out[r["name"]] = r["status"]
    return json.dumps(out, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify Alma backend endpoints end-to-end",
    )
    parser.add_argument(
        "checks",
        nargs="*",
        choices=list(CHECKS.keys()),
        default=[],
        help="Specific checks to run (default: all)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    config = get_config()
    names = args.checks if args.checks else None
    results = run_checks(config, names)

    if args.json:
        print(format_json(results))
    else:
        print(format_human(results))

    sys.exit(0 if results["passed"] == results["total"] else 1)


if __name__ == "__main__":
    main()
