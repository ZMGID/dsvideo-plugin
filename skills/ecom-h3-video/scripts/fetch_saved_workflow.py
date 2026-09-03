#!/usr/bin/env python3
"""Fetch the fixed company workflow from ComfyUI user data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://192.168.1.171:8188"
WORKFLOW_NAME = "【Work-Fisher】Minimax-H3 整合流程.json"


class WorkflowFetchError(RuntimeError):
    pass


def normalize_base_url(value: str) -> str:
    base_url = value.strip().rstrip("/")
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise WorkflowFetchError("ComfyUI 地址无效")
    return base_url


def list_url(base_url: str) -> str:
    query = urlencode({"dir": "workflows", "recurse": "true", "split": "false"})
    return f"{normalize_base_url(base_url)}/userdata?{query}"


def workflow_url(base_url: str) -> str:
    encoded_path = quote(f"workflows/{WORKFLOW_NAME}", safe="")
    return f"{normalize_base_url(base_url)}/userdata/{encoded_path}"


def request_bytes(url: str, timeout: float = 15.0, opener=None) -> bytes:
    opener = opener or urlopen
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with opener(request, timeout=timeout) as response:
            return response.read()
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise WorkflowFetchError(f"无法读取 ComfyUI：{error}") from error


def parse_json(payload: bytes, label: str):
    try:
        return json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WorkflowFetchError(f"{label}不是有效 JSON") from error


def fetch_saved_workflow(
    output_path: Path,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = 15.0,
    opener=None,
) -> dict:
    names = parse_json(request_bytes(list_url(base_url), timeout, opener), "工作流列表")
    if not isinstance(names, list) or WORKFLOW_NAME not in names:
        raise WorkflowFetchError(f"未找到指定工作流：{WORKFLOW_NAME}")

    payload = request_bytes(workflow_url(base_url), timeout, opener)
    workflow = parse_json(payload, "指定工作流")
    if not isinstance(workflow, dict) or not isinstance(workflow.get("nodes"), list):
        raise WorkflowFetchError("指定工作流缺少 nodes")

    output_path = output_path.resolve()
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path.write_bytes(payload)
        temporary_path.replace(output_path)
    except OSError as error:
        raise WorkflowFetchError(f"无法保存临时工作流：{error}") from error
    return {
        "workflow": WORKFLOW_NAME,
        "nodes": len(workflow["nodes"]),
        "path": str(output_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="读取公司 ComfyUI 中指定的 H3 工作流")
    parser.add_argument("output", type=Path, help="临时原始工作流 JSON 的保存路径")
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
        result = fetch_saved_workflow(args.output, args.base_url, args.timeout)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except WorkflowFetchError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
