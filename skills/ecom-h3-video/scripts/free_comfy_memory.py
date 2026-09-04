#!/usr/bin/env python3
"""Unload ComfyUI models when no consecutive task remains in the queue."""

from __future__ import annotations

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://192.168.1.171:8188"


class ComfyMemoryError(RuntimeError):
    pass


def normalize_base_url(value: str) -> str:
    base_url = value.strip().rstrip("/")
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ComfyMemoryError("ComfyUI 地址无效")
    return base_url


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    timeout: float = 15.0,
    opener=None,
):
    opener = opener or urlopen
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with opener(request, timeout=timeout) as response:
            body = response.read()
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise ComfyMemoryError(f"无法访问 ComfyUI：{error}") from error

    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ComfyMemoryError("ComfyUI 返回了无效 JSON") from error


def free_comfy_memory(
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = 15.0,
    opener=None,
) -> dict:
    base_url = normalize_base_url(base_url)
    queue = request_json(f"{base_url}/queue", timeout=timeout, opener=opener)
    if not isinstance(queue, dict):
        raise ComfyMemoryError("ComfyUI 队列响应格式无效")

    running = queue.get("queue_running")
    pending = queue.get("queue_pending")
    if not isinstance(running, list) or not isinstance(pending, list):
        raise ComfyMemoryError("ComfyUI 队列响应缺少 queue_running 或 queue_pending")
    if running or pending:
        return {
            "status": "skipped_consecutive_tasks",
            "running": len(running),
            "pending": len(pending),
        }

    request_json(
        f"{base_url}/free",
        method="POST",
        payload={"unload_models": True, "free_memory": True},
        timeout=timeout,
        opener=opener,
    )
    return {"status": "freed", "unload_models": True, "free_memory": True}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="无连续任务时卸载 ComfyUI 模型并释放内存")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"ComfyUI 地址，默认 {DEFAULT_BASE_URL}",
    )
    parser.add_argument("--timeout", type=float, default=15.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = free_comfy_memory(args.base_url, args.timeout)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except ComfyMemoryError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
