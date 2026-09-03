#!/usr/bin/env python3
"""Small, dependency-free client for the MiniMax H3 Video Generation V2 API."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


MODEL = "MiniMax-H3"
MAX_REQUEST_BYTES = 64 * 1024 * 1024
RATIOS = ("adaptive", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16")
RESOLUTIONS = ("768P", "2K")
TERMINAL_FAILURES = {"failed", "cancelled", "expired"}
REGION_BASE_URLS = {
    "global": "https://api.minimax.io",
    "cn": "https://api.minimax.cn",
}
MEDIA = {
    "image": {
        "extensions": {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".heic": "image/heic",
            ".heif": "image/heif",
        },
        "max_bytes": 30 * 1024 * 1024,
    },
    "video": {
        "extensions": {".mp4": "video/mp4", ".mov": "video/quicktime"},
        "max_bytes": 50 * 1024 * 1024,
    },
    "audio": {
        "extensions": {".mp3": "audio/mp3", ".wav": "audio/wav"},
        "max_bytes": 15 * 1024 * 1024,
    },
}


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


def resolve_media_input(value: str, kind: str) -> str:
    if value.startswith(("http://", "https://", "mm_file://", "data:")):
        if kind == "audio" and value.startswith("data:audio/mpeg;base64,"):
            return value.replace("data:audio/mpeg;base64,", "data:audio/mp3;base64,", 1)
        return value

    path = Path(value).expanduser()
    if not path.is_file():
        raise ValueError(f"File not found: {value}")

    media = MEDIA[kind]
    suffix = path.suffix.lower()
    mime = media["extensions"].get(suffix)
    if mime is None:
        supported = ", ".join(ext.removeprefix(".") for ext in media["extensions"])
        raise ValueError(f"Unsupported {kind} format {suffix!r}; supported: {supported}")

    size = path.stat().st_size
    max_bytes = media["max_bytes"]
    if size > max_bytes:
        raise ValueError(
            f"{kind.capitalize()} file is {size / 1024 / 1024:.1f} MB; "
            f"the maximum is {max_bytes / 1024 / 1024:.0f} MB. "
            "Use a public URL or mm_file:// file ID."
        )

    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_video_request(
    *,
    prompt: str,
    resolution: str | None = None,
    first_frame: str | None = None,
    last_frame: str | None = None,
    reference_images: Iterable[str] | None = None,
    reference_videos: Iterable[str] | None = None,
    reference_audios: Iterable[str] | None = None,
    duration: int = 5,
    ratio: str | None = None,
    callback_url: str | None = None,
) -> dict[str, Any]:
    if not prompt.strip():
        raise ValueError("MiniMax-H3 requires a non-empty prompt.")
    if resolution is None:
        raise ValueError("MiniMax-H3 resolution must be explicitly set to 768P or 2K.")
    if resolution not in RESOLUTIONS:
        raise ValueError(f"Resolution must be one of: {', '.join(RESOLUTIONS)}.")
    if len(prompt) > 7000:
        raise ValueError("MiniMax-H3 prompt must not exceed 7000 characters.")
    if isinstance(duration, bool) or not isinstance(duration, int) or not 4 <= duration <= 15:
        raise ValueError("MiniMax-H3 duration must be an integer from 4 to 15 seconds.")
    if ratio is not None and ratio not in RATIOS:
        raise ValueError(f"Ratio must be one of: {', '.join(RATIOS)}.")

    reference_images = list(reference_images or [])
    reference_videos = list(reference_videos or [])
    reference_audios = list(reference_audios or [])
    has_frames = first_frame is not None or last_frame is not None
    has_references = bool(reference_images or reference_videos or reference_audios)

    if has_frames and has_references:
        raise ValueError("Frame inputs and reference inputs cannot be mixed.")
    if len(reference_images) > 9 or len(reference_videos) > 3 or len(reference_audios) > 3:
        raise ValueError(
            "MiniMax-H3 accepts up to 9 reference images, 3 reference videos, "
            "and 3 reference audios."
        )
    if len(reference_images) + len(reference_videos) + len(reference_audios) > 12:
        raise ValueError("MiniMax-H3 accepts at most 12 total reference media items.")
    if reference_audios and not (reference_images or reference_videos):
        raise ValueError("Reference audio requires at least one reference image or video.")

    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    if first_frame is not None:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": resolve_media_input(first_frame, "image")},
                "role": "first_frame",
            }
        )
    if last_frame is not None:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": resolve_media_input(last_frame, "image")},
                "role": "last_frame",
            }
        )
    for value in reference_images:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": resolve_media_input(value, "image")},
                "role": "reference_image",
            }
        )
    for value in reference_videos:
        content.append(
            {
                "type": "video_url",
                "video_url": {"url": resolve_media_input(value, "video")},
                "role": "reference_video",
            }
        )
    for value in reference_audios:
        content.append(
            {
                "type": "audio_url",
                "audio_url": {"url": resolve_media_input(value, "audio")},
                "role": "reference_audio",
            }
        )

    if has_frames:
        resolved_ratio = "adaptive"
    elif has_references:
        resolved_ratio = ratio or "adaptive"
    else:
        resolved_ratio = ratio or "16:9"
        if resolved_ratio == "adaptive":
            raise ValueError("Text-to-video requires a concrete ratio; adaptive is not supported.")

    request: dict[str, Any] = {
        "model": MODEL,
        "content": content,
        "resolution": resolution,
        "duration": duration,
        "ratio": resolved_ratio,
    }
    if callback_url:
        request["callback_url"] = callback_url

    body_size = len(json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    if body_size > MAX_REQUEST_BYTES:
        raise ValueError(
            f"Request body is {body_size / 1024 / 1024:.1f} MB; the maximum is 64 MB. "
            "Use public URLs or mm_file:// file IDs instead of Base64."
        )
    return request


class MiniMaxClient:
    def __init__(self, base_url: str, api_key: str, *, request_timeout: float = 60) -> None:
        if not api_key:
            raise ValueError("MINIMAX_API_KEY is not set.")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.request_timeout = request_timeout

    def create_video(self, payload: dict[str, Any]) -> str:
        response = self._request("POST", "/v2/video_generation", payload)
        task_id = str(response.get("task_id", "")).strip()
        if not task_id:
            raise ApiError("MiniMax accepted the request but returned no task_id.")
        return task_id

    def get_task(self, task_id: str) -> dict[str, Any]:
        response = self._request("GET", f"/v2/query/video_generation/{quote(task_id, safe='')}")
        task = response.get("task")
        if not isinstance(task, dict):
            raise ApiError("MiniMax returned no task object.")
        return task

    def list_tasks(
        self,
        *,
        page_num: int = 1,
        page_size: int = 20,
        status: str | None = None,
        task_ids: Iterable[str] | None = None,
        model: str | None = None,
        task_type: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page_num": page_num, "page_size": page_size}
        if status:
            params["filter.status"] = status
        if task_ids:
            params["filter.task_ids"] = list(task_ids)
        if model:
            params["filter.model"] = model
        if task_type:
            params["filter.task_type"] = task_type
        return self._request("GET", f"/v2/query/video_generation?{urlencode(params, doseq=True)}")

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
            body = error.read()
            raise _api_error(body, error.code) from None
        except URLError as error:
            raise ApiError(f"Network error: {error.reason}") from None


def wait_for_task(
    client: MiniMaxClient,
    task_id: str,
    *,
    poll_interval: float = 10,
    timeout: float = 1800,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while True:
        task = client.get_task(task_id)
        status = str(task.get("status", "")).lower()
        if status == "succeeded":
            return task
        if status in TERMINAL_FAILURES:
            error = task.get("error") or {}
            code = str(error.get("code", "")).strip()
            message = str(error.get("message", "")).strip()
            detail = f"{code}: {message}" if code and message else code or message or "no error detail"
            raise ApiError(f"Task {task_id} ended as {status}: {detail}", code=code or None)
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Timed out waiting for task {task_id}; the task may still be running. "
                "Resume with the wait command."
            )
        time.sleep(poll_interval)


def paid_request_summary(payload: dict[str, Any]) -> dict[str, Any]:
    roles = {
        item.get("role")
        for item in payload.get("content", [])
        if isinstance(item, dict) and item.get("role")
    }
    if roles & {"reference_image", "reference_video", "reference_audio"}:
        mode = "multimodal-reference"
    elif "last_frame" in roles:
        mode = "first-last-frame"
    elif "first_frame" in roles:
        mode = "first-frame"
    else:
        mode = "text-to-video"
    return {
        "model": payload.get("model"),
        "resolution": payload.get("resolution"),
        "duration_seconds": payload.get("duration"),
        "ratio": payload.get("ratio"),
        "mode": mode,
    }


def verify_task_contract(
    task: dict[str, Any],
    requested: dict[str, Any],
    task_id: str,
) -> None:
    actual_resolution = task.get("resolution")
    actual_duration = task.get("duration")
    if actual_resolution is None or actual_duration is None:
        missing = [
            name
            for name, value in (("resolution", actual_resolution), ("duration", actual_duration))
            if value is None
        ]
        raise ApiError(
            f"Task {task_id} succeeded but cannot verify the paid request contract; "
            f"response is missing {', '.join(missing)}. The result was not downloaded."
        )

    expected_resolution = requested["resolution"]
    if actual_resolution != expected_resolution:
        raise ApiError(
            f"Task {task_id} resolution mismatch: requested {expected_resolution}, "
            f"received {actual_resolution}. The result was not downloaded."
        )

    expected_duration = requested["duration"]
    try:
        duration_matches = float(actual_duration) == expected_duration
    except (TypeError, ValueError):
        duration_matches = False
    if not duration_matches:
        raise ApiError(
            f"Task {task_id} duration mismatch: requested {expected_duration}s, "
            f"received {actual_duration}s. The result was not downloaded."
        )


def download_video(url: str, output: Path, *, attempts: int = 3) -> int:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + ".part")
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": "dsvideo-plugin/0.1"})
            with urlopen(request, timeout=120) as response, partial.open("wb") as target:
                while chunk := response.read(1024 * 1024):
                    target.write(chunk)
            if partial.stat().st_size == 0:
                raise OSError("Downloaded file is empty.")
            os.replace(partial, output)
            return output.stat().st_size
        except (HTTPError, URLError, OSError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2)
    raise ApiError(f"Video download failed after {attempts} attempts: {last_error}")


def generate_video(
    client: MiniMaxClient,
    payload: dict[str, Any],
    output: Path,
    *,
    poll_interval: float = 10,
    timeout: float = 1800,
    on_submitted: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    task_id = client.create_video(payload)
    if on_submitted:
        on_submitted(task_id)
    task = wait_for_task(client, task_id, poll_interval=poll_interval, timeout=timeout)
    verify_task_contract(task, payload, task_id)
    url = (task.get("content") or {}).get("url")
    if not url:
        raise ApiError(f"Task {task_id} succeeded but returned no video URL.")
    size = download_video(url, output)
    return {
        "task_id": task_id,
        "status": "succeeded",
        "resolution": task["resolution"],
        "duration_seconds": task["duration"],
        "saved": str(output.expanduser().resolve()),
        "bytes": size,
    }


def _decode_json(body: bytes) -> dict[str, Any]:
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ApiError("MiniMax returned a non-JSON response.") from error
    if not isinstance(value, dict):
        raise ApiError("MiniMax returned an unexpected JSON response.")
    return value


def _api_error(body: bytes, http_status: int) -> ApiError:
    try:
        value = _decode_json(body)
    except ApiError:
        return ApiError(f"MiniMax API returned HTTP {http_status}.", http_status=http_status)
    detail = value.get("error") if isinstance(value.get("error"), dict) else {}
    message = detail.get("message") or f"MiniMax API returned HTTP {http_status}."
    code = _extract_error_code(detail)
    return ApiError(
        str(message),
        http_status=http_status,
        code=code,
        request_id=value.get("request_id"),
    )


def _extract_error_code(detail: dict[str, Any]) -> str | None:
    if detail.get("code") is not None:
        return str(detail["code"])
    message = str(detail.get("message", ""))
    for token in reversed(message.replace("(", " ").replace(")", " ").split()):
        if token.isdigit():
            return token
    return None


def _safe_request(payload: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(payload, ensure_ascii=False)
    value = json.loads(encoded)
    for item in value["content"]:
        media = item.get(item.get("type"))
        if isinstance(media, dict) and str(media.get("url", "")).startswith("data:"):
            url = media["url"]
            media["url"] = f"<local-data-uri:{len(url.encode('utf-8'))} bytes>"
    return value


def _base_url(args: argparse.Namespace) -> str:
    if args.base_url:
        return args.base_url
    region = args.region or os.environ.get("MINIMAX_REGION", "cn").lower()
    if region not in REGION_BASE_URLS:
        raise ValueError("MINIMAX_REGION must be global or cn.")
    return REGION_BASE_URLS[region]


def _client(args: argparse.Namespace) -> MiniMaxClient:
    return MiniMaxClient(_base_url(args), os.environ.get("MINIMAX_API_KEY", ""))


def _request_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return build_video_request(
        prompt=args.prompt,
        resolution=args.resolution,
        first_frame=args.first_frame,
        last_frame=args.last_frame,
        reference_images=args.reference_image,
        reference_videos=args.reference_video,
        reference_audios=args.reference_audio,
        duration=args.duration,
        ratio=args.ratio,
        callback_url=args.callback_url,
    )


def _print_json(value: Any, *, stream: Any = sys.stdout) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2), file=stream, flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MiniMax-H3 Video Generation V2 API client")
    parser.add_argument("--region", choices=("global", "cn"), help="API region; default: MINIMAX_REGION or cn")
    parser.add_argument("--base-url", default=os.environ.get("MINIMAX_API_BASE"), help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_request_arguments(command: argparse.ArgumentParser) -> None:
        command.add_argument("--prompt", required=True)
        command.add_argument("--resolution", choices=RESOLUTIONS, required=True)
        command.add_argument("--first-frame")
        command.add_argument("--last-frame")
        command.add_argument("--reference-image", action="append", default=[])
        command.add_argument("--reference-video", action="append", default=[])
        command.add_argument("--reference-audio", action="append", default=[])
        command.add_argument("--duration", type=int, default=5)
        command.add_argument("--ratio", choices=RATIOS)
        command.add_argument("--callback-url")
        command.add_argument("--dry-run", action="store_true")

    submit = subparsers.add_parser("submit", help="create one task and return its task ID")
    add_request_arguments(submit)

    generate = subparsers.add_parser("generate", help="create one task, wait, and download")
    add_request_arguments(generate)
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--poll-interval", type=float, default=10)
    generate.add_argument("--timeout", type=float, default=1800)

    status = subparsers.add_parser("status", help="query one existing task")
    status.add_argument("task_id")

    listing = subparsers.add_parser("list", help="list tasks from the last seven days")
    listing.add_argument("--page", type=int, default=1)
    listing.add_argument("--page-size", type=int, default=20)
    listing.add_argument("--status", choices=("queued", "running", "succeeded", "failed", "cancelled"))
    listing.add_argument("--task-id", action="append", default=[])
    listing.add_argument("--model")
    listing.add_argument("--task-type", choices=("generation", "h3_context_ir", "regeneration"))

    wait = subparsers.add_parser("wait", help="wait for an existing task without creating another")
    wait.add_argument("task_id")
    wait.add_argument("--output", type=Path)
    wait.add_argument("--poll-interval", type=float, default=10)
    wait.add_argument("--timeout", type=float, default=1800)
    wait.add_argument("--expect-resolution", choices=RESOLUTIONS)
    wait.add_argument("--expect-duration", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if hasattr(args, "poll_interval") and args.poll_interval < 10:
            raise ValueError("Poll interval must be at least 10 seconds.")
        if hasattr(args, "timeout") and args.timeout <= 0:
            raise ValueError("Timeout must be greater than zero.")

        if args.command in {"submit", "generate"}:
            payload = _request_from_args(args)
            if args.dry_run:
                _print_json(_safe_request(payload))
                return 0
            client = _client(args)
            _print_json({"paid_request": paid_request_summary(payload)}, stream=sys.stderr)
            if args.command == "submit":
                task_id = client.create_video(payload)
                _print_json({"task_id": task_id, "status": "submitted"})
                return 0

            def report_submission(task_id: str) -> None:
                _print_json(
                    {"task_id": task_id, "status": "submitted", "message": "Retain this task ID; do not resubmit."},
                    stream=sys.stderr,
                )

            result = generate_video(
                client,
                payload,
                args.output,
                poll_interval=args.poll_interval,
                timeout=args.timeout,
                on_submitted=report_submission,
            )
            _print_json(result)
            return 0

        client = _client(args)
        if args.command == "status":
            _print_json(client.get_task(args.task_id))
        elif args.command == "list":
            if args.page < 1 or not 1 <= args.page_size <= 100:
                raise ValueError("Page must be at least 1 and page size must be from 1 to 100.")
            _print_json(
                client.list_tasks(
                    page_num=args.page,
                    page_size=args.page_size,
                    status=args.status,
                    task_ids=args.task_id,
                    model=args.model,
                    task_type=args.task_type,
                )
            )
        elif args.command == "wait":
            if (args.expect_resolution is None) != (args.expect_duration is None):
                raise ValueError(
                    "Set both --expect-resolution and --expect-duration to verify the paid request contract."
                )
            if args.expect_duration is not None and not 4 <= args.expect_duration <= 15:
                raise ValueError("Expected duration must be from 4 to 15 seconds.")
            task = wait_for_task(
                client,
                args.task_id,
                poll_interval=args.poll_interval,
                timeout=args.timeout,
            )
            if args.expect_resolution is not None:
                verify_task_contract(
                    task,
                    {"resolution": args.expect_resolution, "duration": args.expect_duration},
                    args.task_id,
                )
            if args.output:
                url = (task.get("content") or {}).get("url")
                if not url:
                    raise ApiError(f"Task {args.task_id} succeeded but returned no video URL.")
                size = download_video(url, args.output)
                _print_json(
                    {
                        "task_id": args.task_id,
                        "status": "succeeded",
                        "resolution": task.get("resolution"),
                        "duration_seconds": task.get("duration"),
                        "saved": str(args.output.expanduser().resolve()),
                        "bytes": size,
                    }
                )
            else:
                _print_json(task)
        return 0
    except (ApiError, TimeoutError, ValueError) as error:
        result: dict[str, Any] = {"error": str(error)}
        if isinstance(error, ApiError):
            if error.http_status is not None:
                result["http_status"] = error.http_status
            if error.code:
                result["code"] = error.code
            if error.request_id:
                result["request_id"] = error.request_id
        _print_json(result, stream=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
