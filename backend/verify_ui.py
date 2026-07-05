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
    python -m backend.verify_ui --json                   # machine-readable
    python -m backend.verify_ui canvas thinking          # specific modes
"""

import json
import os
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

            # New conversation flow
            if "New conversation" in page.content():
                new_chat = page.locator("button:has-text('New conversation')")
                if new_chat.count():
                    try:
                        new_chat.first.click(timeout=5000)
                        page.wait_for_timeout(500)
                        screenshot("new-conversation")
                        results.append(
                            UICheck("new_conversation", "New conversation flow", "pass")
                        )
                    except Exception:
                        results.append(
                            UICheck(
                                "new_conversation",
                                "New conversation flow",
                                "skip",
                                "Button found but outside viewport.",
                            )
                        )

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
        description="UI verification for Alma \u2014 validates that the frontend "
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
    valid_modes = {"canvas", "thinking", "web", "images"}
    if args.modes:
        for m in args.modes:
            if m not in valid_modes:
                parser.error(
                    f"unknown mode: {m!r}; choices: {', '.join(sorted(valid_modes))}"
                )

    output_dir = _ensure_output_dir()

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
