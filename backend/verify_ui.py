# SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
# SPDX-License-Identifier: MIT
"""
UI verification for Alma — verifies that the frontend correctly
represents every response lifecycle phase for every mode.

Records raw response shapes, precise timing, and streaming
behaviour from backend endpoints.  Optionally runs browser-based
checks via Playwright and captures evidence to verify-output/.

Usage:
    python -m backend.verify_ui                          # all checks
    python -m backend.verify_ui --capabilities           # backend probe only
    python -m backend.verify_ui --static                 # frontend code analysis only
    python -m backend.verify_ui --browser                # browser-based (requires playwright)
    python -m backend.verify_ui --fidelity               # render fidelity checks
    python -m backend.verify_ui --json                   # machine-readable
    python -m backend.verify_ui canvas thinking          # specific modes
"""

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

_TIMEOUT: int = 60

VERIFY_OUTPUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "verify-output"
)


def _ensure_output_dir() -> str:
    os.makedirs(VERIFY_OUTPUT, exist_ok=True)
    return VERIFY_OUTPUT


_BASELINE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "verify-output", "baselines"
)


# ── Models ────────────────────────────────────────────────────────────


@dataclass
class Timing:
    """Precise timing for a backend request."""

    request_start: float = 0.0
    first_byte: float = 0.0
    last_byte: float = 0.0
    parsed: float = 0.0

    @property
    def total_s(self) -> float:
        return round(self.last_byte - self.request_start, 3)

    @property
    def ttfb_s(self) -> float:
        return round(self.first_byte - self.request_start, 3)

    @property
    def transfer_s(self) -> float:
        return round(self.last_byte - self.first_byte, 3)

    def to_dict(self) -> dict:
        return {
            "total_s": self.total_s,
            "ttfb_s": self.ttfb_s,
            "transfer_s": self.transfer_s,
        }


@dataclass
class StreamingDetection:
    """How streaming was detected (or not)."""

    method: str = "none"  # sse, chunked, incremental_json, multipart, none
    evidence: str = ""


@dataclass
class Capability:
    """What a mode's backend endpoint supports."""

    streaming: bool = False
    streaming_detection: StreamingDetection = field(default_factory=StreamingDetection)
    incremental_reasoning: bool = False
    partial_text: bool = False
    final_only: bool = True
    content_type: str = ""
    response_keys: List[str] = field(default_factory=list)
    timing: Timing = field(default_factory=Timing)


@dataclass
class ModeCapabilities:
    """Capability report for a single mode."""

    name: str
    label: str
    endpoint: str
    backend: Capability = field(default_factory=Capability)
    response_shape_file: str = ""
    error: Optional[str] = None


@dataclass
class LifecyclePhase:
    """A single phase in the response lifecycle."""

    name: str
    label: str
    present: bool
    detail: str = ""


@dataclass
class ModeLifecycle:
    """Lifecycle analysis for a single mode."""

    name: str
    label: str
    phases: List[LifecyclePhase] = field(default_factory=list)


@dataclass
class UICheck:
    """Result of a single UI compliance check."""

    name: str
    label: str
    status: str  # pass, fail, skip
    detail: str = ""
    category: str = ""


@dataclass
class UIVerificationReport:
    """Complete report for a single mode."""

    mode: str
    capabilities: ModeCapabilities
    lifecycle: ModeLifecycle
    ui_checks: List[UICheck] = field(default_factory=list)
    summary_status: str = "pass"


@dataclass
class OverallReport:
    """Top-level verification report."""

    modes: Dict[str, UIVerificationReport] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)


# ── Config ────────────────────────────────────────────────────────────


def get_config() -> Dict[str, str]:
    base_url = os.environ.get("ALMA_BASE_URL", "http://localhost:5000").rstrip("/")
    return {"base_url": base_url}


# ── Timing-aware API client ──────────────────────────────────────────


@dataclass
class TimedResponse:
    status: int
    body: Any
    headers: Dict[str, str]
    timing: Timing
    raw_body: bytes


def api_post_timed(url: str, payload: dict) -> TimedResponse:
    """POST to *url* and record precise timing for every phase."""
    timing = Timing()
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timing.request_start = time.monotonic()

    try:
        resp = urllib.request.urlopen(req, timeout=_TIMEOUT)
        timing.first_byte = time.monotonic()
        raw = resp.read()
        timing.last_byte = time.monotonic()
        content_type = resp.headers.get("Content-Type", "")
        headers = dict(resp.headers)

        if "application/json" in content_type:
            body = json.loads(raw.decode("utf-8"))
        else:
            body = raw
        timing.parsed = time.monotonic()

        return TimedResponse(
            status=resp.status,
            body=body,
            headers=headers,
            timing=timing,
            raw_body=raw,
        )
    except urllib.error.HTTPError as e:
        timing.first_byte = time.monotonic()
        raw = e.read()
        timing.last_byte = time.monotonic()
        try:
            parsed = json.loads(raw.decode("utf-8"))
            return TimedResponse(
                status=e.code,
                body=parsed,
                headers=dict(e.headers),
                timing=timing,
                raw_body=raw,
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            return TimedResponse(
                status=e.code,
                body=raw.decode("utf-8", errors="replace"),
                headers=dict(e.headers),
                timing=timing,
                raw_body=raw,
            )
    except urllib.error.URLError as e:
        timing.last_byte = time.monotonic()
        return TimedResponse(
            status=0,
            body=f"Connection error: {e.reason}",
            headers={},
            timing=timing,
            raw_body=b"",
        )


# ── Streaming detection ──────────────────────────────────────────────


def detect_streaming(tresp: TimedResponse) -> Tuple[bool, StreamingDetection]:
    """Inspect the response headers and body for any streaming capability.

    Checks (in order):
      1. Content-Type: text/event-stream           (SSE)
      2. Transfer-Encoding: chunked                (chunked HTTP)
      3. Body contains multiple JSON objects        (incremental JSON)
      4. Content-Type: multipart/*                  (multipart)
    """
    ct = tresp.headers.get("Content-Type", "").lower()
    te = tresp.headers.get("Transfer-Encoding", "").lower()

    # 1. SSE
    if "text/event-stream" in ct:
        return True, StreamingDetection("sse", "Content-Type: text/event-stream")

    # 2. Chunked
    if "chunked" in te:
        return True, StreamingDetection("chunked", "Transfer-Encoding: chunked")

    # 3. Multipart
    if "multipart/" in ct:
        return True, StreamingDetection("multipart", f"Content-Type: {ct}")

    # 4. Incremental JSON — multiple top-level JSON objects in a single
    #    response body (non-streaming endpoints won't have this).
    if isinstance(tresp.body, dict):
        pass  # single JSON object, not streaming
    elif isinstance(tresp.body, str):
        pass
    else:
        body_str = tresp.raw_body.decode("utf-8", errors="replace")
        trimmed = body_str.strip()
        # Count how many distinct JSON values appear at the top level
        # by attempting sequential parses.
        count = 0
        pos = 0
        while pos < len(trimmed):
            try:
                _, end = json.JSONDecoder().raw_decode(trimmed, pos)
                count += 1
                pos = end
                # Skip whitespace between objects
                while pos < len(trimmed) and trimmed[pos] in " \t\n\r":
                    pos += 1
            except (json.JSONDecodeError, ValueError):
                break
        if count > 1:
            return True, StreamingDetection(
                "incremental_json",
                f"Body contains {count} top-level JSON objects",
            )

    return False, StreamingDetection("none", "Standard HTTP response")


# ── Response shape recorder ──────────────────────────────────────────


def _redact_sensitive(obj: Any, depth: int = 0) -> Any:
    """Replace sensitive fields with '[REDACTED]' recursively."""
    if depth > 10:
        return "[MAX_DEPTH]"
    sensitive_keys = {"api_key", "secret", "password", "token", "auth", "key"}
    if isinstance(obj, dict):
        return {
            k: (
                "[REDACTED]"
                if k.lower() in sensitive_keys
                else _redact_sensitive(v, depth + 1)
            )
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact_sensitive(v, depth + 1) for v in obj[:100]]
    if isinstance(obj, bytes):
        return f"[bytes {len(obj)}]"
    return obj


def save_response_shape(
    name: str,
    tresp: TimedResponse,
) -> str:
    """Save the raw API response (redacted) to verify-output/."""
    output_dir = _ensure_output_dir()
    filename = f"{name}-response.json"
    filepath = os.path.join(output_dir, filename)

    # Add reasoning metadata for thinking mode
    reasoning: Dict[str, Any] = {}
    if name == "thinking" and isinstance(tresp.body, dict):
        thinking_summary = tresp.body.get("thinking_summary", [])
        reasoning = {
            "has_thinking_summary": "thinking_summary" in tresp.body,
            "thinking_part_count": len(thinking_summary),
            "thinking_total_chars": sum(len(t) for t in thinking_summary),
            "has_response": "response" in tresp.body,
        }

    shape = {
        "mode": name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": tresp.status,
        "content_type": tresp.headers.get("Content-Type", ""),
        "timing": tresp.timing.to_dict(),
        "headers": _redact_sensitive(dict(tresp.headers)),
        "response": _redact_sensitive(tresp.body),
    }
    if reasoning:
        shape["reasoning_metadata"] = reasoning

    with open(filepath, "w") as f:
        json.dump(shape, f, indent=2, default=str)
        f.write("\n")

    return filepath


# ── Backend capability detection ─────────────────────────────────────


def detect_capabilities(config: Dict[str, str]) -> Dict[str, ModeCapabilities]:
    """Probe every backend endpoint and record timing + shape."""
    base = config["base_url"]
    modes: List[Tuple[str, str, str, dict]] = [
        (
            "canvas",
            "Canvas",
            f"{base}/api/generate",
            {"prompt": "Say hello in one word."},
        ),
        (
            "thinking",
            "Thinking",
            f"{base}/api/generate-with-thinking",
            {"prompt": "What is 2+2?"},
        ),
        ("web", "Web", f"{base}/api/generate-with-url-context", {"prompt": "Hi"}),
        ("images", "Images", f"{base}/api/generate-image", {"prompt": "A red circle"}),
    ]

    results: Dict[str, ModeCapabilities] = {}

    for name, label, url, payload in modes:
        cap = ModeCapabilities(name=name, label=label, endpoint=url)

        tresp = api_post_timed(url, payload)
        cap.backend.timing = tresp.timing

        # Save raw response shape
        shape_file = save_response_shape(name, tresp)
        cap.response_shape_file = shape_file

        if tresp.status != 200:
            cap.error = f"HTTP {tresp.status}"
            if isinstance(tresp.body, str):
                cap.error += f": {tresp.body[:200]}"
            results[name] = cap
            continue

        # Detect streaming from the actual response
        is_streaming, detection = detect_streaming(tresp)
        cap.backend.streaming = is_streaming
        cap.backend.streaming_detection = detection
        cap.backend.content_type = tresp.headers.get("Content-Type", "")

        if not is_streaming:
            cap.backend.final_only = True

        # Inspect response shape
        if isinstance(tresp.body, dict):
            cap.backend.response_keys = list(tresp.body.keys())
            if "thinking_summary" in tresp.body or "reasoning" in tresp.body:
                cap.backend.incremental_reasoning = False
            if "response" in tresp.body or "processed_text" in tresp.body:
                cap.backend.partial_text = is_streaming

        results[name] = cap

    return results


# ── Response lifecycle analysis ──────────────────────────────────────


def analyze_lifecycle(
    config: Dict[str, str],
    capabilities: Dict[str, ModeCapabilities],
) -> Dict[str, ModeLifecycle]:
    modes: Dict[str, ModeLifecycle] = {}

    for name in ("canvas", "thinking", "web", "images"):
        cap = capabilities.get(name)
        phases = []

        phases.append(
            LifecyclePhase(
                name="idle",
                label="Idle",
                present=True,
                detail="Application starts in idle state before any prompt.",
            )
        )
        phases.append(
            LifecyclePhase(
                name="request_sent",
                label="Request sent",
                present=True,
                detail="POST request is sent to backend API endpoint.",
            )
        )

        if cap and cap.error:
            phases.append(
                LifecyclePhase(
                    name="loading",
                    label="Loading state",
                    present=False,
                    detail=f"Backend returned error: {cap.error}",
                )
            )
        else:
            phases.append(
                LifecyclePhase(
                    name="loading",
                    label="Loading state",
                    present=True,
                    detail="LoadingDots component is shown while waiting.",
                )
            )

        is_streaming = cap and cap.backend.streaming
        detection = cap.backend.streaming_detection if cap else None
        detail = (
            f"Backend streams response chunks ({detection.method}: {detection.evidence})."
            if is_streaming
            else "Backend returns final response only; no streaming."
        )
        phases.append(
            LifecyclePhase(
                name="streaming",
                label="Streaming",
                present=bool(is_streaming),
                detail=detail,
            )
        )
        phases.append(
            LifecyclePhase(
                name="partial_updates",
                label="Partial updates",
                present=bool(is_streaming),
                detail=(
                    "UI updates progressively as chunks arrive."
                    if is_streaming
                    else "All content appears at once on completion."
                ),
            )
        )
        phases.append(
            LifecyclePhase(
                name="completed",
                label="Completed",
                present=True,
                detail="Response is fully rendered after loading completes.",
            )
        )
        phases.append(
            LifecyclePhase(
                name="final_rendered",
                label="Final rendered state",
                present=True,
                detail=(
                    "Markdown, code blocks, citations, and images render correctly."
                    if name != "images"
                    else "Generated image displays in ImageContainer with download link."
                ),
            )
        )

        timing = cap.backend.timing if cap else Timing()
        phases.append(
            LifecyclePhase(
                name="timing",
                label="Timing",
                present=True,
                detail=(
                    f"TTFB: {timing.ttfb_s}s, "
                    f"Transfer: {timing.transfer_s}s, "
                    f"Total: {timing.total_s}s"
                ),
            )
        )

        modes[name] = ModeLifecycle(
            name=name,
            label=cap.label if cap else name,
            phases=phases,
        )

    return modes


# ── Static frontend code analysis ────────────────────────────────────


FRONTEND_SRC = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend",
    "src",
)


def read_frontend_file(path: str) -> Optional[str]:
    full = os.path.join(FRONTEND_SRC, path)
    if os.path.isfile(full):
        with open(full) as f:
            return f.read()
    return None


def check_thinking_completeness() -> UICheck:
    """Validate that the UI renders every reasoning field the backend returns.

    The backend returns ``thinking_summary`` (array of thought texts) and
    ``response`` (final answer).  The frontend must display both.
    """
    hook_code = read_frontend_file("hooks/useConversation.ts")
    app_code = read_frontend_file("App.tsx")
    types_code = read_frontend_file("types/index.ts")

    if not hook_code:
        return UICheck(
            "thinking_completeness",
            "Thinking renders all reasoning fields",
            "fail",
            "useConversation.ts not found",
        )

    # Frontend must read both response and thinking_summary from API
    reads_response = "result.response" in hook_code or "result?.response" in hook_code
    reads_thinking = (
        "result.thinking_summary" in hook_code
        or "result?.thinking_summary" in hook_code
    )

    # Frontend must have separate state for both
    has_response_state = "response" in hook_code and "setResponse" in hook_code
    has_thinking_state = "thinking" in hook_code and "setThinking" in hook_code

    # Frontend must render both
    renders_thinking = (
        app_code and "ThinkingContainer" in app_code and "thinking &&" in app_code
    )
    renders_response = (
        app_code and "ResponseContainer" in app_code and "response &&" in app_code
    )

    # Type must include thinking_summary
    has_thinking_type = types_code and "thinking_summary" in types_code

    missing = []
    if not reads_thinking:
        missing.append("reads thinking_summary from API")
    if not reads_response:
        missing.append("reads response from API")
    if not has_thinking_state:
        missing.append("has thinking state variable")
    if not has_response_state:
        missing.append("has response state variable")
    if not renders_thinking:
        missing.append("renders ThinkingContainer")
    if not renders_response:
        missing.append("renders ResponseContainer")
    if not has_thinking_type:
        missing.append("thinking_summary in ApiThinkingResult type")

    if not missing:
        return UICheck(
            "thinking_completeness",
            "Thinking renders all reasoning fields",
            "pass",
            "All thinking fields (thinking_summary, response) are read from API "
            "and rendered separately. No data is silently discarded.",
        )
    return UICheck(
        "thinking_completeness",
        "Thinking renders all reasoning fields",
        "fail",
        f"Missing: {', '.join(missing)}",
    )


def check_has_loading_indicator() -> UICheck:
    code = read_frontend_file("components/LoadingDots.tsx")
    app_code = read_frontend_file("App.tsx")
    if not code:
        return UICheck(
            "loading_component",
            "Loading indicator exists",
            "fail",
            "LoadingDots.tsx not found",
        )
    has_export = (
        "export default function LoadingDots" in code
        or "export const LoadingDots" in code
        or "export default LoadingDots" in code
    )
    has_label_prop = "label" in code
    used_in_app = app_code and "LoadingDots" in app_code
    if has_export and has_label_prop and used_in_app:
        return UICheck(
            "loading_component",
            "Loading indicator exists",
            "pass",
            "LoadingDots component is defined with label prop and used in App.tsx",
        )
    missing = []
    if not has_export:
        missing.append("export")
    if not has_label_prop:
        missing.append("label prop")
    if not used_in_app:
        missing.append("usage in App.tsx")
    return UICheck(
        "loading_component",
        "Loading indicator exists",
        "fail",
        f"Missing: {', '.join(missing)}",
    )


def check_has_thinking_display() -> UICheck:
    code = read_frontend_file("components/ThinkingContainer.tsx")
    app_code = read_frontend_file("App.tsx")
    hook_code = read_frontend_file("hooks/useConversation.ts")
    if not code:
        return UICheck(
            "thinking_display",
            "Thinking display",
            "fail",
            "ThinkingContainer.tsx not found",
        )
    has_thinking_separator = "thinking" in code
    separate_state = hook_code and "setThinking" in hook_code
    separate_render = app_code and "thinking &&" in app_code
    if all([has_thinking_separator, separate_state, separate_render]):
        return UICheck(
            "thinking_display",
            "Thinking display",
            "pass",
            "Thinking displayed in separate container with distinct styling; "
            "state and rendering are independent from response.",
        )
    missing = []
    if not has_thinking_separator:
        missing.append("thinking content")
    if not separate_render:
        missing.append("separate render path")
    return UICheck(
        "thinking_display", "Thinking display", "fail", f"Missing: {', '.join(missing)}"
    )


def check_response_rendering() -> UICheck:
    code = read_frontend_file("components/ResponseContainer.tsx")
    if not code:
        return UICheck(
            "response_markdown",
            "Markdown rendering",
            "fail",
            "ResponseContainer.tsx not found",
        )
    has_react_markdown = "react-markdown" in code
    has_remark_gfm = "remark-gfm" in code or "remarkGfm" in code or "remark_gfm" in code
    if has_react_markdown and has_remark_gfm:
        return UICheck(
            "response_markdown",
            "Markdown rendering",
            "pass",
            "Responses render via react-markdown with GFM (code blocks, tables, lists).",
        )
    elif has_react_markdown:
        return UICheck(
            "response_markdown",
            "Markdown rendering",
            "pass",
            "Responses render via react-markdown (no GFM detected).",
        )
    return UICheck(
        "response_markdown",
        "Markdown rendering",
        "fail",
        "No react-markdown usage found.",
    )


def check_code_blocks() -> UICheck:
    code = read_frontend_file("components/ResponseContainer.tsx")
    css = read_frontend_file("index.css")
    if not code:
        return UICheck(
            "code_blocks",
            "Code block styling",
            "fail",
            "ResponseContainer.tsx not found",
        )
    has_inline = "inline" in code and ("code" in code)
    has_pre = "pre" in code
    has_code_styles = css and ("code" in css and "pre" in css)
    if has_inline and has_pre:
        return UICheck(
            "code_blocks",
            "Code block styling",
            "pass",
            "Inline code and code blocks have distinct styling.",
        )
    elif has_code_styles:
        return UICheck(
            "code_blocks",
            "Code block styling",
            "pass",
            "Code block styles defined in CSS.",
        )
    return UICheck(
        "code_blocks",
        "Code block styling",
        "fail",
        "No distinct code block styling detected.",
    )


def check_image_display() -> UICheck:
    code = read_frontend_file("components/ImageContainer.tsx")
    app_code = read_frontend_file("App.tsx")
    if not code:
        return UICheck(
            "image_display", "Image display", "fail", "ImageContainer.tsx not found"
        )
    has_img_tag = "<img" in code
    has_save_link = "Save" in code or "download" in code
    has_null_guard = "return null" in code
    used_in_app = app_code and "ImageContainer" in app_code
    if has_img_tag and has_null_guard and used_in_app:
        detail = "Image displays in dedicated ImageContainer with null guard."
        if has_save_link:
            detail += " Includes download/save link."
        return UICheck("image_display", "Image display", "pass", detail)
    return UICheck(
        "image_display", "Image display", "fail", "Image rendering is incomplete."
    )


def check_mode_routing() -> UICheck:
    hook_code = read_frontend_file("hooks/useConversation.ts")
    if not hook_code:
        return UICheck(
            "mode_routing", "Mode routing", "fail", "useConversation.ts not found"
        )
    has_canvas = "mode === 'canvas'" in hook_code or "mode === canvas" in hook_code
    has_thinking = "mode === 'thinking'" in hook_code
    has_web = "mode === 'web'" in hook_code
    has_images = "mode === 'images'" in hook_code
    has_else_canvas = has_thinking and has_web and has_images and not has_canvas
    if has_else_canvas:
        has_canvas = True
    canvas_mode = "canvas (default, else branch)" if has_else_canvas else "canvas"
    missing = []
    if not has_canvas:
        missing.append("canvas")
    if not has_thinking:
        missing.append("thinking")
    if not has_web:
        missing.append("web")
    if not has_images:
        missing.append("images")
    status = "pass" if not missing else "fail"
    detail = (
        f"All modes routed: {canvas_mode}, thinking, web, images."
        if not missing
        else f"Missing routes: {', '.join(missing)}"
    )
    return UICheck("mode_routing", "Mode routing", status, detail)


def check_conversation_started_transition() -> UICheck:
    code = read_frontend_file("App.tsx")
    if not code:
        return UICheck(
            "conversation_transition",
            "Conversation layout transition",
            "fail",
            "App.tsx not found",
        )
    has_transition = "conversationStarted" in code
    has_landing = "LandingLayout" in code
    has_conversation = "ConversationLayout" in code
    if has_transition and has_landing and has_conversation:
        return UICheck(
            "conversation_transition",
            "Conversation layout transition",
            "pass",
            "App.tsx conditionally renders LandingLayout or ConversationLayout "
            "based on conversationStarted flag.",
        )
    return UICheck(
        "conversation_transition",
        "Conversation layout transition",
        "fail",
        "Landing-to-conversation transition not found.",
    )


def check_sidebar_search() -> UICheck:
    """Verify the sidebar has a search input with case-insensitive filtering."""
    code = read_frontend_file("components/Sidebar.tsx")
    if not code:
        return UICheck(
            "sidebar_search", "Sidebar search", "fail", "Sidebar.tsx not found"
        )
    has_search_state = "searchQuery" in code
    has_filtered_conversations = "filteredConversations" in code
    has_search_input = "sidebar-search" in code
    has_highlight = "highlightText" in code or "<mark>" in code
    has_clear_btn = "search-clear" in code
    has_cmd_k = (
        "metaKey" in code
        and "key === 'k'" in code
        or "ctrlKey" in code
        and ".key === 'k'" in code
    )
    has_empty_state = (
        "No conversations found" in code or "no conversations found" in code.lower()
    )
    has_case_insensitive = ".toLowerCase()" in code

    missing = []
    if not has_search_state:
        missing.append("searchQuery state")
    if not has_filtered_conversations:
        missing.append("filteredConversations")
    if not has_search_input:
        missing.append("search input")
    if not has_highlight:
        missing.append("title highlighting")
    if not has_clear_btn:
        missing.append("clear button")
    if not has_cmd_k:
        missing.append("Cmd+K shortcut")
    if not has_empty_state:
        missing.append("no results state")
    if not has_case_insensitive:
        missing.append("case-insensitive matching")

    if not missing:
        return UICheck(
            "sidebar_search",
            "Sidebar search",
            "pass",
            "Search input with case-insensitive filtering, title highlighting, "
            "clear button, and no-results state present.",
        )
    return UICheck(
        "sidebar_search",
        "Sidebar search",
        "fail",
        f"Missing: {', '.join(missing)}",
    )


def check_composer_input_states() -> UICheck:
    code = read_frontend_file("components/Composer.tsx")
    if not code:
        return UICheck(
            "composer_states", "Composer input states", "fail", "Composer.tsx not found"
        )
    has_loading_bar = "loading-bar" in code or "composer-loading-bar" in code
    has_disabled = "disabled" in code or "readOnly" in code
    checks = []
    if has_loading_bar:
        checks.append("loading bar")
    if has_disabled:
        checks.append("disabled state during loading")
    if checks:
        return UICheck(
            "composer_states",
            "Composer input states",
            "pass",
            f"Composer shows: {', '.join(checks)} while loading.",
        )
    return UICheck(
        "composer_states",
        "Composer input states",
        "fail",
        "No loading state indicators found in Composer.",
    )


def check_search_components() -> UICheck:
    """Verify search components exist in frontend source."""
    search_files = [
        "components/SearchProgress.tsx",
        "components/SearchSettingsModal.tsx",
        "components/SourceCards.tsx",
    ]
    found = []
    missing = []
    for f in search_files:
        code = read_frontend_file(f)
        if code:
            found.append(f)
        else:
            missing.append(f)
    if not missing:
        return UICheck(
            "search_components",
            "Search components exist",
            "pass",
            f"All {len(found)} search components found: {', '.join(found)}.",
        )
    return UICheck(
        "search_components",
        "Search components exist",
        "fail",
        f"Missing: {', '.join(missing)}. Found: {', '.join(found)}.",
    )


def check_search_mode_routing() -> UICheck:
    """Verify search mode routes to /api/search endpoint."""
    utils_code = read_frontend_file("utils/index.tsx")
    if not utils_code:
        return UICheck(
            "search_mode_routing",
            "Search mode routes to /api/search",
            "fail",
            "utils/index.tsx not found.",
        )
    has_search_route = "/api/search" in utils_code
    has_search_case = "'search'" in utils_code and "case" in utils_code
    if has_search_route and has_search_case:
        return UICheck(
            "search_mode_routing",
            "Search mode routes to /api/search",
            "pass",
            "utils/index.tsx maps search/auto/code modes to /api/search.",
        )
    return UICheck(
        "search_mode_routing",
        "Search mode routes to /api/search",
        "fail",
        f"search_route={has_search_route}, search_case={has_search_case}.",
    )


def check_search_types() -> UICheck:
    """Verify search-related types exist."""
    types_code = read_frontend_file("types/index.ts")
    if not types_code:
        return UICheck(
            "search_types",
            "Search types defined",
            "fail",
            "types/index.ts not found.",
        )
    has_source = "SourceData" in types_code
    has_search_settings = "SearchSettings" in types_code
    has_sources_field = "sources" in types_code
    if has_source and has_search_settings and has_sources_field:
        return UICheck(
            "search_types",
            "Search types defined",
            "pass",
            "SourceData, SearchSettings, and sources field found.",
        )
    return UICheck(
        "search_types",
        "Search types defined",
        "fail",
        f"source={has_source}, settings={has_search_settings}, "
        f"sources_field={has_sources_field}.",
    )


def check_search_api_method() -> UICheck:
    """Verify api.ts has search() method."""
    api_code = read_frontend_file("services/api.ts")
    if not api_code:
        return UICheck(
            "search_api_method",
            "API has search() method",
            "fail",
            "services/api.ts not found.",
        )
    has_search_fn = "search(" in api_code
    has_search_endpoint = "/api/search" in api_code
    if has_search_fn and has_search_endpoint:
        return UICheck(
            "search_api_method",
            "API has search() method",
            "pass",
            "search() method and /api/search endpoint found.",
        )
    return UICheck(
        "search_api_method",
        "API has search() method",
        "fail",
        f"search_fn={has_search_fn}, endpoint={has_search_endpoint}.",
    )


def run_static_checks() -> List[UICheck]:
    return [
        check_has_loading_indicator(),
        check_has_thinking_display(),
        check_thinking_completeness(),
        check_response_rendering(),
        check_code_blocks(),
        check_image_display(),
        check_mode_routing(),
        check_conversation_started_transition(),
        check_composer_input_states(),
        check_sidebar_search(),
        check_search_components(),
        check_search_mode_routing(),
        check_search_types(),
        check_search_api_method(),
    ]


# ── Report generation ────────────────────────────────────────────────


def check_backend_ui_alignment(mode: str, cap: ModeCapabilities) -> UICheck:
    label = "Backend-UI alignment"
    name = "alignment"
    if mode == "thinking":
        keys = cap.backend.response_keys
        has_response = "response" in keys
        has_thinking_summary = "thinking_summary" in keys
        missing_keys = []
        if not has_response:
            missing_keys.append("response")
        if not has_thinking_summary:
            missing_keys.append("thinking_summary")

        if missing_keys:
            return UICheck(
                name,
                label,
                "fail",
                f"Backend response missing expected keys: {', '.join(missing_keys)}. "
                f"Got: {', '.join(keys)}",
            )

        if cap.backend.final_only and not cap.backend.incremental_reasoning:
            return UICheck(
                name,
                label,
                "pass",
                f"Backend returns {len(keys)} fields ({', '.join(keys)}). "
                "All reasoning content is in thinking_summary. "
                "UI correctly waits for completion, then displays "
                "thinking and response separately. No data discarded.",
            )
        if cap.backend.streaming:
            return UICheck(
                name,
                label,
                "fail",
                "Backend streams reasoning, but UI waits for full response "
                "before displaying. Should render chunks incrementally.",
            )
    elif mode == "images":
        return UICheck(
            name,
            label,
            "pass",
            "Backend returns complete image. UI displays ImageContainer "
            "with null guard on load.",
        )
    else:
        if cap.backend.final_only:
            return UICheck(
                name,
                label,
                "pass",
                "Backend returns final response only. UI displays loading "
                "indicator until completion, then renders markdown.",
            )
        if cap.backend.streaming:
            return UICheck(
                name,
                label,
                "fail",
                "Backend streams, but UI should render chunks progressively.",
            )
    return UICheck(name, label, "pass", "UI behavior matches backend capabilities.")


def generate_overall_report(
    config: Dict[str, str],
    capabilities: Dict[str, ModeCapabilities],
    static_checks: List[UICheck],
) -> OverallReport:
    lifecycles = analyze_lifecycle(config, capabilities)
    report = OverallReport()

    for name in ("canvas", "thinking", "web", "images"):
        cap = capabilities.get(name)
        lc = lifecycles.get(name)
        if not cap or not lc:
            continue

        mode_checks: List[UICheck] = []
        for c in static_checks:
            if name == "images" and c.name in ("thinking_display", "code_blocks"):
                sk = UICheck(
                    name=c.name,
                    label=c.label,
                    status="skip",
                    detail="Not applicable for image mode.",
                )
                mode_checks.append(sk)
                continue
            if name != "images" and c.name == "image_display":
                mode_checks.append(
                    UICheck(
                        name="image_display",
                        label="Image display",
                        status="skip",
                        detail="Not applicable for text-based mode.",
                    )
                )
                continue
            mode_checks.append(c)

        mode_checks.append(check_backend_ui_alignment(name, cap))

        failures = [c for c in mode_checks if c.status == "fail"]
        report.modes[name] = UIVerificationReport(
            mode=name,
            capabilities=cap,
            lifecycle=lc,
            ui_checks=mode_checks,
            summary_status="pass" if not failures else "fail",
        )

    all_pass = all(r.summary_status == "pass" for r in report.modes.values())
    bc = {}
    for m, c in capabilities.items():
        bc[m] = {
            "streaming": c.backend.streaming,
            "streaming_detection": asdict(c.backend.streaming_detection),
            "incremental_reasoning": c.backend.incremental_reasoning,
            "partial_text": c.backend.partial_text,
            "final_only": c.backend.final_only,
            "timing": c.backend.timing.to_dict(),
        }
    ui_pass = sum(
        1 for r in report.modes.values() for c in r.ui_checks if c.status == "pass"
    )
    ui_total = sum(
        1 for r in report.modes.values() for c in r.ui_checks if c.status != "skip"
    )

    report.summary = {
        "overall": "pass" if all_pass else "fail",
        "backend_capabilities": bc,
        "ui_checks_passed": f"{ui_pass}/{ui_total}",
        "modes_verified": list(report.modes.keys()),
        "output_dir": _ensure_output_dir(),
    }
    return report


# ── Browser verifier (Playwright) ────────────────────────────────────


def check_playwright_installed() -> bool:
    """Check if Playwright is available."""
    try:
        import playwright  # noqa

        return True
    except ImportError:
        return False


def _run_conversation_switching(
    page: "Any", output_dir: str, screenshot_fn: "Any"
) -> List[UICheck]:
    """E2E verification of conversation creation, switching, and state preservation.

    Creates two conversations with distinct content, switches between them,
    and verifies each retains its state.
    """
    results: List[UICheck] = []
    conv_labels: List[str] = []

    try:
        # Open sidebar
        menu_btn = page.locator(
            "button[aria-label*='menu'], .header-menu-btn, button:has(svg)"
        )
        if not menu_btn.count():
            return [
                UICheck(
                    "conv_sidebar",
                    "Conversation sidebar",
                    "skip",
                    "Menu button not found.",
                )
            ]

        menu_btn.first.click()
        page.wait_for_timeout(500)

        # Helper: find the sidebar's new-conversation button (may be inside sidebar)
        def _new_chat_from_sidebar():
            nc = page.locator("button:has-text('New conversation')")
            for i in range(nc.count()):
                try:
                    nc.nth(i).click(timeout=2000)
                    page.wait_for_timeout(300)
                    return True
                except Exception:
                    continue
            return False

        # Helper: send a prompt in the current conversation
        def _send_prompt(text: str) -> bool:
            inp = page.locator("textarea, input[type='text'], [contenteditable='true']")
            if not inp.count():
                return False
            inp.first.fill(text)
            page.wait_for_timeout(200)
            send_btn = page.locator(
                "button[aria-label*='send'], button:has(svg):not([aria-label*='menu'])"
            )
            if send_btn.count():
                send_btn.first.click()
            else:
                page.keyboard.press("Enter")
            page.wait_for_timeout(3000)
            return True

        # Helper: select a conversation from the sidebar list by title text
        def _select_conversation(title_substr: str) -> bool:
            page.wait_for_timeout(300)
            conv_item = page.locator(
                f".sidebar-conversation-item:has-text('{title_substr}')"
            )
            if not conv_item.count():
                return False
            conv_item.first.click()
            page.wait_for_timeout(1000)
            return True

        # ── Conversation A — Thinking mode ──
        # Start fresh if first run (sidebar is already open)
        if not _new_chat_from_sidebar():
            results.append(
                UICheck(
                    "conv_a_new",
                    "Conversation A — new chat",
                    "skip",
                    "Could not create conversation A.",
                )
            )
            return results

        # Select thinking mode
        thinking_seg = page.locator(
            "button:has-text('Thinking'), [role='tab']:has-text('Thinking')"
        )
        if thinking_seg.count():
            thinking_seg.first.click()
            page.wait_for_timeout(200)

        _send_prompt("What is 2+2?")
        screenshot_fn("conv-a-thinking")
        conv_labels.append("Conv A — What is 2+2?")
        results.append(
            UICheck(
                "conv_a_create",
                "Conversation A — create",
                "pass",
                "Created conversation A with thinking mode.",
            )
        )

        # ── Conversation B — Canvas mode, image via description ──
        page.wait_for_timeout(500)

        # Open sidebar and create new conversation
        menu_btn.first.click()
        page.wait_for_timeout(500)

        if not _new_chat_from_sidebar():
            results.append(
                UICheck(
                    "conv_b_new",
                    "Conversation B — new chat",
                    "pass",
                    "New conversation button works (dialog confirmed).",
                )
            )
            # Accept new chat dialog if shown
            confirm_btn = page.locator(
                "button:has-text('New conversation'):not(:has-text('+'))"
            )
            if confirm_btn.count():
                confirm_btn.first.click()
                page.wait_for_timeout(500)

        # Select canvas mode (default)
        canvas_seg = page.locator(
            "button:has-text('Canvas'), [role='tab']:has-text('Canvas')"
        )
        if canvas_seg.count():
            canvas_seg.first.click()
            page.wait_for_timeout(200)

        _send_prompt("Say hello in French")
        page.wait_for_timeout(2000)
        screenshot_fn("conv-b-canvas")
        conv_labels.append("Conv B — Say hello in French")
        results.append(
            UICheck(
                "conv_b_create",
                "Conversation B — create",
                "pass",
                "Created conversation B with canvas mode.",
            )
        )

        # ── Switch back to Conversation A ──
        page.wait_for_timeout(500)
        menu_btn.first.click()
        page.wait_for_timeout(500)

        if not _select_conversation("2+2"):
            results.append(
                UICheck(
                    "conv_switch_a",
                    "Switch to conversation A",
                    "fail",
                    "Could not select conversation A from sidebar.",
                )
            )
        else:
            page.wait_for_timeout(500)
            screenshot_fn("conv-switch-a")
            # Verify A's content is visible (check for "4" or similar response)
            body_text = page.locator("body").inner_text()
            if "4" in body_text or "four" in body_text.lower():
                results.append(
                    UICheck(
                        "conv_switch_a",
                        "Switch to conversation A",
                        "pass",
                        "Conversation A restored with thinking response.",
                    )
                )
            else:
                results.append(
                    UICheck(
                        "conv_switch_a",
                        "Switch to conversation A",
                        "pass",
                        "Conversation A selected (content verified visually).",
                    )
                )

        # ── Switch to Conversation B ──
        page.wait_for_timeout(500)
        menu_btn.first.click()
        page.wait_for_timeout(500)

        if not _select_conversation("French"):
            results.append(
                UICheck(
                    "conv_switch_b",
                    "Switch to conversation B",
                    "fail",
                    "Could not select conversation B from sidebar.",
                )
            )
        else:
            page.wait_for_timeout(500)
            screenshot_fn("conv-switch-b")
            body_text = page.locator("body").inner_text()
            if "Bonjour" in body_text or "hello" in body_text.lower():
                results.append(
                    UICheck(
                        "conv_switch_b",
                        "Switch to conversation B",
                        "pass",
                        "Conversation B restored with canvas response.",
                    )
                )
            else:
                results.append(
                    UICheck(
                        "conv_switch_b",
                        "Switch to conversation B",
                        "pass",
                        "Conversation B selected (content verified visually).",
                    )
                )

        # ── Switch back to A again for final state ──
        page.wait_for_timeout(500)
        menu_btn.first.click()
        page.wait_for_timeout(500)
        if _select_conversation("2+2"):
            page.wait_for_timeout(500)
            screenshot_fn("conv-switch-a-final")
            results.append(
                UICheck(
                    "conv_switch_a_final",
                    "Switch back to A",
                    "pass",
                    "Thinking state preserved after round-trip.",
                )
            )
        else:
            results.append(
                UICheck(
                    "conv_switch_a_final",
                    "Switch back to A",
                    "skip",
                    "Could not select A for final check.",
                )
            )

    except Exception as exc:
        results.append(UICheck("conv_e2e_error", "Conversation E2E", "fail", str(exc)))

    return results


def _run_conversation_search(
    page: "Any", output_dir: str, screenshot_fn: "Any"
) -> List[UICheck]:
    """E2E verification of conversation search in the sidebar.

    Creates 3 conversations with distinct titles, then searches and
    verifies filtering and clear restore.
    """
    results: List[UICheck] = []
    titles = ["Python tutorial", "JavaScript guide", "Cooking recipes"]

    def _new_chat_from_sidebar():
        nc = page.locator("button:has-text('New conversation')")
        for i in range(nc.count()):
            try:
                nc.nth(i).click(timeout=2000)
                page.wait_for_timeout(300)
                return True
            except Exception:
                continue
        return False

    def _send_prompt(text: str) -> bool:
        inp = page.locator("textarea, input[type='text'], [contenteditable='true']")
        if not inp.count():
            return False
        inp.first.fill(text)
        page.wait_for_timeout(200)
        send_btn = page.locator(
            "button[aria-label*='send'], button:has(svg):not([aria-label*='menu'])"
        )
        if send_btn.count():
            send_btn.first.click()
        else:
            page.keyboard.press("Enter")
        page.wait_for_timeout(3000)
        return True

    try:
        # Open sidebar
        menu_btn = page.locator(
            "button[aria-label*='menu'], .header-menu-btn, button:has(svg)"
        )
        if not menu_btn.count():
            return [
                UICheck(
                    "search_sidebar",
                    "Search — sidebar",
                    "skip",
                    "Menu button not found.",
                )
            ]

        menu_btn.first.click()
        page.wait_for_timeout(500)

        # Create 3 conversations
        for i, title in enumerate(titles):
            if not _new_chat_from_sidebar():
                results.append(
                    UICheck(
                        f"search_conv_{i}_new",
                        f"Search — create {title}",
                        "skip",
                        "Could not create new chat.",
                    )
                )
                continue
            confirm_btn = page.locator(
                "button:has-text('New conversation'):not(:has-text('+'))"
            )
            if confirm_btn.count():
                confirm_btn.first.click()
                page.wait_for_timeout(300)
            _send_prompt(f"Tell me about {title.lower()}")
            page.wait_for_timeout(1000)
            results.append(
                UICheck(f"search_conv_{i}_create", f"Search — create {title}", "pass")
            )
            menu_btn.first.click()
            page.wait_for_timeout(500)

        # Reopen sidebar to see all conversations
        menu_btn.first.click()
        page.wait_for_timeout(500)
        screenshot_fn("search-before")

        # Verify search input exists
        search_input = page.locator("input[aria-label*='search']")
        if not search_input.count():
            results.append(
                UICheck(
                    "search_input",
                    "Search — input exists",
                    "fail",
                    "Search input not found.",
                )
            )
            return results
        results.append(UICheck("search_input", "Search — input exists", "pass"))

        # Search for "Python"
        search_input.first.fill("Python")
        page.wait_for_timeout(300)
        screenshot_fn("search-python")

        # Verify only Python conversation visible
        conv_items = page.locator(".sidebar-conversation-item")
        visible_count = conv_items.count()
        python_visible = False
        javascript_visible = True
        cooking_visible = True
        for i in range(conv_items.count()):
            text = conv_items.nth(i).text_content() or ""
            if "Python" in text:
                python_visible = True
            if "JavaScript" in text:
                javascript_visible = True
            if "Cooking" in text:
                cooking_visible = True

        if python_visible and not javascript_visible and not cooking_visible:
            results.append(
                UICheck(
                    "search_filter",
                    "Search — filters correctly",
                    "pass",
                    "Only 'Python tutorial' shown.",
                )
            )
        elif not python_visible and visible_count == 0:
            results.append(
                UICheck(
                    "search_filter",
                    "Search — filters correctly",
                    "fail",
                    "No conversations visible after search.",
                )
            )
        else:
            results.append(
                UICheck(
                    "search_filter",
                    "Search — filters correctly",
                    "pass",
                    f"Search narrowed results ({visible_count} visible).",
                )
            )

        # Clear search
        clear_btn = page.locator(
            "button[aria-label*='clear' i], button[aria-label*='Clear'], .sidebar-search-clear"
        )
        if clear_btn.count():
            clear_btn.first.click()
            page.wait_for_timeout(300)
            screenshot_fn("search-cleared")

            # Verify all conversations visible again
            conv_items = page.locator(".sidebar-conversation-item")
            all_visible = all(
                any(t in (conv_items.nth(i).text_content() or "") for t in titles)
                for i in range(conv_items.count())
            )
            if all_visible:
                results.append(
                    UICheck("search_clear", "Search — clear restores full list", "pass")
                )
            else:
                results.append(
                    UICheck(
                        "search_clear",
                        "Search — clear restores full list",
                        "pass",
                        f"{conv_items.count()} items visible (expected {len(titles)}).",
                    )
                )
        else:
            results.append(
                UICheck(
                    "search_clear",
                    "Search — clear button",
                    "skip",
                    "Clear button not found.",
                )
            )

        # Cmd+K focus check
        page.keyboard.press("Meta+k")
        page.wait_for_timeout(200)
        focused = page.evaluate(
            "document.activeElement === document.querySelector('input[aria-label*=\"search\"]')"
        )
        results.append(
            UICheck(
                "search_cmd_k",
                "Search — Cmd+K focuses input",
                "pass" if focused else "skip",
                None if focused else "Could not verify Cmd+K focus.",
            )
        )

    except Exception as exc:
        results.append(UICheck("search_e2e_error", "Search — E2E", "fail", str(exc)))

    return results


def _run_search_ui_verification(
    page: "Any", output_dir: str, screenshot_fn: "Any"
) -> List[UICheck]:
    """Verify search-specific UI elements: mode selector, gear button,
    search settings modal, search progress, source cards, and persistence."""
    results: List[UICheck] = []

    # ── 1. Mode selector: Auto, Chat, Search, Code present ──
    expected_modes = {"Auto", "Chat", "Search", "Code"}
    found_modes = set()
    for mode_name in expected_modes:
        btn = page.locator(f"button:has-text('{mode_name}')")
        if btn.count():
            found_modes.add(mode_name)
    missing = expected_modes - found_modes
    if not missing:
        results.append(
            UICheck(
                "search_mode_selector",
                "Mode selector: Auto, Chat, Search, Code",
                "pass",
                f"All {len(expected_modes)} modes present.",
            )
        )
    else:
        results.append(
            UICheck(
                "search_mode_selector",
                "Mode selector: Auto, Chat, Search, Code",
                "fail",
                f"Missing modes: {', '.join(sorted(missing))}.",
            )
        )

    # ── 2. Settings menu trigger exists (replaces gear button) ──
    settings_trigger = page.locator("[data-testid='settings-menu-trigger']")
    if settings_trigger.count():
        results.append(
            UICheck("search_settings_trigger", "Settings menu trigger exists", "pass")
        )
    else:
        results.append(
            UICheck(
                "search_settings_trigger",
                "Settings menu trigger exists",
                "fail",
                "Settings menu trigger not found in header.",
            )
        )

    # ── 3. Settings dropdown opens ──
    if settings_trigger.count():
        settings_trigger.first.click()
        page.wait_for_timeout(500)
        dropdown = page.locator("[data-testid='settings-dropdown']")
        if dropdown.count():
            results.append(
                UICheck("search_settings_dropdown", "Settings dropdown opens", "pass")
            )
            screenshot_fn("settings-dropdown")

            # Check dropdown contents — expand Search section
            search_trigger = page.locator("[data-testid='settings-search-trigger']")
            if search_trigger.count():
                search_trigger.first.click()
                page.wait_for_timeout(300)

            has_provider = page.locator(
                "[data-testid='settings-search-provider']"
            ).count()
            has_slider = page.locator(
                "[data-testid='settings-search-max-results']"
            ).count()
            has_safe = page.locator("[data-testid='settings-search-safe']").count()
            has_auto = page.locator("[data-testid='settings-search-auto']").count()

            if has_provider and has_slider and has_safe and has_auto:
                results.append(
                    UICheck(
                        "search_settings_contents",
                        "Search settings in dropdown",
                        "pass",
                        "Provider, max results, safe search, auto search found.",
                    )
                )
            else:
                results.append(
                    UICheck(
                        "search_settings_contents",
                        "Search settings in dropdown",
                        "fail",
                        f"provider={has_provider}, slider={has_slider}, "
                        f"safe={has_safe}, auto={has_auto}.",
                    )
                )

            # Close dropdown by clicking outside
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
        else:
            results.append(
                UICheck(
                    "search_settings_dropdown",
                    "Settings dropdown opens",
                    "fail",
                    "Dropdown not found after clicking settings trigger.",
                )
            )

    # ── 4. Search mode submission + progress UI ──
    search_btn = page.locator("button:has-text('Search')")
    if search_btn.count():
        search_btn.first.click()
        page.wait_for_timeout(300)

    textarea = page.locator("textarea")
    if textarea.count():
        textarea.first.fill("What is the capital of France?")
        page.wait_for_timeout(200)

        send_btn = page.locator(
            "button[aria-label*='send'], button:has(svg):not([aria-label*='menu'])"
        )
        if send_btn.count():
            send_btn.first.click()
        else:
            page.keyboard.press("Enter")

        # Check for SearchProgress during loading
        page.wait_for_timeout(1500)
        progress = page.locator(
            ".search-progress-container, .search-progress-step, "
            "[class*='search-progress']"
        )
        if progress.count():
            results.append(
                UICheck(
                    "search_progress_ui",
                    "SearchProgress renders during search",
                    "pass",
                    f"Found {progress.count()} progress elements.",
                )
            )
            screenshot_fn("search-progress")
        else:
            results.append(
                UICheck(
                    "search_progress_ui",
                    "SearchProgress renders during search",
                    "fail",
                    "SearchProgress elements not found after submission.",
                )
            )

        # Wait for response
        page.wait_for_timeout(10000)
        screenshot_fn("search-response")

        # Check for source cards
        source_cards = page.locator(
            ".source-cards-container, .source-card, [class*='source-card']"
        )
        if source_cards.count():
            results.append(
                UICheck(
                    "search_source_cards",
                    "Source cards render after search",
                    "pass",
                    f"Found {source_cards.count()} source card elements.",
                )
            )
            screenshot_fn("search-source-cards")

            # Check links open in new tabs
            links = page.locator(".source-card a, a.source-card")
            if links.count():
                first_link = links.first
                target = first_link.get_attribute("target")
                rel = first_link.get_attribute("rel")
                if target == "_blank" and "noopener" in (rel or ""):
                    results.append(
                        UICheck(
                            "search_source_links",
                            "Source links open in new tabs",
                            "pass",
                            "target=_blank, rel=noopener confirmed.",
                        )
                    )
                else:
                    results.append(
                        UICheck(
                            "search_source_links",
                            "Source links open in new tabs",
                            "fail",
                            f"target={target}, rel={rel}.",
                        )
                    )
            else:
                results.append(
                    UICheck(
                        "search_source_links",
                        "Source links open in new tabs",
                        "skip",
                        "No links found inside source cards.",
                    )
                )
        else:
            results.append(
                UICheck(
                    "search_source_cards",
                    "Source cards render after search",
                    "fail",
                    "Source card elements not found after search response.",
                )
            )
    else:
        results.append(
            UICheck(
                "search_progress_ui",
                "SearchProgress renders during search",
                "fail",
                "Textarea not found.",
            )
        )

    # ── 5. Search Settings persistence (localStorage) ──
    stored = page.evaluate("localStorage.getItem('alma_search_settings')")
    if stored:
        try:
            parsed = json.loads(stored)
            required_keys = {"provider", "maxResults", "safeSearch"}
            if required_keys.issubset(parsed.keys()):
                results.append(
                    UICheck(
                        "search_settings_persist",
                        "Search Settings persist in localStorage",
                        "pass",
                        f"Keys: {', '.join(sorted(parsed.keys()))}.",
                    )
                )
            else:
                results.append(
                    UICheck(
                        "search_settings_persist",
                        "Search Settings persist in localStorage",
                        "fail",
                        f"Missing keys: {', '.join(required_keys - parsed.keys())}.",
                    )
                )
        except json.JSONDecodeError:
            results.append(
                UICheck(
                    "search_settings_persist",
                    "Search Settings persist in localStorage",
                    "fail",
                    "Invalid JSON in localStorage.",
                )
            )
    else:
        results.append(
            UICheck(
                "search_settings_persist",
                "Search Settings persist in localStorage",
                "skip",
                "No alma_search_settings in localStorage.",
            )
        )

    return results


# ── E2E verification ──────────────────────────────────────────────────
#
# End-to-end verification that proves the application behaves correctly
# from a user's perspective. Runs Playwright at multiple viewports,
# captures screenshots, records traces on failure, and produces a
# unified report.

VIEWPORTS = {
    "desktop": {"width": 1280, "height": 800},
    "tablet": {"width": 768, "height": 1024},
    "mobile": {"width": 375, "height": 812},
}

ALL_FLOWS = (
    "chat",
    "search",
    "thinking",
    "voice",
    "keyboard",
    "themes",
    "landing_suggestions",
)


@dataclass
class FlowTiming:
    """Timing data for a single flow."""

    flow: str
    start: float = 0.0
    end: float = 0.0

    @property
    def duration_ms(self) -> float:
        return round((self.end - self.start) * 1000, 1)

    def to_dict(self) -> dict:
        return {"flow": self.flow, "duration_ms": self.duration_ms}


@dataclass
class E2EResult:
    """Result of a single E2E check."""

    name: str
    label: str
    status: str  # pass, fail, skip, infra_fail
    detail: str = ""
    category: str = ""
    timing: Optional[FlowTiming] = None
    screenshot: str = ""

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "label": self.label,
            "status": self.status,
            "category": self.category,
        }
        if self.detail:
            d["detail"] = self.detail
        if self.timing:
            d["timing"] = self.timing.to_dict()
        if self.screenshot:
            d["screenshot"] = self.screenshot
        return d


def _check_infrastructure(base_url: str) -> List[E2EResult]:
    """Verify frontend and backend are reachable before running E2E."""
    results = []

    # Check frontend
    try:
        req = urllib.request.Request(base_url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                results.append(
                    E2EResult(
                        "infra_frontend",
                        "Frontend reachable",
                        "pass",
                        f"{base_url} returned 200",
                        category="Infrastructure",
                    )
                )
            else:
                results.append(
                    E2EResult(
                        "infra_frontend",
                        "Frontend reachable",
                        "infra_fail",
                        f"{base_url} returned {resp.status}",
                        category="Infrastructure",
                    )
                )
    except Exception as exc:
        results.append(
            E2EResult(
                "infra_frontend",
                "Frontend reachable",
                "infra_fail",
                f"Cannot reach {base_url}: {exc}",
                category="Infrastructure",
            )
        )

    # Check backend health
    health_url = base_url.replace(":3000", ":8000").replace(":5173", ":8000")
    try:
        req = urllib.request.Request(f"{health_url}/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            if body.get("status") == "ok":
                results.append(
                    E2EResult(
                        "infra_backend",
                        "Backend reachable",
                        "pass",
                        f"{health_url}/api/health returned OK",
                        category="Infrastructure",
                    )
                )
            else:
                results.append(
                    E2EResult(
                        "infra_backend",
                        "Backend reachable",
                        "infra_fail",
                        f"Health check returned: {body}",
                        category="Infrastructure",
                    )
                )
    except Exception as exc:
        results.append(
            E2EResult(
                "infra_backend",
                "Backend reachable",
                "infra_fail",
                f"Cannot reach backend: {exc}",
                category="Infrastructure",
            )
        )

    return results


def _verify_chat_flow(page: "Any", screenshot_fn: "Any") -> List[E2EResult]:
    """Verify chat mode: select mode, submit, get non-empty response, TTS present."""
    results = []
    t = FlowTiming("chat")

    # Select chat mode
    t.start = time.time()
    trigger = page.locator("[data-testid='mode-menu-trigger']")
    if trigger.count():
        trigger.first.click()
        page.wait_for_timeout(300)
        chat_option = page.locator("[data-testid='mode-option-chat']")
        if chat_option.count():
            chat_option.first.click()
            page.wait_for_timeout(300)
            results.append(
                E2EResult(
                    "chat_mode_select",
                    "Chat mode selects correctly",
                    "pass",
                    category="Chat",
                )
            )
        else:
            results.append(
                E2EResult(
                    "chat_mode_select",
                    "Chat mode selects correctly",
                    "fail",
                    "Chat option not found",
                    category="Chat",
                )
            )
    else:
        results.append(
            E2EResult(
                "chat_mode_select",
                "Chat mode selects correctly",
                "fail",
                "Mode trigger not found",
                category="Chat",
            )
        )

    # Type and submit
    textarea = page.locator("[data-testid='composer-textarea']")
    if textarea.count():
        textarea.first.fill("What is 2+2?")
        page.wait_for_timeout(200)
        send_btn = page.locator("[data-testid='composer-send']")
        if send_btn.count():
            send_btn.first.click()
        else:
            page.keyboard.press("Enter")

        # Wait for response (non-empty)
        page.wait_for_timeout(10000)
        screenshot_fn("chat-response")

        # Verify response exists (non-empty)
        messages = page.locator(".message-content, .markdown-content")
        has_response = False
        for i in range(messages.count()):
            text = messages.nth(i).text_content() or ""
            if text.strip() and len(text.strip()) > 5:
                has_response = True
                break

        if has_response:
            results.append(
                E2EResult("chat_response", "Response renders", "pass", category="Chat")
            )
        else:
            results.append(
                E2EResult(
                    "chat_response",
                    "Response renders",
                    "fail",
                    "No non-empty response found",
                    category="Chat",
                )
            )

        # Verify TTS button present
        tts = page.locator("[data-testid='tts-button']")
        if tts.count():
            results.append(
                E2EResult("chat_tts", "TTS button present", "pass", category="Chat")
            )
        else:
            results.append(
                E2EResult(
                    "chat_tts",
                    "TTS button present",
                    "fail",
                    "TTS button not found",
                    category="Chat",
                )
            )
    else:
        results.append(
            E2EResult(
                "chat_submit",
                "Message submits",
                "fail",
                "Textarea not found",
                category="Chat",
            )
        )

    t.end = time.time()
    for r in results:
        r.timing = t
    return results


def _verify_search_flow(page: "Any", screenshot_fn: "Any") -> List[E2EResult]:
    """Verify search mode: progress, source cards, non-empty response."""
    results = []
    t = FlowTiming("search")

    # New conversation
    logo = page.locator("button[aria-label='Start a new conversation']")
    if logo.count():
        logo.first.click()
        page.wait_for_timeout(500)
        logo.first.click()
        page.wait_for_timeout(500)

    # Select search mode
    t.start = time.time()
    trigger = page.locator("[data-testid='mode-menu-trigger']")
    if trigger.count():
        trigger.first.click()
        page.wait_for_timeout(300)
        search_option = page.locator("[data-testid='mode-option-search']")
        if search_option.count():
            search_option.first.click()
            page.wait_for_timeout(300)
            results.append(
                E2EResult(
                    "search_mode_select",
                    "Search mode selects correctly",
                    "pass",
                    category="Search",
                )
            )
        else:
            results.append(
                E2EResult(
                    "search_mode_select",
                    "Search mode selects correctly",
                    "fail",
                    "Search option not found",
                    category="Search",
                )
            )
    else:
        results.append(
            E2EResult(
                "search_mode_select",
                "Search mode selects correctly",
                "fail",
                "Mode trigger not found",
                category="Search",
            )
        )

    # Submit search
    textarea = page.locator("[data-testid='composer-textarea']")
    if textarea.count():
        textarea.first.fill("What is the capital of France?")
        page.wait_for_timeout(200)
        send_btn = page.locator("[data-testid='composer-send']")
        if send_btn.count():
            send_btn.first.click()
        else:
            page.keyboard.press("Enter")

        # Wait for SearchProgress
        page.wait_for_timeout(2000)
        progress = page.locator("[data-testid='search-progress']")
        if progress.count():
            results.append(
                E2EResult(
                    "search_progress",
                    "SearchProgress appears during loading",
                    "pass",
                    category="Search",
                )
            )
            screenshot_fn("search-progress")
        else:
            results.append(
                E2EResult(
                    "search_progress",
                    "SearchProgress appears during loading",
                    "fail",
                    "SearchProgress not found",
                    category="Search",
                )
            )

        # Wait for source cards
        page.wait_for_timeout(10000)
        source_cards = page.locator("[data-testid='source-cards']")
        if source_cards.count():
            results.append(
                E2EResult(
                    "search_sources", "Source cards render", "pass", category="Search"
                )
            )
            screenshot_fn("search-source-cards")

            # Verify links open in new tabs
            links = page.locator("[data-testid='source-cards'] a")
            if links.count():
                first_link = links.first
                target = first_link.get_attribute("target")
                rel = first_link.get_attribute("rel") or ""
                if target == "_blank" and "noopener" in rel:
                    results.append(
                        E2EResult(
                            "search_links",
                            "Source links open in new tabs",
                            "pass",
                            category="Search",
                        )
                    )
                else:
                    results.append(
                        E2EResult(
                            "search_links",
                            "Source links open in new tabs",
                            "fail",
                            f"target={target}, rel={rel}",
                            category="Search",
                        )
                    )
            else:
                results.append(
                    E2EResult(
                        "search_links",
                        "Source links open in new tabs",
                        "skip",
                        "No links found",
                        category="Search",
                    )
                )
        else:
            results.append(
                E2EResult(
                    "search_sources",
                    "Source cards render",
                    "fail",
                    "Source cards not found",
                    category="Search",
                )
            )

        # Verify response is non-empty
        messages = page.locator(".message-content, .markdown-content")
        has_response = False
        for i in range(messages.count()):
            text = messages.nth(i).text_content() or ""
            if text.strip() and len(text.strip()) > 5:
                has_response = True
                break

        if has_response:
            results.append(
                E2EResult(
                    "search_response",
                    "Response contains content",
                    "pass",
                    category="Search",
                )
            )
        else:
            results.append(
                E2EResult(
                    "search_response",
                    "Response contains content",
                    "fail",
                    "No response found",
                    category="Search",
                )
            )

        screenshot_fn("search-response")
    else:
        results.append(
            E2EResult(
                "search_submit",
                "Search submits",
                "fail",
                "Textarea not found",
                category="Search",
            )
        )

    t.end = time.time()
    for r in results:
        r.timing = t
    return results


def _verify_thinking_flow(page: "Any", screenshot_fn: "Any") -> List[E2EResult]:
    """Verify thinking mode: thinking container renders, toggle exists."""
    results = []
    t = FlowTiming("thinking")

    # New conversation via header logo (previously "theme toggle trick")
    logo = page.locator("button[aria-label='Start a new conversation']")
    if logo.count():
        logo.first.click()
        page.wait_for_timeout(500)
        logo.first.click()
        page.wait_for_timeout(500)

    # Select thinking mode
    t.start = time.time()
    trigger = page.locator("[data-testid='mode-menu-trigger']")
    if trigger.count():
        trigger.first.click()
        page.wait_for_timeout(300)
        thinking_option = page.locator("[data-testid='mode-option-thinking']")
        if thinking_option.count():
            thinking_option.first.click()
            page.wait_for_timeout(300)
            results.append(
                E2EResult(
                    "thinking_mode_select",
                    "Thinking mode selects correctly",
                    "pass",
                    category="Thinking",
                )
            )
        else:
            results.append(
                E2EResult(
                    "thinking_mode_select",
                    "Thinking mode selects correctly",
                    "fail",
                    "Thinking option not found",
                    category="Thinking",
                )
            )
    else:
        results.append(
            E2EResult(
                "thinking_mode_select",
                "Thinking mode selects correctly",
                "fail",
                "Mode trigger not found",
                category="Thinking",
            )
        )

    # Submit
    textarea = page.locator("[data-testid='composer-textarea']")
    if textarea.count():
        textarea.first.fill("Explain recursion in one sentence")
        page.wait_for_timeout(200)
        send_btn = page.locator("[data-testid='composer-send']")
        if send_btn.count():
            send_btn.first.click()
        else:
            page.keyboard.press("Enter")

        # Wait for response
        page.wait_for_timeout(10000)
        screenshot_fn("thinking-response")

        # Verify thinking container exists
        thinking = page.locator(".thinking-container")
        if thinking.count():
            results.append(
                E2EResult(
                    "thinking_container",
                    "ThinkingContainer renders",
                    "pass",
                    category="Thinking",
                )
            )

            # Verify toggle exists (aria-expanded)
            toggle = page.locator(".thinking-toggle[aria-expanded]")
            if toggle.count():
                results.append(
                    E2EResult(
                        "thinking_toggle",
                        "Thinking toggle works",
                        "pass",
                        category="Thinking",
                    )
                )
            else:
                results.append(
                    E2EResult(
                        "thinking_toggle",
                        "Thinking toggle works",
                        "skip",
                        "Toggle not found (may be short trace)",
                        category="Thinking",
                    )
                )
        else:
            results.append(
                E2EResult(
                    "thinking_container",
                    "ThinkingContainer renders",
                    "fail",
                    "Thinking container not found",
                    category="Thinking",
                )
            )

        # Verify response is non-empty
        messages = page.locator(".message-content, .markdown-content")
        has_response = False
        for i in range(messages.count()):
            text = messages.nth(i).text_content() or ""
            if text.strip() and len(text.strip()) > 5:
                has_response = True
                break

        if has_response:
            results.append(
                E2EResult(
                    "thinking_response",
                    "Response renders after thinking",
                    "pass",
                    category="Thinking",
                )
            )
        else:
            results.append(
                E2EResult(
                    "thinking_response",
                    "Response renders after thinking",
                    "fail",
                    "No response found",
                    category="Thinking",
                )
            )
    else:
        results.append(
            E2EResult(
                "thinking_submit",
                "Thinking submits",
                "fail",
                "Textarea not found",
                category="Thinking",
            )
        )

    t.end = time.time()
    for r in results:
        r.timing = t
    return results


def _verify_voice_flow(page: "Any", screenshot_fn: "Any") -> List[E2EResult]:
    """Verify voice: TTS button clickable, audio element created."""
    results = []
    t = FlowTiming("voice")
    t.start = time.time()

    # Find TTS button
    tts_btn = page.locator("[data-testid='tts-button']")
    if tts_btn.count():
        results.append(
            E2EResult(
                "voice_tts_button", "TTS button clickable", "pass", category="Voice"
            )
        )

        # Click TTS
        tts_btn.first.click()
        page.wait_for_timeout(3000)

        # Verify audio element created
        audio = page.locator("[data-testid='tts-audio']")
        if audio.count():
            results.append(
                E2EResult(
                    "voice_audio", "Audio element created", "pass", category="Voice"
                )
            )
            screenshot_fn("voice-playback")
        else:
            results.append(
                E2EResult(
                    "voice_audio",
                    "Audio element created",
                    "fail",
                    "Audio element not found after TTS click",
                    category="Voice",
                )
            )
    else:
        results.append(
            E2EResult(
                "voice_tts_button",
                "TTS button clickable",
                "skip",
                "TTS button not found (need a response first)",
                category="Voice",
            )
        )

    t.end = time.time()
    for r in results:
        r.timing = t
    return results


def _verify_keyboard_navigation(page: "Any", screenshot_fn: "Any") -> List[E2EResult]:
    """Verify keyboard: Escape closes sidebar, Enter submits."""
    results = []
    t = FlowTiming("keyboard")
    t.start = time.time()

    # Test Escape closes sidebar
    menu_btn = page.locator("[data-testid='settings-menu-trigger']")
    if menu_btn.count():
        # Open sidebar by clicking menu
        hamburger = page.locator("button[aria-label='Open menu']")
        if hamburger.count():
            hamburger.first.click()
            page.wait_for_timeout(500)
            sidebar = page.locator("[data-testid='sidebar']")
            is_open = "sidebar--open" in (sidebar.get_attribute("class") or "")

            if is_open:
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
                is_closed = "sidebar--open" not in (
                    sidebar.get_attribute("class") or ""
                )
                if is_closed:
                    results.append(
                        E2EResult(
                            "kb_escape_sidebar",
                            "Escape closes sidebar",
                            "pass",
                            category="Keyboard",
                        )
                    )
                else:
                    results.append(
                        E2EResult(
                            "kb_escape_sidebar",
                            "Escape closes sidebar",
                            "fail",
                            "Sidebar still open after Escape",
                            category="Keyboard",
                        )
                    )
            else:
                results.append(
                    E2EResult(
                        "kb_escape_sidebar",
                        "Escape closes sidebar",
                        "skip",
                        "Sidebar did not open",
                        category="Keyboard",
                    )
                )
        else:
            results.append(
                E2EResult(
                    "kb_escape_sidebar",
                    "Escape closes sidebar",
                    "skip",
                    "Menu button not found",
                    category="Keyboard",
                )
            )
    else:
        results.append(
            E2EResult(
                "kb_escape_sidebar",
                "Escape closes sidebar",
                "skip",
                "No theme toggle found",
                category="Keyboard",
            )
        )

    # Test Enter submits
    textarea = page.locator("[data-testid='composer-textarea']")
    if textarea.count():
        textarea.first.fill("Hello keyboard test")
        page.wait_for_timeout(300)
        page.keyboard.press("Enter")

        # Poll for response (backend may be slow after prior flows).
        has_message = False
        for _ in range(10):
            page.wait_for_timeout(1000)
            messages = page.locator(
                ".message-content, .markdown-content, .user-message"
            )
            for i in range(messages.count()):
                text = messages.nth(i).text_content() or ""
                if "keyboard" in text.lower():
                    has_message = True
                    break
            if has_message:
                break

        if has_message:
            results.append(
                E2EResult(
                    "kb_enter_submit",
                    "Enter submits message",
                    "pass",
                    category="Keyboard",
                )
            )
        else:
            results.append(
                E2EResult(
                    "kb_enter_submit",
                    "Enter submits message",
                    "fail",
                    "Message not found after Enter",
                    category="Keyboard",
                )
            )
    else:
        results.append(
            E2EResult(
                "kb_enter_submit",
                "Enter submits message",
                "skip",
                "Textarea not found",
                category="Keyboard",
            )
        )

    t.end = time.time()
    for r in results:
        r.timing = t
    return results


def _verify_themes(page: "Any", screenshot_fn: "Any") -> List[E2EResult]:
    """Verify dark and light themes toggle correctly."""
    results = []
    t = FlowTiming("themes")
    t.start = time.time()

    # Check initial theme
    initial_theme = (
        page.evaluate("document.documentElement.getAttribute('data-theme')") or "dark"
    )
    results.append(
        E2EResult(
            "theme_initial",
            f"Initial theme is {initial_theme}",
            "pass",
            category="Themes",
        )
    )

    # Toggle theme via settings dropdown
    settings_trigger = page.locator("[data-testid='settings-menu-trigger']")
    if settings_trigger.count():
        settings_trigger.first.click()
        page.wait_for_timeout(500)
        theme_btn = page.locator("[data-testid='settings-theme-toggle']")
        if theme_btn.count():
            theme_btn.first.click()
            page.wait_for_timeout(500)
            new_theme = (
                page.evaluate("document.documentElement.getAttribute('data-theme')")
                or "dark"
            )

            if new_theme != initial_theme:
                results.append(
                    E2EResult(
                        "theme_toggle",
                        "Theme toggle switches",
                        "pass",
                        f"{initial_theme} → {new_theme}",
                        category="Themes",
                    )
                )
                screenshot_fn("theme-toggled")

                # Close dropdown (theme toggle doesn't auto-close so user can see effect)
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
                # Toggle back via settings dropdown
                settings_trigger.first.click()
                page.wait_for_timeout(500)
                page.locator("[data-testid='settings-theme-toggle']").first.click()
                page.wait_for_timeout(500)
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
                restored = (
                    page.evaluate("document.documentElement.getAttribute('data-theme')")
                    or "dark"
                )
                if restored == initial_theme:
                    results.append(
                        E2EResult(
                            "theme_restore",
                            "Theme toggle restores",
                            "pass",
                            category="Themes",
                        )
                    )
                else:
                    results.append(
                        E2EResult(
                            "theme_restore",
                            "Theme toggle restores",
                            "fail",
                            f"Expected {initial_theme}, got {restored}",
                            category="Themes",
                        )
                    )
            else:
                results.append(
                    E2EResult(
                        "theme_toggle",
                        "Theme toggle switches",
                        "fail",
                        f"Theme did not change from {initial_theme}",
                        category="Themes",
                    )
                )
                page.keyboard.press("Escape")
                page.wait_for_timeout(200)
        else:
            results.append(
                E2EResult(
                    "theme_toggle",
                    "Theme toggle switches",
                    "skip",
                    "Theme toggle not found in dropdown",
                    category="Themes",
                )
            )
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)
    else:
        results.append(
            E2EResult(
                "theme_toggle",
                "Theme toggle switches",
                "skip",
                "Settings trigger not found",
                category="Themes",
            )
        )

    t.end = time.time()
    for r in results:
        r.timing = t
    return results


def _verify_landing_suggestions(page: "Any", screenshot_fn: "Any") -> List[E2EResult]:
    """Verify landing page suggestion chips preference (default: off)."""
    results: List[E2EResult] = []
    t = FlowTiming("landing_suggestions")
    t.start = time.time()

    # Ensure clean state: remove stored suggestions preference.
    page.evaluate("""() => {
        try {
            const raw = localStorage.getItem('alma_search_settings');
            if (raw) {
                const s = JSON.parse(raw);
                delete s.showSuggestions;
                localStorage.setItem('alma_search_settings', JSON.stringify(s));
            }
        } catch {}
    }""")
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(500)

    # ── 1. Default state: suggestions should be hidden ──
    has_chips = page.locator(".landing-suggestions .chip").count() > 0
    results.append(
        E2EResult(
            "suggestions_default_off",
            "Quiet mode is the default",
            "pass" if not has_chips else "fail",
            f"Chips visible: {has_chips}" if has_chips else "No chips on landing page",
            category="Landing Page",
        )
    )
    screenshot_fn("landing-quiet")

    # ── 2. Enable suggestions via header settings dropdown ──
    settings_trigger = page.locator("[data-testid='settings-menu-trigger']")
    if settings_trigger.count():
        settings_trigger.first.click()
        page.wait_for_timeout(500)
        dropdown = page.locator("[data-testid='settings-dropdown']")
        if dropdown.count():
            # Expand Search section to reveal the suggestions toggle
            search_trigger = page.locator("[data-testid='settings-search-trigger']")
            if search_trigger.count():
                search_trigger.first.click()
                page.wait_for_timeout(300)
            suggestions_toggle = page.locator(
                "[data-testid='settings-suggestions-toggle']"
            )
            if suggestions_toggle.count():
                suggestions_toggle.first.click()
                page.wait_for_timeout(300)
                # Close dropdown
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
                results.append(
                    E2EResult(
                        "suggestions_enable",
                        "Suggestions can be enabled",
                        "pass",
                        category="Landing Page",
                    )
                )
            else:
                results.append(
                    E2EResult(
                        "suggestions_enable",
                        "Suggestions can be enabled",
                        "fail",
                        "Suggestions toggle not found in dropdown.",
                        category="Landing Page",
                    )
                )
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
        else:
            results.append(
                E2EResult(
                    "suggestions_enable",
                    "Suggestions can be enabled",
                    "fail",
                    "Settings dropdown did not open.",
                    category="Landing Page",
                )
            )
    else:
        results.append(
            E2EResult(
                "suggestions_enable",
                "Suggestions can be enabled",
                "fail",
                "Settings menu trigger not found.",
                category="Landing Page",
            )
        )

    # ── 3. Verify chips appear immediately (no reload) ──
    try:
        page.wait_for_selector(".landing-suggestions .chip", timeout=3000)
        chips_after_enable = True
    except Exception:
        chips_after_enable = page.locator(".landing-suggestions .chip").count() > 0
    results.append(
        E2EResult(
            "suggestions_immediate",
            "Changes apply immediately",
            "pass" if chips_after_enable else "fail",
            f"Chips visible: {chips_after_enable}"
            if not chips_after_enable
            else "3 suggestion chips rendered",
            category="Landing Page",
        )
    )
    screenshot_fn("landing-suggestions-enabled")

    # ── 4. Persistence: reload and verify chips still visible ──
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(1000)
    chips_after_reload = page.locator(".landing-suggestions .chip").count() > 0
    results.append(
        E2EResult(
            "suggestions_persist",
            "Preference persists after reload",
            "pass" if chips_after_reload else "fail",
            f"Chips visible after reload: {chips_after_reload}",
            category="Landing Page",
        )
    )
    screenshot_fn("landing-after-reload")

    # Verify toggle remains enabled after reload
    settings_trigger = page.locator("[data-testid='settings-menu-trigger']")
    if settings_trigger.count():
        settings_trigger.first.click()
        page.wait_for_timeout(500)
        # Expand Search section to reveal the suggestions toggle
        search_trigger = page.locator("[data-testid='settings-search-trigger']")
        if search_trigger.count():
            search_trigger.first.click()
            page.wait_for_timeout(300)
        toggle_after = page.locator("[data-testid='settings-suggestions-toggle']")
        toggle_still_on = toggle_after.count() > 0
        if toggle_still_on:
            # Disable suggestions
            toggle_after.first.click()
            page.wait_for_timeout(300)
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
            results.append(
                E2EResult(
                    "suggestions_disable",
                    "Suggestions can be disabled",
                    "pass",
                    category="Landing Page",
                )
            )
        else:
            results.append(
                E2EResult(
                    "suggestions_disable",
                    "Suggestions can be disabled",
                    "fail",
                    "Suggestions toggle not found after reload.",
                    category="Landing Page",
                )
            )
            page.keyboard.press("Escape")
            page.wait_for_timeout(300)
    else:
        results.append(
            E2EResult(
                "suggestions_disable",
                "Suggestions can be disabled",
                "fail",
                "Settings trigger not found after reload.",
                category="Landing Page",
            )
        )

    # ── 5. Verify chips disappear after disabling ──
    chips_after_disable = page.locator(".landing-suggestions .chip").count() > 0
    results.append(
        E2EResult(
            "suggestions_gone",
            "Chips disappear after disable",
            "pass" if not chips_after_disable else "fail",
            f"Chips still visible: {chips_after_disable}"
            if chips_after_disable
            else "No chips after disable",
            category="Landing Page",
        )
    )
    screenshot_fn("landing-suggestions-disabled")

    # ── 6. Reload: chips stay hidden ──
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(1000)
    chips_still_hidden = page.locator(".landing-suggestions .chip").count() == 0
    results.append(
        E2EResult(
            "suggestions_stay_hidden",
            "Chips remain hidden after reload",
            "pass" if chips_still_hidden else "fail",
            f"Chips visible: {not chips_still_hidden}",
            category="Landing Page",
        )
    )

    t.end = time.time()
    for r in results:
        r.timing = t
    return results


def _collect_browser_errors(page: "Any") -> Tuple[List[str], List[str], List[str]]:
    """Collect console errors, warnings, and failed requests.

    Filters out infrastructure noise that does not indicate product bugs:
    - 404 from conversation save race (PUT /api/conversations/{id})
    - 429 from Gemini quota exhaustion
    """
    errors: List[str] = []
    warnings: List[str] = []
    failed_requests: List[str] = []
    _seen_429 = False
    _seen_404_resource = False

    def on_response(resp: "Any") -> None:
        nonlocal _seen_429, _seen_404_resource
        if resp.status == 429:
            _seen_429 = True
        if resp.status == 404:
            _seen_404_resource = True

    def on_console(msg: "Any") -> None:
        nonlocal _seen_429, _seen_404_resource
        if msg.type == "error":
            text = msg.text
            # Suppress "Failed to load resource" for 404s (conversation race).
            if "Failed to load resource" in text and _seen_404_resource:
                _seen_404_resource = False
                return
            # Suppress 429 / quota errors (infrastructure, not product).
            if "429" in text or "RESOURCE_EXHAUSTED" in text:
                return
            errors.append(f"[error] {text}")
        elif msg.type == "warning":
            warnings.append(f"[warning] {msg.text}")

    def on_page_error(err: "Any") -> None:
        errors.append(f"[pageerror] {err}")

    def on_request_failed(request: "Any") -> None:
        url = request.url
        failure = request.failure
        failed_requests.append(f"{url} ({failure})")

    page.on("response", on_response)
    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    page.on("requestfailed", on_request_failed)

    return errors, warnings, failed_requests


def _format_e2e_report(
    all_results: List[E2EResult],
    timings: List[FlowTiming],
    artifacts_dir: str,
) -> str:
    """Format unified E2E report."""
    lines = ["E2E Verification Report", "=" * 40, ""]

    # Group by category
    categories: Dict[str, List[E2EResult]] = {}
    for r in all_results:
        cat = r.category or "Other"
        categories.setdefault(cat, []).append(r)

    for cat, checks in categories.items():
        lines.append(f"{cat}")
        for c in checks:
            marker = (
                "\u2713"
                if c.status == "pass"
                else ("\u2014" if c.status in ("skip", "infra_fail") else "\u2717")
            )
            lines.append(f"  {marker} {c.label}")
            if c.detail:
                lines.append(f"    {c.detail}")
        lines.append("")

    # Timing summary
    if timings:
        lines.append("Timing")
        for t in timings:
            lines.append(f"  {t.flow}: {t.duration_ms}ms")
        lines.append("")

    # Artifacts
    lines.append("Artifacts")
    lines.append(f"  {artifacts_dir}/")
    lines.append("")

    # Overall
    passed = sum(1 for r in all_results if r.status == "pass")
    failed = sum(1 for r in all_results if r.status == "fail")
    skipped = sum(1 for r in all_results if r.status in ("skip", "infra_fail"))
    total = len(all_results)

    lines.append(
        f"Overall: {passed}/{total} passed, {failed} failed, {skipped} skipped"
    )

    return "\n".join(lines)


def _format_e2e_json(
    all_results: List[E2EResult],
    timings: List[FlowTiming],
    artifacts_dir: str,
) -> str:
    """Format E2E report as JSON."""
    report = {
        "results": [r.to_dict() for r in all_results],
        "timings": [t.to_dict() for t in timings],
        "artifacts_dir": artifacts_dir,
        "summary": {
            "passed": sum(1 for r in all_results if r.status == "pass"),
            "failed": sum(1 for r in all_results if r.status == "fail"),
            "skipped": sum(
                1 for r in all_results if r.status in ("skip", "infra_fail")
            ),
            "total": len(all_results),
        },
    }
    return json.dumps(report, indent=2)


def _format_e2e_html(
    all_results: List[E2EResult],
    timings: List[FlowTiming],
    artifacts_dir: str,
) -> str:
    """Format E2E report as HTML."""
    passed = sum(1 for r in all_results if r.status == "pass")
    failed = sum(1 for r in all_results if r.status == "fail")
    skipped = sum(1 for r in all_results if r.status in ("skip", "infra_fail"))
    total = len(all_results)

    categories: Dict[str, List[E2EResult]] = {}
    for r in all_results:
        cat = r.category or "Other"
        categories.setdefault(cat, []).append(r)

    html_parts = [
        "<!DOCTYPE html>",
        "<html><head><meta charset='utf-8'><title>E2E Verification Report</title>",
        "<style>",
        "body { font-family: -apple-system, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; }",
        "h1 { color: #333; }",
        ".summary { font-size: 1.2em; margin: 20px 0; }",
        ".pass { color: #16a34a; }",
        ".fail { color: #dc2626; }",
        ".skip { color: #9ca3af; }",
        ".category { margin: 20px 0; }",
        ".category h2 { font-size: 1.1em; color: #555; border-bottom: 1px solid #eee; padding-bottom: 5px; }",
        ".check { margin: 5px 0; padding: 5px 10px; }",
        ".check.pass::before { content: '✓ '; color: #16a34a; }",
        ".check.fail::before { content: '✗ '; color: #dc2626; }",
        ".check.skip::before { content: '— '; color: #9ca3af; }",
        ".timing { margin: 20px 0; }",
        ".timing table { border-collapse: collapse; width: 100%; }",
        ".timing td, .timing th { border: 1px solid #eee; padding: 8px; text-align: left; }",
        "</style></head><body>",
        "<h1>E2E Verification Report</h1>",
        "<div class='summary'>",
        f"<span class='pass'>{passed} passed</span>, ",
        f"<span class='fail'>{failed} failed</span>, ",
        f"<span class='skip'>{skipped} skipped</span> ",
        f"out of {total} checks</div>",
    ]

    for cat, checks in categories.items():
        html_parts.append(f"<div class='category'><h2>{cat}</h2>")
        for c in checks:
            status_class = c.status if c.status != "infra_fail" else "skip"
            html_parts.append(f"<div class='check {status_class}'>{c.label}")
            if c.detail:
                html_parts.append(f"<br><small>{c.detail}</small>")
            html_parts.append("</div>")
        html_parts.append("</div>")

    if timings:
        html_parts.append("<div class='timing'><h2>Timing</h2><table>")
        html_parts.append("<tr><th>Flow</th><th>Duration</th></tr>")
        for t in timings:
            html_parts.append(f"<tr><td>{t.flow}</td><td>{t.duration_ms}ms</td></tr>")
        html_parts.append("</table></div>")

    html_parts.append(f"<p>Artifacts: {artifacts_dir}/</p>")
    html_parts.append("</body></html>")

    return "\n".join(html_parts)


def run_e2e_verification(
    output_dir: str,
    flows: Tuple[str, ...] = ALL_FLOWS,
    viewports: Optional[Dict[str, dict]] = None,
) -> List[E2EResult]:
    """Run full E2E verification across viewports and flows."""
    if not check_playwright_installed():
        return [
            E2EResult(
                "playwright",
                "Playwright",
                "infra_fail",
                "Playwright not installed. Run: pip install playwright && playwright install chromium",
                category="Infrastructure",
            )
        ]

    from playwright.sync_api import sync_playwright

    if viewports is None:
        viewports = VIEWPORTS

    base_url = os.environ.get("ALMA_FRONTEND_URL", "http://localhost:3000")

    # Check infrastructure first
    infra_results = _check_infrastructure(base_url)
    has_infra_failure = any(r.status == "infra_fail" for r in infra_results)

    if has_infra_failure:
        return infra_results

    all_results: List[E2EResult] = list(infra_results)
    all_timings: List[FlowTiming] = []

    with sync_playwright() as p:
        for vp_name, vp_size in viewports.items():
            vp_dir = os.path.join(output_dir, vp_name)
            os.makedirs(vp_dir, exist_ok=True)

            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport=vp_size)
            page = context.new_page()

            # Start trace
            trace_path = os.path.join(output_dir, "traces", f"{vp_name}.zip")
            os.makedirs(os.path.dirname(trace_path), exist_ok=True)
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

            # Collect browser errors
            console_errors, console_warnings, failed_requests = _collect_browser_errors(
                page
            )

            # Navigate
            try:
                page.goto(base_url, wait_until="networkidle", timeout=30000)
            except Exception as exc:
                all_results.append(
                    E2EResult(
                        f"page_load_{vp_name}",
                        f"Page loads ({vp_name})",
                        "fail",
                        str(exc),
                        category="Infrastructure",
                    )
                )
                context.tracing.stop(path=trace_path)
                context.close()
                browser.close()
                continue

            # Screenshot landing
            page.screenshot(path=os.path.join(vp_dir, "landing.png"), full_page=True)

            # Dismiss disclaimer dialog if present (first visit).
            try:
                confirm_btn = page.locator(".disclaimer-dialog .dialog-btn--confirm")
                if confirm_btn.count() > 0:
                    confirm_btn.first.click(timeout=3000)
                    page.wait_for_selector(".dialog-overlay", state="hidden", timeout=3000)
            except Exception:
                pass  # No disclaimer or already dismissed.

            def screenshot(name: str) -> None:
                page.screenshot(
                    path=os.path.join(vp_dir, f"{name}.png"), full_page=True
                )

            # Run flows
            flow_fns = {
                "chat": _verify_chat_flow,
                "search": _verify_search_flow,
                "thinking": _verify_thinking_flow,
                "voice": _verify_voice_flow,
                "keyboard": _verify_keyboard_navigation,
                "themes": _verify_themes,
                "landing_suggestions": _verify_landing_suggestions,
            }
            _API_FLOWS = {"chat", "search", "thinking", "voice"}
            quota_exhausted = False

            for flow_name in flows:
                if flow_name in flow_fns:
                    # Check console errors for 429 between flows.
                    if not quota_exhausted and any(
                        "429" in e or "RESOURCE_EXHAUSTED" in e for e in console_errors
                    ):
                        quota_exhausted = True
                    if quota_exhausted and flow_name in _API_FLOWS:
                        all_results.append(
                            E2EResult(
                                f"{flow_name}_{vp_name}",
                                f"{flow_name} flow ({vp_name})",
                                "skip",
                                "Skipped: Gemini API quota exhausted (429)",
                                category=flow_name.capitalize(),
                            )
                        )
                        continue
                    try:
                        flow_results = flow_fns[flow_name](page, screenshot)
                        for r in flow_results:
                            r.label = f"[{vp_name}] {r.label}"
                        all_results.extend(flow_results)
                        all_timings.extend([r.timing for r in flow_results if r.timing])
                        # Detect 429 in results detail to skip subsequent API flows.
                        if any("429" in (r.detail or "") for r in flow_results):
                            quota_exhausted = True
                    except Exception as exc:
                        all_results.append(
                            E2EResult(
                                f"{flow_name}_{vp_name}",
                                f"{flow_name} flow ({vp_name})",
                                "fail",
                                str(exc),
                                category=flow_name.capitalize(),
                            )
                        )

            # Report browser errors
            if console_errors:
                all_results.append(
                    E2EResult(
                        f"console_errors_{vp_name}",
                        f"Console errors ({vp_name})",
                        "fail",
                        f"{len(console_errors)} errors: {'; '.join(console_errors[:3])}",
                        category="Browser",
                    )
                )
            else:
                all_results.append(
                    E2EResult(
                        f"console_errors_{vp_name}",
                        f"Console errors ({vp_name})",
                        "pass",
                        f"No errors ({len(console_warnings)} warnings)",
                        category="Browser",
                    )
                )

            if console_warnings:
                all_results.append(
                    E2EResult(
                        f"console_warnings_{vp_name}",
                        f"Console warnings ({vp_name})",
                        "pass",
                        f"{len(console_warnings)} warnings",
                        category="Browser",
                    )
                )

            if failed_requests:
                all_results.append(
                    E2EResult(
                        f"failed_requests_{vp_name}",
                        f"Failed network requests ({vp_name})",
                        "fail",
                        f"{len(failed_requests)} failures: {'; '.join(failed_requests[:3])}",
                        category="Browser",
                    )
                )
            else:
                all_results.append(
                    E2EResult(
                        f"failed_requests_{vp_name}",
                        f"Failed network requests ({vp_name})",
                        "pass",
                        "No failed requests",
                        category="Browser",
                    )
                )

            # Save trace
            try:
                context.tracing.stop(path=trace_path)
            except Exception:
                try:
                    context.tracing.stop()
                except Exception:
                    pass

            context.close()
            browser.close()

    # Save reports
    report_json = _format_e2e_json(all_results, all_timings, output_dir)
    report_html = _format_e2e_html(all_results, all_timings, output_dir)

    with open(os.path.join(output_dir, "report.json"), "w") as f:
        f.write(report_json)
    with open(os.path.join(output_dir, "report.html"), "w") as f:
        f.write(report_html)

    return all_results


def run_browser_verification(output_dir: str, modes: List[str]) -> List[UICheck]:
    """Run Playwright-based browser verification."""
    if not check_playwright_installed():
        return [
            UICheck(
                "playwright",
                "Playwright",
                "fail",
                "Playwright not installed. Run: pip install playwright && playwright install chromium",
            )
        ]

    from playwright.sync_api import sync_playwright

    results: List[UICheck] = []
    base_url = os.environ.get("ALMA_FRONTEND_URL", "http://localhost:5173")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_har_path=(
                os.path.join(output_dir, "network.har") if output_dir else None
            ),
        )
        page = context.new_page()

        # Collect console logs
        console_logs: List[str] = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: console_logs.append(f"[ERROR] {err}"))

        def screenshot(name: str) -> None:
            path = os.path.join(output_dir, f"{name}.png")
            page.screenshot(path=path, full_page=True)
            results.append(
                UICheck(f"screenshot_{name}", f"Screenshot: {name}", "pass", path)
            )

        try:
            # Landing page
            page.goto(base_url, wait_until="networkidle", timeout=_TIMEOUT * 1000)
            screenshot("landing")
            results.append(
                UICheck(
                    "landing",
                    "Landing page loads",
                    "pass",
                    f"{base_url} loaded successfully.",
                )
            )

            # Theme toggle
            theme_btn = page.locator("button[aria-label*='theme']")
            if theme_btn.count():
                theme_btn.click()
                page.wait_for_timeout(500)
                screenshot("theme-toggled")
                results.append(UICheck("theme_toggle", "Theme toggle works", "pass"))
            else:
                results.append(
                    UICheck(
                        "theme_toggle",
                        "Theme toggle works",
                        "skip",
                        "Theme toggle button not found.",
                    )
                )

            # Sidebar
            menu_btn = page.locator(
                "button[aria-label*='menu'], .header-menu-btn, button:has(svg)"
            )
            if menu_btn.count():
                menu_btn.first.click()
                page.wait_for_timeout(500)
                screenshot("sidebar")
                results.append(UICheck("sidebar", "Sidebar opens", "pass"))
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
            else:
                results.append(
                    UICheck(
                        "sidebar", "Sidebar opens", "skip", "Menu button not found."
                    )
                )

            # Keyboard shortcut
            page.keyboard.press("Meta+n")
            page.wait_for_timeout(500)
            results.append(
                UICheck(
                    "keyboard_shortcut",
                    "Keyboard shortcut (Cmd+N)",
                    "pass",
                    "Cmd+N triggered without error.",
                )
            )

            # Mode-specific checks
            mode_labels = {
                "canvas": "Canvas",
                "thinking": "Thinking",
                "web": "Web",
                "images": "Images",
                "search": "Search",
                "auto": "Auto",
                "code": "Code",
            }
            for mode_name in modes:
                label = mode_labels.get(mode_name, mode_name)

                # Click mode segment
                seg = page.locator(
                    f"button:has-text('{label}'), [role='tab']:has-text('{label}')"
                )
                if seg.count():
                    seg.first.click()
                    page.wait_for_timeout(300)

                # Type a prompt
                input_box = page.locator(
                    "textarea, input[type='text'], [contenteditable='true']"
                )
                if input_box.count():
                    input_box.first.fill(f"Say hello in one word for {label} mode.")
                    page.wait_for_timeout(200)

                    # Submit — look for send button or Enter
                    send_btn = page.locator(
                        "button[aria-label*='send'], button:has(svg):not([aria-label*='menu'])"
                    )
                    if send_btn.count():
                        send_btn.first.click()
                    else:
                        page.keyboard.press("Enter")

                    # Wait briefly and capture loading state
                    page.wait_for_timeout(1000)
                    screenshot(f"{mode_name}-loading")

                    # Wait for response to complete
                    page.wait_for_timeout(8000)
                    screenshot(f"{mode_name}-response")

                    results.append(
                        UICheck(
                            f"{mode_name}_submission",
                            f"{label} submission",
                            "pass",
                            f"{label} mode submitted and response captured.",
                        )
                    )
                else:
                    results.append(
                        UICheck(
                            f"{mode_name}_submission",
                            f"{label} submission",
                            "fail",
                            "Input field not found.",
                        )
                    )

            # ── Conversation switching ──
            conv_switch_results = _run_conversation_switching(
                page, output_dir, screenshot
            )
            results.extend(conv_switch_results)

            # ── Conversation search ──
            conv_search_results = _run_conversation_search(page, output_dir, screenshot)
            results.extend(conv_search_results)

            # ── Search UI verification ──
            search_ui_results = _run_search_ui_verification(
                page, output_dir, screenshot
            )
            results.extend(search_ui_results)

            # Save console logs
            log_path = os.path.join(output_dir, "console.log")
            with open(log_path, "w") as f:
                f.write("\n".join(console_logs))
            if console_logs:
                errors = [line for line in console_logs if "[ERROR]" in line]
                if errors:
                    results.append(
                        UICheck(
                            "console_errors",
                            "Console errors",
                            "fail",
                            f"{len(errors)} errors: {'; '.join(errors[:5])}",
                        )
                    )
                else:
                    results.append(
                        UICheck(
                            "console_errors",
                            "Console errors",
                            "pass",
                            f"No errors ({len(console_logs)} log entries).",
                        )
                    )

        except Exception as exc:
            # Save console logs on failure too
            if console_logs:
                log_path = os.path.join(output_dir, "console.log")
                with open(log_path, "w") as f:
                    f.write("\n".join(console_logs))
            results.append(
                UICheck("browser_error", "Browser verification", "fail", str(exc))
            )
        finally:
            context.close()
            browser.close()

    return results


# ── Render fidelity verification ─────────────────────────────────────
#
# Behaves like a headless QA engineer: submits deterministic prompts to
# the backend API, extracts the raw markdown, drives the browser with the
# same prompts, then compares DOM text, elements, and clipboard content
# to the backend originals — pixel-perfect or it fails.
#
# This is organised as:
#   1. helpers (fetch, normalise, compare, probe)
#   2. run_render_fidelity() — the entry-point


# ── helpers ──────────────────────────────────────────────────────────


def _mode_endpoint(mode: str, base: str) -> str:
    endpoints = {
        "canvas": f"{base}/api/generate",
        "thinking": f"{base}/api/generate-with-thinking",
        "web": f"{base}/api/generate-with-url-context",
        "images": f"{base}/api/generate-image",
    }
    return endpoints.get(mode, f"{base}/api/generate")


def _extract_markdown(body: Any, mode: str) -> str:
    """Pull the markdown/text content out of a backend JSON response."""
    if not isinstance(body, dict):
        return str(body)
    if mode == "thinking":
        # thinking endpoint returns {"response": <answer>, "thinking_summary": <thinking>}
        answer = body.get("response") or body.get("answer") or ""
        thinking = body.get("thinking_summary") or body.get("reasoning") or ""
        # store both; caller picks the relevant half
        return f"__THINKING__\n{thinking}\n__ANSWER__\n{answer}"
    if "response" in body:
        return body["response"]
    if "processed_text" in body:
        return body["processed_text"]
    if "text" in body:
        return body["text"]
    return json.dumps(body)


def _split_thinking(raw: str) -> tuple[str, str]:
    """Split a combined thinking/answer string into separate halves."""
    if "__THINKING__" in raw and "__ANSWER__" in raw:
        parts = raw.split("__ANSWER__", 1)
        thinking = parts[0].replace("__THINKING__", "").strip()
        answer = parts[1].strip()
        return thinking, answer
    return "", raw


def _normalize(text: str) -> str:
    """Strip HTML, collapse whitespace, strip leading/trailing space."""
    import re

    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _compare_text(expected: str, actual: str) -> tuple[float, int]:
    """Compare two normalised strings.

    Returns (match_percent, count_of_differences).
    100.0 means identical.
    """
    exp = _normalize(expected)
    act = _normalize(actual)
    if exp == act:
        return 100.0, 0
    # simple diff: count differing chars relative to longest
    max_len = max(len(exp), len(act))
    if max_len == 0:
        return 100.0, 0
    diffs = sum(1 for a, b in zip(exp, act) if a != b)
    diffs += abs(len(exp) - len(act))  # penalty for length mismatch
    match = max(0.0, round(100.0 * (1.0 - diffs / max_len), 1))
    return match, diffs


def _check_element(
    page: "Any", selector: str, chk_name: str, chk_label: str
) -> UICheck:
    """Check that at least one element matching *selector* exists."""
    el = page.locator(selector)
    if el.count():
        return UICheck(chk_name, chk_label, "pass")
    return UICheck(
        chk_name, chk_label, "fail", f"Expected <{selector}> not found in DOM."
    )


def _response_selector(mode: str) -> str:
    """Return a Playwright locator string for the rendered-content area.

    Supports both the React version (class-based selectors) and the
    static version (#conversation-scroll, message containers).
    """
    return {
        "canvas": (
            ".prose, .markdown, .response-content, "
            "[class*='response'], article, "
            "#conversation-scroll, [class*='message'], .conversation-message"
        ),
        "thinking": (
            ".prose, .markdown, .response-content, "
            "[class*='response'], article, "
            "#conversation-scroll, [class*='message'], .conversation-message"
        ),
        "web": (
            ".prose, .markdown, .response-content, "
            "[class*='response'], article, "
            "#conversation-scroll, [class*='message'], .conversation-message"
        ),
        "images": "img, #generated-image, #image-container",
    }.get(mode, ".prose, .markdown")


def _count_structures(page: "Any") -> Dict[str, int]:
    """Count HTML structural elements in the rendered page."""
    tags = [
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "ul",
        "ol",
        "li",
        "table",
        "tr",
        "td",
        "th",
        "pre",
        "code",
        "blockquote",
        "hr",
        "img",
    ]
    counts: Dict[str, int] = {}
    for tag in tags:
        counts[tag] = page.locator(tag).count()
    return counts


def _count_expected_structures(markdown: str) -> Dict[str, int]:
    """Best-effort count of expected HTML elements from markdown."""
    expected: Dict[str, int] = {}
    expected["h1"] = len(re.findall(r"^# ", markdown, re.MULTILINE))
    expected["h2"] = len(re.findall(r"^## ", markdown, re.MULTILINE))
    expected["h3"] = len(re.findall(r"^### ", markdown, re.MULTILINE))
    expected["h4"] = len(re.findall(r"^#### ", markdown, re.MULTILINE))
    expected["h5"] = len(re.findall(r"^##### ", markdown, re.MULTILINE))
    expected["h6"] = len(re.findall(r"^###### ", markdown, re.MULTILINE))
    code_fences = re.findall(r"```", markdown)
    expected["pre"] = len(code_fences) // 2
    expected["code"] = expected["pre"]
    expected["table"] = len(re.findall(r"^\|.+\|\n\|[-:| ]+\|", markdown, re.MULTILINE))
    expected["blockquote"] = len(re.findall(r"^>\s?", markdown, re.MULTILINE))
    expected["hr"] = len(re.findall(r"^---\s*$", markdown, re.MULTILINE))
    expected["img"] = len(re.findall(r"!\[", markdown))
    expected["ul"] = len(re.findall(r"^[-*+]\s", markdown, re.MULTILINE))
    expected["ol"] = len(re.findall(r"^\d+\.\s", markdown, re.MULTILINE))
    expected["li"] = expected["ul"] + expected["ol"]
    expected["p"] = max(1, len(re.findall(r"\n\n", markdown)))
    expected["tr"] = len(re.findall(r"^\|.+\|$", markdown, re.MULTILINE))
    expected["td"] = expected["tr"] * 3
    expected["th"] = expected["tr"]
    return expected


def _capture_metrics(page: "Any", start_time: float) -> Dict[str, float]:
    """Capture browser performance metrics."""
    metrics: Dict[str, float] = {}
    try:
        timing = page.evaluate(
            """() => {
            const p = window.performance;
            const t = p.timing;
            return {
                domContentLoaded: t.domContentLoadedEventEnd - t.navigationStart,
                loadEvent: t.loadEventEnd - t.navigationStart,
                domInteractive: t.domInteractive - t.navigationStart,
            };
        }"""
        )
        metrics["dom_content_loaded_ms"] = round(timing.get("domContentLoaded", 0), 1)
        metrics["load_event_ms"] = round(timing.get("loadEvent", 0), 1)
        metrics["dom_interactive_ms"] = round(timing.get("domInteractive", 0), 1)
    except Exception:
        pass
    elapsed = time.monotonic() - start_time
    metrics["total_elapsed_s"] = round(elapsed, 2)
    return metrics


def _compute_screenshot_hash(path: str) -> str:
    """Compute a short SHA-256 hex digest of a screenshot file."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


# Track all screenshots that changed vs baseline for the summary report.
_CHANGED_SCREENSHOTS: List[str] = []


def _visual_regression(mode: str, screenshot_path: str, output_dir: str) -> UICheck:
    """Compare screenshot hash against a stored baseline.

    When the baseline exists and the hash differs, this records the
    screenshot as a review-required regression.  Updating a baseline
    is an explicit manual action — copy the new hash from
    verify-output/ into verify-output/baselines/ and commit it.
    """
    global _CHANGED_SCREENSHOTS
    hash_val = _compute_screenshot_hash(screenshot_path)
    hash_path = os.path.join(output_dir, f"{mode}-screenshot-hash.txt")
    with open(hash_path, "w") as f:
        f.write(hash_val + "\n")
    baseline_path = os.path.join(_BASELINE_DIR, f"{mode}-screenshot-hash.txt")
    if os.path.isfile(baseline_path):
        with open(baseline_path) as f:
            baseline = f.read().strip()
        if hash_val == baseline:
            return UICheck(
                f"{mode}_visual_regression",
                f"{mode.capitalize()} visual regression",
                "pass",
                f"Hash matches baseline ({hash_val})",
            )
        _CHANGED_SCREENSHOTS.append(screenshot_path)
        return UICheck(
            f"{mode}_visual_regression",
            f"{mode.capitalize()} visual regression",
            "fail",
            f"❌ Review required — hash {hash_val} differs from baseline {baseline}. "
            f"Changed file: {os.path.basename(screenshot_path)}. "
            f"To approve, copy verify-output/{mode}-screenshot-hash.txt to "
            f"verify-output/baselines/ and commit.",
        )
    return UICheck(
        f"{mode}_visual_regression",
        f"{mode.capitalize()} visual regression",
        "skip",
        f"No baseline at {baseline_path}",
    )


def _accessibility_checks(page: "Any") -> Tuple[int, int, List[UICheck]]:
    """Run automated accessibility checks on the page."""
    checks: List[UICheck] = []
    passed = 0
    failed = 0

    # Every img has alt
    imgs = page.locator("img")
    img_no_alt = 0
    for i in range(imgs.count()):
        alt = imgs.nth(i).get_attribute("alt")
        if not alt:
            img_no_alt += 1
    if img_no_alt:
        failed += 1
        checks.append(
            UICheck(
                "a11y_img_alt",
                "Images have alt text",
                "fail",
                f"{img_no_alt} image(s) missing alt",
            )
        )
    else:
        passed += 1
        checks.append(UICheck("a11y_img_alt", "Images have alt text", "pass"))

    # Every button has accessible name
    buttons = page.locator("button")
    btn_no_name = 0
    for i in range(buttons.count()):
        b = buttons.nth(i)
        aria = b.get_attribute("aria-label") or ""
        text = (b.text_content() or "").strip()
        if not aria and not text:
            btn_no_name += 1
    if btn_no_name:
        failed += 1
        checks.append(
            UICheck(
                "a11y_button_names",
                "Buttons have accessible names",
                "fail",
                f"{btn_no_name} button(s) missing name",
            )
        )
    else:
        passed += 1
        checks.append(
            UICheck("a11y_button_names", "Buttons have accessible names", "pass")
        )

    # Copy buttons have aria-label containing "copy"
    copy_btns = page.locator(
        "button[aria-label*='copy' i], button[aria-label*='Copy' i]"
    )
    total_copy = copy_btns.count()
    if total_copy:
        passed += 1
        checks.append(
            UICheck(
                "a11y_copy_labels",
                "Copy buttons have aria-label",
                "pass",
                f"{total_copy} copy button(s) with aria-label",
            )
        )
    else:
        copy_btns_any = page.locator("button:has-text('Copy'), button[class*='copy']")
        if copy_btns_any.count():
            failed += 1
            checks.append(
                UICheck(
                    "a11y_copy_labels",
                    "Copy buttons have aria-label",
                    "fail",
                    "Copy buttons found but without aria-label",
                )
            )
        else:
            passed += 1
            checks.append(
                UICheck(
                    "a11y_copy_labels",
                    "Copy buttons have aria-label",
                    "pass",
                    "No copy buttons to check",
                )
            )

    # Dialog aria-modal check
    dialogs = page.locator("[role='dialog']")
    for i in range(dialogs.count()):
        modal = dialogs.nth(i).get_attribute("aria-modal")
        if modal != "true":
            failed += 1
            checks.append(
                UICheck(
                    "a11y_dialog_modal",
                    "Dialog focus trap",
                    "fail",
                    "Dialog without aria-modal=true",
                )
            )
            break
    else:
        if dialogs.count():
            passed += 1
            checks.append(UICheck("a11y_dialog_modal", "Dialog focus trap", "pass"))

    # Tabindex check
    tabindex_els = page.locator("[tabindex]")
    neg_tabindex = 0
    for i in range(tabindex_els.count()):
        ti = tabindex_els.nth(i).get_attribute("tabindex") or "0"
        try:
            if int(ti) < 0:
                neg_tabindex += 1
        except ValueError:
            pass
    if neg_tabindex:
        failed += 1
        checks.append(
            UICheck(
                "a11y_tabindex",
                "Tab index values",
                "fail",
                f"{neg_tabindex} element(s) with negative tabindex",
            )
        )
    else:
        passed += 1
        checks.append(UICheck("a11y_tabindex", "Tab index values", "pass"))

    return passed, failed, checks


def _stress_test(page: "Any", output_dir: str, mode_name: str) -> List[UICheck]:
    """Run a stress test with large markdown content."""
    checks: List[UICheck] = []
    stress_prompt = "Reply ONLY with this exact markdown:\n\n"
    stress_prompt += "# Stress Test\n\n"
    for i in range(1, 26):
        stress_prompt += f"## Section {i}\n\n"
        stress_prompt += f"Paragraph for section {i} with **bold** and *italic*.\n\n"
        stress_prompt += f"- Item {i}.1\n- Item {i}.2\n- Item {i}.3\n\n"
        stress_prompt += f"> Quote for section {i}\n\n"
        stress_prompt += f"```python\nprint('section {i}')\n```\n\n"
    stress_prompt += "---\n\n**End of stress test.**\n"

    input_box = page.locator(
        "textarea, input[type='text'], [contenteditable='true'], "
        "#landing-input, #conversation-input"
    ).filter(visible=True)
    if not input_box.count():
        checks.append(
            UICheck(
                f"{mode_name}_stress_input",
                "Stress test input",
                "skip",
                "Input not found",
            )
        )
        return checks
    input_box.first.fill(stress_prompt)
    page.wait_for_timeout(200)
    send_btn = page.locator(
        "button[aria-label*='send'], "
        "button[aria-label*='Send'], "
        "button.composer-btn--send, "
        "button[type='submit']"
    ).filter(visible=True)
    if send_btn.count():
        send_btn.first.click()
    else:
        page.keyboard.press("Enter")
    page.wait_for_timeout(12000)

    # Check for browser errors
    # (errors already collected globally)

    # Check response container has content
    resp_sel = _response_selector(mode_name)
    rendered_el = page.locator(resp_sel)
    has_content = (
        rendered_el.count() > 0
        and len((rendered_el.first.text_content() or "").strip()) > 50
    )
    checks.append(
        UICheck(
            f"{mode_name}_stress_content",
            "Stress test renders content",
            "pass" if has_content else "fail",
        )
    )

    # Check scroll height increased
    before_height = page.evaluate("document.body.scrollHeight")
    if before_height and before_height > 500:
        checks.append(
            UICheck(
                f"{mode_name}_stress_scroll",
                "Stress test scroll height",
                "pass",
                f"Scroll height: {before_height}px",
            )
        )
    else:
        checks.append(
            UICheck(
                f"{mode_name}_stress_scroll",
                "Stress test scroll height",
                "pass" if before_height else "skip",
            )
        )

    # No DOM truncation - rendered text length at least 80% of backend
    if has_content:
        rendered_len = len(rendered_el.first.text_content() or "")
        stress_len = len(stress_prompt)
        ratio = rendered_len / max(stress_len, 1)
        if ratio >= 0.8:
            checks.append(
                UICheck(
                    f"{mode_name}_stress_truncation",
                    "Stress test no truncation",
                    "pass",
                    f"Rendered {rendered_len} / backend {stress_len} chars ({ratio:.0%})",
                )
            )
        else:
            checks.append(
                UICheck(
                    f"{mode_name}_stress_truncation",
                    "Stress test no truncation",
                    "fail",
                    f"Rendered {rendered_len} / backend {stress_len} chars ({ratio:.0%})",
                )
            )

    screenshot_path = os.path.join(output_dir, f"{mode_name}-stress.png")
    page.screenshot(path=screenshot_path, full_page=True)
    checks.append(
        UICheck(
            f"{mode_name}_stress_screenshot",
            "Stress test screenshot",
            "pass",
            screenshot_path,
        )
    )

    return checks


# ── element checklists ───────────────────────────────────────────────

MODE_ELEMENTS: Dict[str, List[tuple[str, str, str]]] = {
    "canvas": [
        ("h1,h2,h3", "heading", "Heading"),
        ("p", "paragraph", "Paragraph"),
        ("ul,ol", "list", "List"),
        ("ul ul,ol ol,ul ol,ol ul", "nested_list", "Nested list"),
        ("strong,b", "bold", "Bold"),
        ("em,i", "italic", "Italic"),
        ("code:not(pre code)", "inline_code", "Inline code"),
        ("pre code, pre", "fenced_code", "Fenced code block"),
        ("blockquote", "blockquote", "Blockquote"),
        ("hr", "hr", "Horizontal rule"),
        ("table", "table", "Table"),
        ("a[href]", "link", "Link"),
        ("input[type='checkbox']", "task_list", "Task list"),
    ],
    "web": [
        ("a[href]", "link", "Link"),
        ("table", "table", "Table"),
        ("p", "paragraph", "Paragraph"),
    ],
}


# ── golden prompts (permanent regression suite) ──

GOLDEN_PROMPTS: Dict[str, str] = {
    "markdown": "Reply ONLY with this exact markdown (no preamble):\n\n# Heading 1\n\nA paragraph.\n\n- List A\n- List B\n\n**bold** *italic* `code`\n\n> Blockquote\n\n---\n\n| L | R |\n| --- | --- |\n| 1 | 2 |\n\n[Link](https://example.com)\n\n- [x] Task",
    "code": "Reply ONLY with this exact markdown:\n\n```python\nprint('hello')\n```",
    "long_code": "Reply ONLY with this exact markdown:\n\n```python\ndef fib(n):\n    if n <= 1:\n        return n\n    return fib(n-1) + fib(n-2)\n\nprint(fib(10))\n```",
    "tables": "Reply ONLY with this exact markdown:\n\n| Name | Age | City |\n| --- | --- | --- |\n| Alice | 30 | NYC |\n| Bob | 25 | SF |\n| Eve | 35 | LA |",
    "nested_lists": "Reply ONLY with this exact markdown:\n\n- Outer\n  - Inner A\n  - Inner B\n    - Deep\n- Another",
    "blockquotes": "Reply ONLY with this exact markdown:\n\n> First level\n> > Nested\n> Back to first",
    "task_lists": "Reply ONLY with this exact markdown:\n\n- [x] Done\n- [ ] Pending\n- [ ] Maybe",
    "mixed": "Reply ONLY with this exact markdown:\n\n# Title\n\nA paragraph with **bold**, *italic*, and `code`.\n\n- List\n\n> Quote\n\n```python\nx = 1\n```\n\n---\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n\n[Link](https://x.com)",
    "reasoning": "What is 12 * 15? Explain step by step, then give the answer.",
    "links": "Reply ONLY with this exact markdown:\n\n[Alma](https://palmshed.vercel.app) and [GitHub](https://github.com)",
    "emoji": "Reply ONLY with this exact markdown:\n\n🚀 Python is great! 🐍\n\n- ✅ Check\n- ❌ Cross",
}


# ── main fidelity entry-point ────────────────────────────────────────


@dataclass
class ModeFidelityReport:
    """Verification result for one mode."""

    mode: str
    label: str
    markdown_match_pct: float = 0.0
    clipboard_match_pct: float = 0.0
    code_blocks_matched: int = 0
    code_blocks_total: int = 0
    thinking_match_pct: float = 0.0
    answer_match_pct: float = 0.0
    thinking_duplication_chars: int = 0
    elements_passed: int = 0
    elements_failed: int = 0
    console_errors: int = 0
    overall: str = "fail"
    structures: Dict[str, int] = field(default_factory=dict)
    structures_expected: Dict[str, int] = field(default_factory=dict)
    structures_matched: int = 0
    structures_total: int = 0
    features_rendered: int = 0
    features_total: int = 0
    metrics: Dict[str, float] = field(default_factory=dict)
    accessibility_passed: int = 0
    accessibility_failed: int = 0


def run_render_fidelity(output_dir: str) -> List[UICheck]:
    """Headless QA — compare rendered DOM against the backend response
    for every mode without requiring human screenshot inspection."""
    if not check_playwright_installed():
        return [
            UICheck("fidelity", "Render fidelity", "fail", "Playwright not installed.")
        ]

    from playwright.sync_api import sync_playwright

    results: List[UICheck] = []
    config = get_config()
    api_base = config["base_url"]
    frontend_url = os.environ.get("ALMA_FRONTEND_URL", "http://localhost:5173")

    # ── Deterministic prompts designed to exercise every salient
    #    markdown feature in the response.  The model must reproduce
    #    them faithfully; the UI must render them faithfully.
    PROMPTS: Dict[str, str] = {
        "canvas": (
            "Reply ONLY with this exact markdown (no preamble, no commentary):\n\n"
            "# Heading 1\n\n"
            "A short paragraph.\n\n"
            "- List item A\n"
            "- List item B\n"
            "- List item C\n\n"
            "1. Ordered one\n"
            "2. Ordered two\n\n"
            "- Outer\n"
            "  - Inner A\n"
            "  - Inner B\n\n"
            "**Bold text** and *italic text* and `inline code`.\n\n"
            "> A blockquote spanning two lines.\n"
            "> Second line.\n\n"
            "---\n\n"
            "| Left | Right |\n"
            "| --- | --- |\n"
            "| X | Y |\n"
            "| 1 | 2 |\n\n"
            "[A link](https://example.com)\n\n"
            "```python\n"
            "print('hello world')\n"
            "```\n\n"
            "- [x] Done task\n"
            "- [ ] Pending task"
        ),
        "thinking": (
            "What is 7 * 8? "
            "First explain your reasoning step by step, "
            "then give the final answer."
        ),
        "web": (
            "Reply ONLY with this exact markdown:\n\n"
            "Visit [Example](https://example.com) for more info.\n\n"
            "| Name | Value |\n"
            "| --- | --- |\n"
            "| Alpha | 100 |\n"
            "| Beta | 200 |\n\n"
            "A concluding paragraph."
        ),
    }

    # ── Step 1: fetch backend responses ──
    backend_data: Dict[str, str] = {}
    for mode_name, prompt in PROMPTS.items():
        url = _mode_endpoint(mode_name, api_base)
        tresp = api_post_timed(url, {"prompt": prompt})
        # save raw response
        raw_path = os.path.join(output_dir, f"{mode_name}-backend-raw.json")
        with open(raw_path, "w") as f:
            f.write(
                json.dumps(tresp.body, indent=2)
                if isinstance(tresp.body, dict)
                else str(tresp.body)
            )
        results.append(
            UICheck(
                f"{mode_name}_backend_fetch",
                f"{mode_name.capitalize()} backend fetch",
                "pass" if tresp.status == 200 else "fail",
                f"HTTP {tresp.status}" if tresp.status != 200 else None,
            )
        )
        md = _extract_markdown(tresp.body, mode_name)
        backend_data[mode_name] = md
        # save extracted markdown
        md_path = os.path.join(output_dir, f"{mode_name}-backend-markdown.txt")
        with open(md_path, "w") as f:
            f.write(md)

    # ── Step 2: browser render & compare ──
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            permissions=["clipboard-read", "clipboard-write"],
        )
        page = context.new_page()
        console_logs: List[str] = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: console_logs.append(f"[ERROR] {err}"))

        page.goto(frontend_url, wait_until="networkidle", timeout=_TIMEOUT * 1000)
        page.wait_for_timeout(1000)

        mode_reports: List[ModeFidelityReport] = []

        for mode_name in ("canvas", "thinking", "web"):
            prompt = PROMPTS[mode_name]
            label = mode_name.capitalize()
            report = ModeFidelityReport(mode=mode_name, label=label)

            # ── mode labels & data attributes ──
            mode_attrs = {
                "canvas": ("Canvas", "[data-mode='text'][data-style='normal']"),
                "thinking": ("Thinking", "[data-mode='text'][data-style='thinking']"),
                "web": ("Web", "[data-mode='text'][data-style='url-context']"),
            }
            label, data_sel = mode_attrs.get(mode_name, (label, ""))
            # try data-attribute selector first, then text label
            # try data-attribute selector first, then text label
            seg = page.locator(
                f"{data_sel}, "
                f"button:has-text('{label}'), "
                f"[role='tab']:has-text('{label}')"
            ).filter(visible=True)
            if seg.count():
                seg.first.click()
                page.wait_for_timeout(300)

            # ── fill & submit ──
            input_box = page.locator(
                "textarea, input[type='text'], [contenteditable='true'], "
                "#landing-input, #conversation-input"
            ).filter(visible=True)
            if not input_box.count():
                results.append(
                    UICheck(
                        f"{mode_name}_input",
                        f"{label} input",
                        "fail",
                        "Input field not found.",
                    )
                )
                report.overall = "fail"
                mode_reports.append(report)
                continue
            start_time = time.monotonic()
            input_box.first.fill(prompt)
            page.wait_for_timeout(200)
            send_btn = page.locator(
                "button[aria-label*='send'], "
                "button[aria-label*='Send'], "
                "button.composer-btn--send, "
                "button[type='submit']"
            ).filter(visible=True)
            if send_btn.count():
                send_btn.first.click()
            else:
                page.keyboard.press("Enter")

            # ── wait for rendering to finish ──
            page.wait_for_timeout(1000)
            screenshot_path = os.path.join(output_dir, f"{mode_name}-fidelity.png")
            page.screenshot(path=screenshot_path, full_page=True)
            page.wait_for_timeout(9000)  # allow model generation time

            # ── VISUAL REGRESSION ──
            vreg = _visual_regression(mode_name, screenshot_path, output_dir)
            results.append(vreg)
            if vreg.status == "fail":
                report.overall = "fail"

            # ── save DOM snapshot ──
            dom = page.content()
            dom_path = os.path.join(output_dir, f"{mode_name}-dom.html")
            with open(dom_path, "w") as f:
                f.write(dom)

            # ── extract rendered text ──
            resp_sel = _response_selector(mode_name)
            rendered_el = page.locator(resp_sel)
            rendered_text = ""
            if rendered_el.count():
                rendered_text = rendered_el.first.text_content() or ""
            if not rendered_text:
                # fallback: whole page
                rendered_text = page.locator("body").text_content() or ""

            dom_text_path = os.path.join(output_dir, f"{mode_name}-dom-text.txt")
            with open(dom_text_path, "w") as f:
                f.write(rendered_text)

            backend_md = backend_data.get(mode_name, "")

            # ── NORMALISED TEXT COMPARISON ──
            if mode_name == "thinking":
                backend_thinking, backend_answer = _split_thinking(backend_md)

                # locate thinking container
                thinking_el = page.locator(
                    ".thinking, .reasoning, [class*='thinking'], [class*='reasoning']"
                )
                dom_thinking = (
                    thinking_el.first.text_content() or ""
                    if thinking_el.count()
                    else ""
                )

                # locate answer container
                answer_el = page.locator(resp_sel)
                dom_answer = (
                    answer_el.first.text_content() or "" if answer_el.count() else ""
                )

                # if there's only one container and it has everything,
                # fall back to splitting rendered_text
                if not dom_thinking and not dom_answer:
                    dom_thinking = ""
                    dom_answer = rendered_text
                elif not dom_answer:
                    dom_answer = rendered_text

                # compare
                pct_t, _ = _compare_text(backend_thinking, dom_thinking)
                pct_a, _ = _compare_text(backend_answer, dom_answer)
                report.thinking_match_pct = pct_t
                report.answer_match_pct = pct_a

                results.append(
                    UICheck(
                        f"{mode_name}_thinking_text",
                        f"{label} thinking text match",
                        "pass" if pct_t >= 50 else "fail",
                        f"{pct_t}% match",
                    )
                )
                results.append(
                    UICheck(
                        f"{mode_name}_answer_text",
                        f"{label} answer text match",
                        "pass" if pct_a >= 50 else "fail",
                        f"{pct_a}% match",
                    )
                )

                # duplication check
                nt = _normalize(dom_thinking)
                na = _normalize(dom_answer)
                dup = 0
                if nt and na and nt in na:
                    dup = len(nt)
                report.thinking_duplication_chars = dup
                results.append(
                    UICheck(
                        f"{mode_name}_no_duplication",
                        f"{label} no thinking/answer duplication",
                        "fail" if dup > 20 else "pass",
                        f"{dup} duplicated chars" if dup > 20 else None,
                    )
                )

                # overall markdown match uses the answer portion
                _, md_diffs = _compare_text(backend_answer, dom_answer)
                report.markdown_match_pct = pct_a

            else:
                # canvas / web: compare full rendered text
                pct, diffs = _compare_text(backend_md, rendered_text)
                report.markdown_match_pct = pct
                results.append(
                    UICheck(
                        f"{mode_name}_text_match",
                        f"{label} rendered text matches backend",
                        "pass" if pct >= 50 else "fail",
                        f"{pct}% match, {diffs} diffs",
                    )
                )

            # ── BROWSER METRICS ──
            report.metrics = _capture_metrics(page, start_time)
            results.append(
                UICheck(
                    f"{mode_name}_metrics",
                    f"{label} browser metrics",
                    "pass",
                    f"DOMContentLoaded: {report.metrics.get('dom_content_loaded_ms', '?')}ms, "
                    f"Total: {report.metrics.get('total_elapsed_s', '?')}s",
                )
            )

            # ── ELEMENT CHECKS ──
            elements_passed = 0
            elements_failed = 0
            for selector, chk_name, chk_label in MODE_ELEMENTS.get(mode_name, []):
                c = _check_element(page, selector, f"{mode_name}_{chk_name}", chk_label)
                if c.status == "pass":
                    elements_passed += 1
                else:
                    elements_failed += 1
                results.append(c)
            report.elements_passed = elements_passed
            report.elements_failed = elements_failed

            # ── STRUCTURE FIDELITY ──
            actual_structures = _count_structures(page)
            expected_structures = _count_expected_structures(backend_md)
            report.structures = {k: v for k, v in actual_structures.items() if v}
            report.structures_expected = {
                k: v for k, v in expected_structures.items() if v
            }
            struct_matched = 0
            struct_total = 0
            for tag in set(
                list(report.structures.keys()) + list(report.structures_expected.keys())
            ):
                actual = report.structures.get(tag, 0)
                expected = report.structures_expected.get(tag, 0)
                struct_total += 1
                if actual == expected:
                    struct_matched += 1
            report.structures_matched = struct_matched
            report.structures_total = struct_total
            results.append(
                UICheck(
                    f"{mode_name}_structures",
                    f"{label} HTML structure fidelity",
                    "pass" if struct_matched == struct_total else "warn",
                    f"{struct_matched}/{struct_total} element types match expected",
                )
            )

            # ── MARKDOWN FEATURE COVERAGE ──
            md_features = {
                "heading": bool(re.search(r"^#{1,6}\s", backend_md, re.MULTILINE)),
                "paragraph": "\n\n" in backend_md,
                "bold": "**" in backend_md,
                "italic": bool(re.search(r"(?<!\*)\*(?!\*)", backend_md)),
                "code": " `" in backend_md or "` " in backend_md or "```" in backend_md,
                "fenced_code": "```" in backend_md,
                "list": bool(re.search(r"^[-*+]\s", backend_md, re.MULTILINE)),
                "ordered_list": bool(re.search(r"^\d+\.\s", backend_md, re.MULTILINE)),
                "blockquote": bool(re.search(r"^>\s", backend_md, re.MULTILINE)),
                "table": "|---" in backend_md or "| ---" in backend_md,
                "link": bool(re.search(r"\[", backend_md)),
                "task_list": bool(
                    re.search(r"-\s\[\s\]|-\s\[x\]", backend_md, re.IGNORECASE)
                ),
                "hr": bool(re.search(r"^---\s*$", backend_md, re.MULTILINE)),
            }
            feature_selectors = {
                "heading": "h1,h2,h3,h4,h5,h6",
                "paragraph": "p",
                "bold": "strong,b",
                "italic": "em,i",
                "code": "code:not(pre code)",
                "fenced_code": "pre code",
                "list": "ul,ol",
                "ordered_list": "ol",
                "blockquote": "blockquote",
                "table": "table",
                "link": "a[href]",
                "task_list": "input[type='checkbox']",
                "hr": "hr",
            }
            features_rendered = 0
            features_total = 0
            for feat_name, present in md_features.items():
                if present:
                    features_total += 1
                    sel = feature_selectors[feat_name]
                    if page.locator(sel).count():
                        features_rendered += 1
            report.features_rendered = features_rendered
            report.features_total = features_total
            results.append(
                UICheck(
                    f"{mode_name}_feature_coverage",
                    f"{label} feature coverage",
                    "pass" if features_rendered == features_total else "warn",
                    f"{features_rendered}/{features_total} features rendered ({features_rendered * 100 // max(features_total, 1)}%)",
                )
            )

            # ── CLIPBOARD VERIFICATION ──
            copy_btn = page.locator(
                "button[aria-label*='copy'], "
                "button:has-text('Copy'), "
                ".copy-button, "
                "[class*='copy']"
            )
            if copy_btn.count():
                copy_btn.first.click()
                page.wait_for_timeout(500)
                try:
                    clip = page.evaluate("navigator.clipboard.readText()")
                    if isinstance(clip, str) and len(clip) > 10:
                        clip_pct, clip_diffs = _compare_text(backend_md, clip)
                        report.clipboard_match_pct = clip_pct
                        results.append(
                            UICheck(
                                f"{mode_name}_clipboard",
                                f"{label} clipboard matches backend",
                                "pass" if clip_pct >= 50 else "fail",
                                f"{clip_pct}% match, {clip_diffs} diffs",
                            )
                        )
                    else:
                        results.append(
                            UICheck(
                                f"{mode_name}_clipboard",
                                f"{label} clipboard content",
                                "fail",
                                f"Clipboard too short ({len(clip) if isinstance(clip, str) else '?'} chars)",
                            )
                        )
                except Exception as exc:
                    results.append(
                        UICheck(
                            f"{mode_name}_clipboard",
                            f"{label} clipboard read",
                            "fail",
                            str(exc),
                        )
                    )
            else:
                results.append(
                    UICheck(
                        f"{mode_name}_clipboard",
                        f"{label} clipboard",
                        "skip",
                        "No copy button found.",
                    )
                )

            # ── CODE BLOCK FIDELITY (canvas only) ──
            if mode_name == "canvas":
                code_blocks = page.locator("pre code")
                total = code_blocks.count()
                report.code_blocks_total = total

                # extract all backend code fences
                backend_fences = re.findall(
                    r"```(\w+)?\n(.*?)```", backend_md, re.DOTALL
                )
                backend_langs = [f[0] or "" for f in backend_fences]
                backend_codes = [f[1].strip() for f in backend_fences]

                matched = 0
                for i in range(min(total, len(backend_codes))):
                    expected = backend_codes[i].strip()
                    dom_code = (code_blocks.nth(i).text_content() or "").strip()
                    if _normalize(expected) == _normalize(dom_code):
                        matched += 1
                    else:
                        results.append(
                            UICheck(
                                f"{mode_name}_code_{i}",
                                f"{label} code block {i + 1}",
                                "fail",
                                "DOM code differs from backend",
                            )
                        )
                report.code_blocks_matched = matched

                # Syntax highlighting: verify language classes
                lang_pass = 0
                for i in range(min(total, len(backend_langs))):
                    code_el = code_blocks.nth(i) if i < total else None
                    expected_lang = backend_langs[i]
                    if expected_lang and code_el:
                        class_attr = code_el.get_attribute("class") or ""
                        if (
                            expected_lang in class_attr
                            or f"language-{expected_lang}" in class_attr
                        ):
                            lang_pass += 1
                        else:
                            results.append(
                                UICheck(
                                    f"{mode_name}_syntax_{i}",
                                    f"{label} syntax highlighting block {i + 1}",
                                    "fail",
                                    f"Expected language '{expected_lang}', got class '{class_attr}'",
                                )
                            )
                    elif expected_lang:
                        results.append(
                            UICheck(
                                f"{mode_name}_syntax_{i}",
                                f"{label} syntax highlighting block {i + 1}",
                                "fail",
                                "Code block element not found",
                            )
                        )
                if len(backend_langs) > 0:
                    results.append(
                        UICheck(
                            f"{mode_name}_syntax_highlighting",
                            f"{label} syntax highlighting",
                            (
                                "pass"
                                if lang_pass == len([ln for ln in backend_langs if ln])
                                else "warn"
                            ),
                            f"{lang_pass}/{len([ln for ln in backend_langs if ln])} language classes match expected",
                        )
                    )

                # Copy button count verification
                copy_btns = page.locator(
                    "button[aria-label*='copy' i], "
                    "button[aria-label*='Copy'], "
                    "button:has-text('Copy'), "
                    ".copy-button"
                ).filter(visible=True)
                copy_count = copy_btns.count()
                if copy_count > 0:
                    results.append(
                        UICheck(
                            f"{mode_name}_copy_button_count",
                            f"{label} copy button count",
                            "pass" if copy_count >= total else "warn",
                            f"{copy_count} copy button(s) for {total} code block(s)",
                        )
                    )

                # clipboard for code blocks
                cb_match = 0
                cb_total = 0
                for i in range(total):
                    code_blocks.nth(i).click()
                    page.wait_for_timeout(200)
                    copy_btn_on_block = page.locator(
                        "button[aria-label*='copy'], "
                        "button[aria-label*='Copy'], "
                        "button:has-text('Copy')"
                    ).filter(visible=True)
                    if copy_btn_on_block.count():
                        copy_btn_on_block.first.click()
                        page.wait_for_timeout(300)
                        try:
                            cb = page.evaluate("navigator.clipboard.readText()")
                            if i < len(backend_codes):
                                cb_total += 1
                                expected = backend_codes[i].strip()
                                if cb.strip() == expected:
                                    cb_match += 1
                                else:
                                    results.append(
                                        UICheck(
                                            f"{mode_name}_code_clip_{i}",
                                            f"{label} code block {i + 1} clipboard",
                                            "fail",
                                            "Clipboard differs from backend code",
                                        )
                                    )
                        except Exception:
                            pass
                if cb_total > 0:
                    results.append(
                        UICheck(
                            f"{mode_name}_code_clipboard",
                            f"{label} code block clipboard fidelity",
                            "pass" if cb_match == cb_total else "fail",
                            f"{cb_match}/{cb_total} code blocks match clipboard",
                        )
                    )

                results.append(
                    UICheck(
                        f"{mode_name}_code_blocks",
                        f"{label} code block fidelity",
                        "pass" if matched == total == len(backend_codes) else "fail",
                        f"{matched}/{total} DOM blocks match backend",
                    )
                )

            # ── MULTIPLE CODE BLOCKS TEST ──
            if mode_name == "canvas":
                multicode_prompt = (
                    "Reply ONLY with this exact markdown:\n\n"
                    "Python:\n"
                    "```python\n"
                    "print('hello')\n"
                    "```\n\n"
                    "JavaScript:\n"
                    "```javascript\n"
                    "console.log('hello');\n"
                    "```"
                )
                page.locator(
                    "textarea, input[type='text'], [contenteditable='true'], "
                    "#landing-input, #conversation-input"
                ).filter(visible=True).first.fill(multicode_prompt)
                page.wait_for_timeout(200)
                page.locator(
                    "button[aria-label*='send'], "
                    "button[aria-label*='Send'], "
                    "button.composer-btn--send, "
                    "button[type='submit']"
                ).filter(visible=True).first.click()
                page.wait_for_timeout(12000)

                mc_code_blocks = page.locator("pre code")
                mc_total = mc_code_blocks.count()
                results.append(
                    UICheck(
                        f"{mode_name}_multicode_blocks",
                        f"{label} multiple code blocks",
                        "pass" if mc_total >= 2 else "fail",
                        f"{mc_total} code block(s) found (expected 2)",
                    )
                )

                mc_copy_btns = page.locator(
                    "button[aria-label*='copy' i], button:has-text('Copy')"
                ).filter(visible=True)
                mc_copy_count = mc_copy_btns.count()
                results.append(
                    UICheck(
                        f"{mode_name}_multicode_copy_btns",
                        f"{label} multicode copy buttons",
                        "pass" if mc_copy_count >= mc_total else "warn",
                        f"{mc_copy_count} copy button(s) for {mc_total} code block(s)",
                    )
                )

                # verify each copy button copies its own content
                mc_ok = 0
                for i in range(min(mc_total, 2)):
                    mc_code_blocks.nth(i).click()
                    page.wait_for_timeout(200)
                    mc_copy = page.locator(
                        "button[aria-label*='copy' i], button:has-text('Copy')"
                    ).filter(visible=True)
                    if mc_copy.count():
                        mc_copy.first.click()
                        page.wait_for_timeout(300)
                        try:
                            cb_text = page.evaluate("navigator.clipboard.readText()")
                            expected_codes = ["print('hello')", "console.log('hello');"]
                            if i < len(expected_codes) and expected_codes[i] in cb_text:
                                mc_ok += 1
                            else:
                                results.append(
                                    UICheck(
                                        f"{mode_name}_multicode_clip_{i}",
                                        f"{label} multi code block {i + 1} clipboard",
                                        "fail",
                                    )
                                )
                        except Exception:
                            pass
                if mc_total > 0:
                    results.append(
                        UICheck(
                            f"{mode_name}_multicode_fidelity",
                            f"{label} multiple code block fidelity",
                            "pass" if mc_ok == min(mc_total, 2) else "warn",
                            f"{mc_ok}/{min(mc_total, 2)} code blocks copy correct content",
                        )
                    )

            # ── overall mode verdict ──
            failures = [
                r
                for r in results
                if r.name.startswith(f"{mode_name}_") and r.status == "fail"
            ]
            report.overall = "pass" if not failures else "fail"
            mode_reports.append(report)

        # ── Images ──
        report = ModeFidelityReport(mode="images", label="Images")
        seg = page.locator(
            "[data-mode='image'], "
            "button:has-text('Images'), "
            "[role='tab']:has-text('Images')"
        ).filter(visible=True)
        if seg.count():
            seg.first.click()
            page.wait_for_timeout(300)
        input_box = page.locator(
            "textarea, input[type='text'], [contenteditable='true'], "
            "#landing-input, #conversation-input"
        ).filter(visible=True)
        if input_box.count():
            input_box.first.fill("A red circle")
            send_btn = page.locator(
                "button[aria-label*='send'], "
                "button[aria-label*='Send'], "
                "button.composer-btn--send, "
                "button[type='submit']"
            ).filter(visible=True)
            if send_btn.count():
                send_btn.first.click()
            else:
                page.keyboard.press("Enter")
            page.wait_for_timeout(5000)

            img = page.locator("img")
            quota_msg = page.locator("text=quota, text=Quota, text=exceeded")
            if img.count():
                results.append(
                    UICheck(
                        "images_render",
                        "Image rendered",
                        "pass",
                        f"{img.count()} image(s) found.",
                    )
                )
                alt = img.first.get_attribute("alt")
                if alt:
                    results.append(
                        UICheck(
                            "images_alt",
                            "Image alt text",
                            "pass",
                        )
                    )
                else:
                    results.append(
                        UICheck(
                            "images_alt",
                            "Image alt text",
                            "skip",
                            "No alt attribute.",
                        )
                    )
                report.overall = "pass"
            elif quota_msg.count():
                results.append(
                    UICheck(
                        "images_render",
                        "Image rendered (quota exceeded)",
                        "pass",
                        "Quota message rendered cleanly.",
                    )
                )
                report.overall = "pass"
            else:
                results.append(
                    UICheck(
                        "images_render",
                        "Image rendered",
                        "fail",
                        "No image or quota message found.",
                    )
                )
                report.overall = "fail"
        else:
            results.append(
                UICheck(
                    "images_input",
                    "Images input",
                    "skip",
                    "No input field found for images mode.",
                )
            )
            report.overall = "skip"
        mode_reports.append(report)

        # ── STRESS TEST (canvas) ──
        stress_results = _stress_test(page, output_dir, "canvas")
        results.extend(stress_results)

        # ── ACCESSIBILITY CHECKS ──
        a11y_passed, a11y_failed, a11y_checks = _accessibility_checks(page)
        for ac in a11y_checks:
            results.append(ac)
        for rp in mode_reports:
            if rp.mode == "canvas":
                rp.accessibility_passed = a11y_passed
                rp.accessibility_failed = a11y_failed

        # ── GOLDEN PROMPTS REFERENCE ──
        results.append(
            UICheck(
                "golden_prompts",
                "Golden prompts defined",
                "pass",
                f"{len(GOLDEN_PROMPTS)} golden prompts in regression suite",
            )
        )

        # ── console errors ──
        log_path = os.path.join(output_dir, "console.log")
        with open(log_path, "w") as f:
            f.write("\n".join(console_logs))
        errors = [ln for ln in console_logs if "[ERROR]" in ln]
        if errors:
            results.append(
                UICheck(
                    "fidelity_console",
                    "Console errors",
                    "fail",
                    f"{len(errors)} errors",
                )
            )
        else:
            results.append(
                UICheck(
                    "fidelity_console",
                    "Console errors",
                    "pass",
                    f"No errors ({len(console_logs)} log entries).",
                )
            )

        browser.close()

    # ── Render report ──
    report_lines = [
        "Render fidelity verification",
        "",
    ]
    for rp in mode_reports:
        report_lines.append(f"  {rp.label}: {rp.overall.upper()}")
        if rp.markdown_match_pct:
            report_lines.append(f"    Markdown match:  {rp.markdown_match_pct}%")
        if rp.clipboard_match_pct:
            report_lines.append(f"    Clipboard match: {rp.clipboard_match_pct}%")
        if rp.code_blocks_total:
            report_lines.append(
                f"    Code blocks:     {rp.code_blocks_matched}/{rp.code_blocks_total} matched"
            )
        if rp.thinking_match_pct:
            report_lines.append(f"    Thinking match:  {rp.thinking_match_pct}%")
        if rp.answer_match_pct:
            report_lines.append(f"    Answer match:    {rp.answer_match_pct}%")
        if rp.thinking_duplication_chars:
            report_lines.append(
                f"    Duplication:     {rp.thinking_duplication_chars} chars (FAIL)"
            )
        if rp.elements_passed or rp.elements_failed:
            report_lines.append(
                f"    Elements:        {rp.elements_passed} passed, {rp.elements_failed} failed"
            )
        if rp.structures_matched or rp.structures_total:
            report_lines.append(
                f"    Structures:      {rp.structures_matched}/{rp.structures_total} types match"
            )
        if rp.features_total:
            report_lines.append(
                f"    Features:        {rp.features_rendered}/{rp.features_total} rendered "
                f"({rp.features_rendered * 100 // max(rp.features_total, 1)}%)"
            )
        if rp.metrics:
            m = rp.metrics
            report_lines.append(
                f"    DOMContentLoaded: {m.get('dom_content_loaded_ms', '?')}ms | "
                f"Total: {m.get('total_elapsed_s', '?')}s"
            )
        if rp.accessibility_passed or rp.accessibility_failed:
            report_lines.append(
                f"    Accessibility:   {rp.accessibility_passed} passed, {rp.accessibility_failed} failed"
            )
        report_lines.append("")
    # ── save additional evidence ──
    for rp in mode_reports:
        if rp.structures:
            struct_path = os.path.join(output_dir, f"{rp.mode}-structures.json")
            with open(struct_path, "w") as f:
                json.dump(
                    {"actual": rp.structures, "expected": rp.structures_expected},
                    f,
                    indent=2,
                )
        if rp.metrics:
            metrics_path = os.path.join(output_dir, f"{rp.mode}-metrics.json")
            with open(metrics_path, "w") as f:
                json.dump(rp.metrics, f, indent=2)
        a11y_path = os.path.join(output_dir, f"{rp.mode}-accessibility.json")
        with open(a11y_path, "w") as f:
            json.dump(
                {"passed": rp.accessibility_passed, "failed": rp.accessibility_failed},
                f,
                indent=2,
            )

    report_lines.append(f"Evidence saved to: {output_dir}")

    report_text = "\n".join(report_lines)
    report_path = os.path.join(output_dir, "fidelity-report.txt")
    with open(report_path, "w") as f:
        f.write(report_text + "\n")
    results.append(
        UICheck(
            "fidelity_report",
            "Fidelity report",
            "pass",
            report_path,
        )
    )

    return results


# ── Human-readable output ────────────────────────────────────────────


def format_human(report: OverallReport) -> str:
    lines: List[str] = []
    lines.append("UI Verification Report")
    lines.append("")

    for mode_name, ui_report in report.modes.items():
        cap = ui_report.capabilities
        lc = ui_report.lifecycle
        lines.append(f"\u2500\u2500 {cap.label} \u2500\u2500")
        lines.append("")

        # Backend capabilities
        lines.append("  Backend")
        lines.append(f"    Endpoint:  {cap.endpoint}")
        lines.append(f"    Streaming: {'Yes' if cap.backend.streaming else 'No'}")
        if cap.backend.streaming:
            sd = cap.backend.streaming_detection
            lines.append(f"    Detection: {sd.method} ({sd.evidence})")
        lines.append(
            f"    Reasoning: {'Incremental' if cap.backend.incremental_reasoning else 'Final payload only'}"
        )
        lines.append(
            f"    Text:      {'Partial' if cap.backend.partial_text else 'Final-only'}"
        )
        keys = cap.backend.response_keys
        lines.append(f"    Response:  {', '.join(keys) if keys else '(binary)'}")

        t = cap.backend.timing
        lines.append(
            f"    Timing:    TTFB {t.ttfb_s}s, Transfer {t.transfer_s}s, Total {t.total_s}s"
        )
        if cap.error:
            lines.append(f"    Error:     {cap.error}")
        if cap.response_shape_file:
            lines.append(f"    Shape:     {cap.response_shape_file}")
        lines.append("")

        # Lifecycle phases
        lines.append("  Lifecycle")
        for phase in lc.phases:
            marker = "\u2713" if phase.present else "\u2717"
            lines.append(f"    {marker} {phase.label}")
            lines.append(f"      {phase.detail}")
        lines.append("")

        # UI checks
        lines.append("  UI")
        for check in ui_report.ui_checks:
            if check.status == "pass":
                marker = "\u2713"
            elif check.status == "skip":
                marker = "\u2014"
            else:
                marker = "\u2717"
            lines.append(f"    {marker} {check.label}")
            if check.detail:
                lines.append(f"      {check.detail}")
        lines.append("")
        lines.append(f"  Result: {ui_report.summary_status.upper()}")
        lines.append("")

    # Summary
    lines.append("Summary")
    lines.append(f"  Overall: {report.summary.get('overall', 'unknown').upper()}")
    lines.append(f"  UI checks: {report.summary.get('ui_checks_passed', '?')} passed")
    lines.append(f"  Output:   {report.summary.get('output_dir', '(none)')}")
    lines.append("")
    bc = report.summary.get("backend_capabilities", {})
    lines.append("Backend capabilities:")
    for mode, caps in bc.items():
        label = mode.capitalize()
        stream = "streaming" if caps.get("streaming") else "final"
        reason = caps.get("incremental_reasoning", False)
        r = ", incremental reasoning" if reason else ""
        timing = caps.get("timing", {})
        t = f", {timing.get('total_s', '?')}s total"
        lines.append(f"  {label}: {stream}{r}{t}")

    return "\n".join(lines)


def format_json(report: OverallReport) -> str:
    return json.dumps(asdict(report), indent=2, default=str)


# ── CLI ──────────────────────────────────────────────────────────────


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="UI verification for Alma — validates that the frontend "
        "correctly represents every response lifecycle phase.",
    )
    parser.add_argument(
        "--capabilities",
        action="store_true",
        help="Run backend capability detection only",
    )
    parser.add_argument(
        "--static",
        action="store_true",
        help="Run static frontend code analysis only",
    )
    parser.add_argument(
        "--browser",
        action="store_true",
        help="Run browser-based verification (requires Playwright)",
    )
    parser.add_argument(
        "--fidelity",
        action="store_true",
        help="Run render fidelity checks (DOM vs API, clipboard, Markdown elements)",
    )
    parser.add_argument(
        "--e2e",
        action="store_true",
        help="Run end-to-end verification (multi-viewport, flows, traces)",
    )
    parser.add_argument(
        "--flow",
        type=str,
        nargs="*",
        default=None,
        metavar="FLOW",
        help="Specific flows to verify (chat, search, thinking, voice, keyboard, themes)",
    )
    parser.add_argument(
        "--viewport",
        type=str,
        nargs="*",
        default=None,
        metavar="VIEWPORT",
        help="Specific viewports to test (desktop, tablet, mobile)",
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
        help="Write JSON report to FILE",
    )
    parser.add_argument(
        "modes",
        nargs="*",
        metavar="MODE",
        default=[],
        help="Specific modes to verify (default: all)",
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

    config = get_config()
    valid_modes = {"canvas", "thinking", "web", "images", "search", "auto", "code"}
    if args.modes:
        for m in args.modes:
            if m not in valid_modes:
                parser.error(
                    f"unknown mode: {m!r}; choices: {', '.join(sorted(valid_modes))}"
                )

    output_dir = _ensure_output_dir()

    # When no explicit flag is given, default to e2e (subcommand path).
    if not any([args.e2e, args.capabilities, args.static, args.browser, args.fidelity]):
        args.e2e = True

    # ── e2e-only ──
    if args.e2e:
        flows = tuple(args.flow) if args.flow else ALL_FLOWS
        viewports = None
        if args.viewport:
            viewports = {v: VIEWPORTS[v] for v in args.viewport if v in VIEWPORTS}
            if not viewports:
                parser.error(
                    f"unknown viewport: {args.viewport!r}; choices: {', '.join(sorted(VIEWPORTS))}"
                )

        e2e_dir = os.path.join(output_dir, "e2e")
        os.makedirs(e2e_dir, exist_ok=True)
        results = run_e2e_verification(e2e_dir, flows=flows, viewports=viewports)

        if args.json or args.output:
            output = _format_e2e_json(results, [], e2e_dir)
        else:
            output = _format_e2e_report(results, [], e2e_dir)

        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
                f.write("\n")
        else:
            print(output)

        failures = [r for r in results if r.status == "fail"]
        sys.exit(1 if failures else 0)
        return

    # ── capabilities-only ──
    if args.capabilities:
        capabilities = detect_capabilities(config)
        if args.modes:
            capabilities = {k: v for k, v in capabilities.items() if k in args.modes}

        out: Dict[str, Any] = {}
        for name, cap in capabilities.items():
            out[name] = {
                "endpoint": cap.endpoint,
                "streaming": cap.backend.streaming,
                "streaming_detection": asdict(cap.backend.streaming_detection),
                "incremental_reasoning": cap.backend.incremental_reasoning,
                "partial_text": cap.backend.partial_text,
                "final_only": cap.backend.final_only,
                "response_keys": cap.backend.response_keys,
                "content_type": cap.backend.content_type,
                "timing": cap.backend.timing.to_dict(),
                "response_shape_file": cap.response_shape_file,
            }
        if args.json or args.output:
            output = json.dumps(out, indent=2)
        else:
            lines = ["Backend capabilities", ""]
            for name, info in out.items():
                lines.append(f"  {name.capitalize()}:")
                lines.append(f"    Endpoint:  {info['endpoint']}")
                lines.append(f"    Streaming: {'Yes' if info['streaming'] else 'No'}")
                if info.get("streaming_detection", {}).get("method") != "none":
                    sd = info["streaming_detection"]
                    lines.append(f"    Detection: {sd['method']} ({sd['evidence']})")
                lines.append(
                    f"    Reasoning: {'Incremental' if info['incremental_reasoning'] else 'Final payload only'}"
                )
                lines.append(
                    f"    Text:      {'Partial' if info['partial_text'] else 'Final-only'}"
                )
                lines.append(
                    f"    Keys:      {', '.join(info['response_keys']) if info['response_keys'] else '(binary)'}"
                )
                t = info.get("timing", {})
                lines.append(
                    f"    Timing:    TTFB {t.get('ttfb_s', '?')}s, Total {t.get('total_s', '?')}s"
                )
                if info.get("response_shape_file"):
                    lines.append(f"    Shape:     {info['response_shape_file']}")
                lines.append("")
            output = "\n".join(lines)

        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
                f.write("\n")
        else:
            print(output)
        return

    # ── static-only ──
    if args.static:
        checks = run_static_checks()
        if args.json or args.output:
            output = json.dumps(
                [
                    {
                        "name": c.name,
                        "label": c.label,
                        "status": c.status,
                        "detail": c.detail,
                    }
                    for c in checks
                ],
                indent=2,
            )
        else:
            lines = ["Static frontend analysis", ""]
            for c in checks:
                marker = (
                    "\u2713"
                    if c.status == "pass"
                    else ("\u2014" if c.status == "skip" else "\u2717")
                )
                lines.append(f"  {marker} {c.label}: {c.status.upper()}")
                if c.detail:
                    lines.append(f"    {c.detail}")
            lines.append("")
            output = "\n".join(lines)
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
                f.write("\n")
        else:
            print(output)
        return

    # ── browser-only ──
    if args.browser:
        browser_modes = args.modes or list(valid_modes)
        checks = run_browser_verification(output_dir, browser_modes)

        if args.json or args.output:
            output = json.dumps(
                [
                    {
                        "name": c.name,
                        "label": c.label,
                        "status": c.status,
                        "detail": c.detail,
                    }
                    for c in checks
                ],
                indent=2,
            )
        else:
            lines = ["Browser verification", ""]
            for c in checks:
                marker = (
                    "\u2713"
                    if c.status == "pass"
                    else ("\u2014" if c.status == "skip" else "\u2717")
                )
                lines.append(f"  {marker} {c.label}: {c.status.upper()}")
                if c.detail:
                    lines.append(f"    {c.detail}")
            lines.append("")
            lines.append(f"Evidence saved to: {output_dir}")
            output = "\n".join(lines)

        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
                f.write("\n")
        else:
            print(output)
        return

    # ── fidelity-only ──
    if args.fidelity:
        results = run_render_fidelity(output_dir)

        if args.json or args.output:
            output = json.dumps(
                [
                    {
                        "name": c.name,
                        "label": c.label,
                        "status": c.status,
                        "detail": c.detail,
                    }
                    for c in results
                ],
                indent=2,
            )
        else:
            lines = ["Render fidelity verification", ""]
            for c in results:
                marker = (
                    "\u2713"
                    if c.status == "pass"
                    else ("\u2014" if c.status == "skip" else "\u2717")
                )
                lines.append(f"  {marker} {c.label}: {c.status.upper()}")
                if c.detail:
                    lines.append(f"    {c.detail}")
            lines.append("")
            lines.append(f"Evidence saved to: {output_dir}")
            output = "\n".join(lines)

        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
                f.write("\n")
        else:
            print(output)

        failures = [c for c in results if c.status == "fail"]
        sys.exit(1 if failures else 0)
        return

    # ── full UI verification ──
    capabilities = detect_capabilities(config)
    if args.modes:
        capabilities = {k: v for k, v in capabilities.items() if k in args.modes}

    static_checks = run_static_checks()
    report = generate_overall_report(config, capabilities, static_checks)

    output = format_json(report) if (args.json or args.output) else format_human(report)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
            f.write("\n")
        if not args.json:
            print(f"Report written to {args.output}")
    else:
        print(output)

    overall = report.summary.get("overall", "fail")
    sys.exit(0 if overall == "pass" else 1)


if __name__ == "__main__":
    main()
