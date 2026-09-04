#!/usr/bin/env python3
"""Prepare the bundled MiniMax H3 workflow without rediscovering its graph."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_WORKFLOW = Path(__file__).parents[1] / "assets" / "minimax-h3-workflow.json"
DEFAULT_MEGAPIXELS = 0.4

BRANCHES = {
    "text": {
        "group": "文生图1",
        "prompt": 234,
        "duration": 236,
        "resolution": 235,
        "conditioning": 307,
        "task_type": "T2VA",
        "images": [],
    },
    "single": {
        "group": "单图参考1",
        "prompt": 312,
        "duration": 323,
        "resolution": 313,
        "conditioning": 333,
        "task_type": "Ref2VA",
        "images": [335],
    },
    "multi": {
        "group": "多图参考1",
        "prompt": 339,
        "duration": 350,
        "resolution": 340,
        "conditioning": 363,
        "task_type": "Ref2VA",
        "images": [362, 364, 365],
    },
}

RATIOS = {
    "1:1": "1:1 (Square)",
    "2:3": "2:3 (Portrait Photo)",
    "3:2": "3:2 (Photo)",
    "3:4": "3:4 (Portrait Standard)",
    "4:3": "4:3 (Standard)",
    "9:16": "9:16 (Portrait Widescreen)",
    "16:9": "16:9 (Widescreen)",
    "21:9": "21:9 (Ultrawide)",
}

REMOVED_NODE_TYPES = {"MarkdownNote", "Note", "Fast Groups Bypasser (rgthree)", "LoadAudio"}


class WorkflowPrepareError(ValueError):
    pass


def _node_map(workflow: dict[str, Any]) -> dict[int, dict[str, Any]]:
    nodes = workflow.get("nodes")
    if not isinstance(nodes, list):
        raise WorkflowPrepareError("Bundled workflow has no nodes list.")
    return {node.get("id"): node for node in nodes if isinstance(node, dict)}


def _branch_node_ids(workflow: dict[str, Any], title: str) -> set[int]:
    groups = workflow.get("groups")
    if not isinstance(groups, list):
        raise WorkflowPrepareError("Bundled workflow has no groups list.")
    group = next((item for item in groups if item.get("title") == title), None)
    if group is None or not isinstance(group.get("bounding"), list):
        raise WorkflowPrepareError(f"Bundled workflow is missing branch group {title!r}.")
    x, y, width, height = group["bounding"]
    result = set()
    for node in workflow["nodes"]:
        position = node.get("pos")
        if (
            isinstance(position, list)
            and len(position) >= 2
            and x <= position[0] <= x + width
            and y <= position[1] <= y + height
        ):
            result.add(node["id"])
    return result


def _set_widget(node: dict[str, Any], index: int, value: Any) -> None:
    widgets = node.get("widgets_values")
    if not isinstance(widgets, list) or len(widgets) <= index:
        raise WorkflowPrepareError(
            f"Node {node.get('id')} no longer has expected widget index {index}."
        )
    widgets[index] = value


def _remove_nodes(workflow: dict[str, Any], node_ids: set[int]) -> None:
    links_to_remove: set[int] = set()
    for node in workflow["nodes"]:
        if node.get("id") not in node_ids:
            continue
        for item in node.get("inputs") or []:
            if item.get("link") is not None:
                links_to_remove.add(item["link"])
        for item in node.get("outputs") or []:
            links_to_remove.update(item.get("links") or [])

    workflow["nodes"] = [node for node in workflow["nodes"] if node.get("id") not in node_ids]
    workflow["links"] = [link for link in workflow.get("links", []) if link[0] not in links_to_remove]

    for node in workflow["nodes"]:
        for item in node.get("inputs") or []:
            if item.get("link") in links_to_remove:
                item["link"] = None
        for item in node.get("outputs") or []:
            links = item.get("links")
            if isinstance(links, list):
                item["links"] = [link for link in links if link not in links_to_remove]


def _select_mode(image_count: int) -> str:
    if image_count == 0:
        return "text"
    if image_count == 1:
        return "single"
    if image_count <= 3:
        return "multi"
    raise WorkflowPrepareError("The bundled local workflow supports at most 3 reference images.")


def prepare_workflow(
    workflow: dict[str, Any],
    *,
    prompt: str,
    duration: float,
    ratio: str,
    images: list[str],
    megapixels: float = DEFAULT_MEGAPIXELS,
) -> dict[str, Any]:
    if not prompt.strip():
        raise WorkflowPrepareError("Prompt must not be empty.")
    if not 2 <= duration <= 15:
        raise WorkflowPrepareError("Duration must be from 2 to 15 seconds.")
    if ratio not in RATIOS:
        raise WorkflowPrepareError(f"Unsupported ratio: {ratio}.")

    mode = _select_mode(len(images))
    branch_ids = {
        name: _branch_node_ids(workflow, config["group"])
        for name, config in BRANCHES.items()
    }
    nodes = _node_map(workflow)

    required_ids = {
        value
        for config in BRANCHES.values()
        for key, value in config.items()
        if key in {"prompt", "duration", "resolution", "conditioning"}
    }
    required_ids.update(node_id for config in BRANCHES.values() for node_id in config["images"])
    missing = sorted(required_ids - nodes.keys())
    if missing:
        raise WorkflowPrepareError(f"Bundled workflow is missing expected nodes: {missing}.")

    for name, ids in branch_ids.items():
        for node_id in ids:
            nodes[node_id]["mode"] = 0 if name == mode else 4

    active = BRANCHES[mode]
    _set_widget(nodes[active["prompt"]], 0, prompt)
    _set_widget(nodes[active["duration"]], 0, duration)
    _set_widget(nodes[active["resolution"]], 0, RATIOS[ratio])
    if not 0.1 <= megapixels <= 16:
        raise WorkflowPrepareError("Megapixels must be from 0.1 to 16.")
    _set_widget(nodes[active["resolution"]], 1, megapixels)
    _set_widget(nodes[active["conditioning"]], 4, active["task_type"])

    for node_id, filename in zip(active["images"], images):
        _set_widget(nodes[node_id], 0, filename)

    unused_images = set(active["images"][len(images) :])
    removable = {
        node["id"]
        for node in workflow["nodes"]
        if node.get("type") in REMOVED_NODE_TYPES
    }
    _remove_nodes(workflow, removable | unused_images)

    workflow.setdefault("extra", {})["dsvideo"] = {
        "mode": mode,
        "task_type": active["task_type"],
        "duration_seconds": duration,
        "ratio": ratio,
        "megapixels": megapixels,
        "reference_images": len(images),
    }
    return workflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare the bundled dsvideo ComfyUI workflow")
    parser.add_argument("--workflow", type=Path, default=DEFAULT_WORKFLOW)
    prompt = parser.add_mutually_exclusive_group(required=True)
    prompt.add_argument("--prompt")
    prompt.add_argument("--prompt-file", type=Path)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--ratio", choices=RATIOS, required=True)
    parser.add_argument("--image", action="append", default=[], help="server-side ComfyUI filename")
    parser.add_argument("--megapixels", type=float, default=DEFAULT_MEGAPIXELS)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        workflow_path = args.workflow.expanduser().resolve()
        output = args.output.expanduser().resolve()
        if output == workflow_path:
            raise WorkflowPrepareError("The output path must differ from the source workflow path.")
        prompt = args.prompt
        if args.prompt_file:
            prompt = args.prompt_file.read_text(encoding="utf-8")
        workflow = json.loads(workflow_path.read_text(encoding="utf-8-sig"))
        prepared = prepare_workflow(
            workflow,
            prompt=prompt,
            duration=args.duration,
            ratio=args.ratio,
            images=args.image,
            megapixels=args.megapixels,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(prepared, ensure_ascii=False, indent=2), encoding="utf-8")
        result = prepared["extra"]["dsvideo"] | {
            "workflow": str(workflow_path),
            "output": str(output),
            "nodes": len(prepared["nodes"]),
        }
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, WorkflowPrepareError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
