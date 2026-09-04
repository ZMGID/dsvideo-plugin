#!/usr/bin/env python3
"""Dependency-free client for xAI Grok Imagine Video 1.5."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

PLUGIN_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
if str(PLUGIN_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PLUGIN_SCRIPTS))

from dsvideo_config import ConfigError, get_provider


MODEL = "grok-imagine-video-1.5"
DEFAULT_BASE_URL = "https://api.x.ai"
RESOLUTIONS = ("480p", "720p", "1080p")
RATIOS = ("1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3")
OUTPUT_PRICE_USD_PER_SECOND = {
    "480p": Decimal("0.08"),
    "720p": Decimal("0.14"),
    "1080p": Decimal("0.25"),
}
IMAGE_INPUT_PRICE_USD = Decimal("0.01")
PRICING_URL = "https://docs.x.ai/developers/pricing"
IMAGE_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}
TERMINAL_FAILURES = {"failed", "expired"}


class ApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        http_status: int | None = None,
        code: str | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.code = code
        self.request_id = request_id


def resolve_image(value: str) -> str:
    if value.startswith(("http://", "https://", "data:")):
        return value
    path = Path(value).expanduser()
    if not path.is_file():
        raise ValueError(f"File not found: {value}")
    mime = IMAGE_MIME.get(path.suffix.lower())
    if mime is None:
        supported = ", ".join(ext.removeprefix(".") for ext in IMAGE_MIME)
        raise ValueError(f"Unsupported image format {path.suffix!r}; supported: {supported}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_video_request(
    *,
    prompt: str,
    model: str = MODEL,
    resolution: str | None = None,
    duration: int = 5,
    ratio: str = "16:9",
    image: str | None = None,
    generate_audio: bool = True,
) -> dict[str, Any]:
    if not prompt.strip():
        raise ValueError("Grok video requires a non-empty prompt.")
    if resolution is None:
        raise ValueError("Grok video resolution must be explicitly selected.")
    if resolution not in RESOLUTIONS:
        raise ValueError(f"Resolution must be one of: {', '.join(RESOLUTIONS)}.")
    if isinstance(duration, bool) or not isinstance(duration, int) or not 1 <= duration <= 15:
        raise ValueError("Grok video duration must be an integer from 1 to 15 seconds.")
    if ratio not in RATIOS:
        raise ValueError(f"Ratio must be one of: {', '.join(RATIOS)}.")
    if not model.strip():
        raise ValueError("Grok video model cannot be empty.")
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": ratio,
        "resolution": resolution,
        "generate_audio": generate_audio,
    }
    if image:
        payload["image"] = {"url": resolve_image(image)}
    return payload


def cost_quote(*, duration: int, image_count: int = 0) -> dict[str, Any]:
    if isinstance(duration, bool) or not isinstance(duration, int) or not 1 <= duration <= 15:
        raise ValueError("Grok video duration must be an integer from 1 to 15 seconds.")
    if image_count not in (0, 1):
        raise ValueError("This integration accepts zero or one source image.")
    estimates = {
        resolution: format(rate * duration + IMAGE_INPUT_PRICE_USD * image_count, ".2f")
        for resolution, rate in OUTPUT_PRICE_USD_PER_SECOND.items()
    }
    return {
        "model": MODEL,
        "currency": "USD",
        "duration_seconds": duration,
        "image_count": image_count,
        "estimated_cost": estimates,
        "pricing_url": PRICING_URL,
        "note": "Estimate from the current official rate card; final billing is determined by xAI.",
    }


def paid_request_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": payload.get("model"),
        "resolution": payload.get("resolution"),
        "duration_seconds": payload.get("duration"),
        "aspect_ratio": payload.get("aspect_ratio"),
        "mode": "image-to-video" if payload.get("image") else "text-to-video",
        "generate_audio": payload.get("generate_audio"),
    }


class GrokVideoClient:
    def __init__(self, base_url: str, api_key: str, *, request_timeout: float = 60) -> None:
        if not api_key:
            raise ValueError("Grok API key is not configured.")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.request_timeout = request_timeout

    def create_video(self, payload: dict[str, Any]) -> str:
        response = self._request("POST", "/v1/videos/generations", payload)
        request_id = str(response.get("request_id", "")).strip()
        if not request_id:
            raise ApiError("xAI accepted the request but returned no request_id.")
        return request_id

    def get_video(self, request_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/videos/{quote(request_id, safe='')}")

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = None
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.request_timeout) as response:
                return _decode_json(response.read())
        except HTTPError as error:
            raise _api_error(error.read(), error.code) from None
        except URLError as error:
            raise ApiError(f"Network error: {error.reason}") from None


def wait_for_video(
    client: GrokVideoClient,
    request_id: str,
    *,
    poll_interval: float = 5,
    timeout: float = 900,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while True:
        result = client.get_video(request_id)
        status = str(result.get("status", "")).lower()
        if status == "done":
            return result
        if status in TERMINAL_FAILURES:
            detail = result.get("error") or "no error detail"
            if isinstance(detail, dict):
                detail = detail.get("message") or detail.get("code") or detail
            raise ApiError(f"Request {request_id} ended as {status}: {detail}")
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Timed out waiting for request {request_id}; resume with the wait command."
            )
        time.sleep(poll_interval)


def verify_result(result: dict[str, Any], requested: dict[str, Any], request_id: str) -> None:
    actual_model = result.get("model")
    if actual_model is not None and actual_model != requested["model"]:
        raise ApiError(
            f"Request {request_id} model mismatch: requested {requested['model']}, "
            f"received {actual_model}. The result was not downloaded."
        )
    actual_duration = (result.get("video") or {}).get("duration")
    if actual_duration is None:
        raise ApiError(
            f"Request {request_id} completed but returned no duration; "
            "the paid output contract cannot be verified."
        )
    try:
        matches = float(actual_duration) == requested["duration"]
    except (TypeError, ValueError):
        matches = False
    if not matches:
        raise ApiError(
            f"Request {request_id} duration mismatch: requested {requested['duration']}s, "
            f"received {actual_duration}s. The result was not downloaded."
        )


def download_video(
    url: str,
    output: Path,
    *,
    attempts: int = 3,
    api_key: str | None = None,
) -> int:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + ".part")
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            headers = {"User-Agent": "dsvideo-plugin/0.1"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            request = Request(url, headers=headers)
            with urlopen(request, timeout=120) as response, partial.open("wb") as target:
                content_type = response.headers.get_content_type()
                if content_type.startswith("text/") or content_type in {
                    "application/json",
                    "application/xml",
                }:
                    raise OSError(f"Download returned {content_type}, not a video.")
                while chunk := response.read(1024 * 1024):
                    target.write(chunk)
            if partial.stat().st_size == 0:
                raise OSError("Downloaded file is empty.")
            with partial.open("rb") as source:
                if source.read(8)[4:8] != b"ftyp":
                    raise OSError("Downloaded file is not an MP4 video.")
            os.replace(partial, output)
            return output.stat().st_size
        except (HTTPError, URLError, OSError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2)
    partial.unlink(missing_ok=True)
    raise ApiError(f"Video download failed after {attempts} attempts: {last_error}")


def generate_video(
    client: GrokVideoClient,
    payload: dict[str, Any],
    output: Path,
    *,
    poll_interval: float = 5,
    timeout: float = 900,
    on_submitted: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    request_id = client.create_video(payload)
    if on_submitted:
        on_submitted(request_id)
    result = wait_for_video(client, request_id, poll_interval=poll_interval, timeout=timeout)
    verify_result(result, payload, request_id)
    url = (result.get("video") or {}).get("url")
    if not url:
        raise ApiError(f"Request {request_id} completed but returned no video URL.")
    size = download_video(
        urljoin(client.base_url + "/", url),
        output,
        api_key=client.api_key if url.startswith("/") else None,
    )
    return {
        "request_id": request_id,
        "status": "done",
        "requested_resolution": payload["resolution"],
        "duration_seconds": (result.get("video") or {}).get("duration"),
        "saved": str(output.expanduser().resolve()),
        "bytes": size,
    }


def _decode_json(body: bytes) -> dict[str, Any]:
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ApiError("xAI returned a non-JSON response.") from error
    if not isinstance(value, dict):
        raise ApiError("xAI returned an unexpected JSON response.")
    return value


def _api_error(body: bytes, http_status: int) -> ApiError:
    try:
        value = _decode_json(body)
    except ApiError:
        return ApiError(f"xAI API returned HTTP {http_status}.", http_status=http_status)
    detail = value.get("error") if isinstance(value.get("error"), dict) else {}
    message = detail.get("message") or value.get("message") or f"xAI API returned HTTP {http_status}."
    code = detail.get("code")
    return ApiError(
        str(message),
        http_status=http_status,
        code=str(code) if code is not None else None,
        request_id=value.get("request_id"),
    )


def _safe_request(payload: dict[str, Any]) -> dict[str, Any]:
    value = json.loads(json.dumps(payload, ensure_ascii=False))
    image = value.get("image")
    if isinstance(image, dict) and str(image.get("url", "")).startswith("data:"):
        url = image["url"]
        image["url"] = f"<local-data-uri:{len(url.encode('utf-8'))} bytes>"
    return value


def _settings(args: argparse.Namespace) -> tuple[str, str, str]:
    provider_name = getattr(args, "provider", None) or os.environ.get(
        "DSVIDEO_VIDEO_PROVIDER", "grok"
    )
    provider = get_provider(provider_name)
    base_url = (
        getattr(args, "base_url", None)
        or os.environ.get("XAI_API_BASE")
        or provider.get("base_url")
        or DEFAULT_BASE_URL
    )
    api_key = os.environ.get("XAI_API_KEY") or provider.get("api_key") or ""
    model = (
        getattr(args, "model", None)
        or os.environ.get("XAI_VIDEO_MODEL")
        or provider.get("model")
        or MODEL
    )
    return str(base_url), str(api_key), str(model)


def _client(args: argparse.Namespace) -> GrokVideoClient:
    base_url, api_key, _model = _settings(args)
    return GrokVideoClient(base_url, api_key)


def _request_from_args(args: argparse.Namespace) -> dict[str, Any]:
    _base_url, _api_key, model = _settings(args)
    return build_video_request(
        prompt=args.prompt,
        model=model,
        resolution=args.resolution,
        duration=args.duration,
        ratio=args.ratio,
        image=args.image,
        generate_audio=not args.no_audio,
    )


def _print_json(value: Any, *, stream: Any = None) -> None:
    print(
        json.dumps(value, ensure_ascii=False, indent=2),
        file=stream or sys.stdout,
        flush=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="xAI Grok Imagine Video 1.5 client")
    parser.add_argument("--base-url", help=argparse.SUPPRESS)
    parser.add_argument("--provider", help=argparse.SUPPRESS)
    parser.add_argument("--model", help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="command", required=True)

    quote_parser = subparsers.add_parser("quote", help="estimate cost without a network request")
    quote_parser.add_argument("--duration", type=int, required=True)
    quote_parser.add_argument("--image-count", type=int, choices=(0, 1), default=0)

    def add_request_arguments(command: argparse.ArgumentParser) -> None:
        command.add_argument("--prompt", required=True)
        command.add_argument("--resolution", choices=RESOLUTIONS, required=True)
        command.add_argument("--duration", type=int, default=5)
        command.add_argument("--ratio", choices=RATIOS, default="16:9")
        command.add_argument("--image")
        command.add_argument("--no-audio", action="store_true")
        command.add_argument("--dry-run", action="store_true")

    submit = subparsers.add_parser("submit", help="create one request and return its ID")
    add_request_arguments(submit)

    generate = subparsers.add_parser("generate", help="create, wait, and download one video")
    add_request_arguments(generate)
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--poll-interval", type=float, default=5)
    generate.add_argument("--timeout", type=float, default=900)

    status = subparsers.add_parser("status", help="query one existing request")
    status.add_argument("request_id")

    wait = subparsers.add_parser("wait", help="wait for and download an existing request")
    wait.add_argument("request_id")
    wait.add_argument("--expect-duration", type=int, required=True)
    wait.add_argument("--expect-resolution", choices=RESOLUTIONS, required=True)
    wait.add_argument("--output", type=Path, required=True)
    wait.add_argument("--poll-interval", type=float, default=5)
    wait.add_argument("--timeout", type=float, default=900)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "quote":
            _print_json(cost_quote(duration=args.duration, image_count=args.image_count))
            return 0

        if args.command in {"submit", "generate"}:
            payload = _request_from_args(args)
            if args.dry_run:
                _print_json({"dry_run": True, "request": _safe_request(payload)})
                return 0
            _print_json({"paid_request": paid_request_summary(payload)}, stream=sys.stderr)
            client = _client(args)
            if args.command == "submit":
                request_id = client.create_video(payload)
                _print_json({"request_id": request_id, "status": "submitted"})
                return 0

            def submitted(request_id: str) -> None:
                _print_json({"request_id": request_id, "status": "submitted"}, stream=sys.stderr)

            result = generate_video(
                client,
                payload,
                args.output,
                poll_interval=args.poll_interval,
                timeout=args.timeout,
                on_submitted=submitted,
            )
            _print_json(result)
            return 0

        client = _client(args)
        if args.command == "status":
            _print_json(client.get_video(args.request_id))
            return 0

        _base_url, _api_key, model = _settings(args)
        requested = {"model": model, "resolution": args.expect_resolution, "duration": args.expect_duration}
        result = wait_for_video(
            client,
            args.request_id,
            poll_interval=args.poll_interval,
            timeout=args.timeout,
        )
        verify_result(result, requested, args.request_id)
        url = (result.get("video") or {}).get("url")
        if not url:
            raise ApiError(f"Request {args.request_id} completed but returned no video URL.")
        size = download_video(
            urljoin(client.base_url + "/", url),
            args.output,
            api_key=client.api_key if url.startswith("/") else None,
        )
        _print_json(
            {
                "request_id": args.request_id,
                "status": "done",
                "requested_resolution": args.expect_resolution,
                "duration_seconds": (result.get("video") or {}).get("duration"),
                "saved": str(args.output.expanduser().resolve()),
                "bytes": size,
            }
        )
        return 0
    except (ApiError, ConfigError, TimeoutError, ValueError) as error:
        _print_json(
            {
                "error": str(error),
                "http_status": getattr(error, "http_status", None),
                "code": getattr(error, "code", None),
                "request_id": getattr(error, "request_id", None),
            },
            stream=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
