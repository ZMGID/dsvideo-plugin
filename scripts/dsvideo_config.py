#!/usr/bin/env python3
"""Manage dsvideo API providers in one per-user JSON file."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CONFIG_VERSION = 1
VIDEO_MODEL_HINTS = (
    "video",
    "seedance",
    "veo",
    "sora",
    "kling",
    "hailuo",
    "minimax-h3",
    "wan2",
)


class ConfigError(RuntimeError):
    pass


def config_path() -> Path:
    override = os.environ.get("DSVIDEO_CONFIG_PATH")
    if override:
        return Path(override).expanduser()
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "dsvideo" / "providers.json"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    root = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return root / "dsvideo" / "providers.json"


def load_config(path: Path | None = None) -> dict[str, Any]:
    target = path or config_path()
    if not target.exists():
        return {"version": CONFIG_VERSION, "providers": {}}
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ConfigError(f"Cannot read dsvideo config: {error}") from error
    if not isinstance(value, dict) or not isinstance(value.get("providers"), dict):
        raise ConfigError("dsvideo config must contain a providers object.")
    return value


def get_provider(name: str, path: Path | None = None) -> dict[str, Any]:
    value = load_config(path).get("providers", {}).get(name, {})
    return value if isinstance(value, dict) else {}


def save_provider(name: str, provider: dict[str, Any], path: Path | None = None) -> Path:
    if not name or any(character.isspace() for character in name):
        raise ConfigError("Provider name must be non-empty and contain no spaces.")
    target = path or config_path()
    config = load_config(target)
    config["version"] = CONFIG_VERSION
    config.setdefault("providers", {})[name] = provider
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix="providers-", suffix=".tmp", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(config, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
        os.chmod(target, 0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def normalize_base_url(value: str) -> str:
    base_url = value.strip().rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]
    if not base_url.startswith(("http://", "https://")):
        raise ConfigError("API URL must start with http:// or https://.")
    return base_url


def fetch_models(
    base_url: str,
    api_key: str,
    *,
    opener: Callable[..., Any] = urlopen,
) -> list[str]:
    request = Request(
        normalize_base_url(base_url) + "/v1/models",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
    )
    try:
        with opener(request, timeout=60) as response:
            value = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise ConfigError(f"Model request returned HTTP {error.code}.") from None
    except URLError as error:
        raise ConfigError(f"Model request failed: {error.reason}") from None
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ConfigError("Model endpoint did not return valid JSON.") from error
    entries = value.get("data") if isinstance(value, dict) else None
    if not isinstance(entries, list):
        raise ConfigError("Model response does not contain a data list.")
    identifiers = sorted(
        {
            str(entry.get("id", "")).strip()
            for entry in entries
            if isinstance(entry, dict) and str(entry.get("id", "")).strip()
        }
    )
    video_models = [
        model
        for model in identifiers
        if any(hint in model.lower() for hint in VIDEO_MODEL_HINTS)
    ]
    return video_models or identifiers


def _read_secret(use_stdin: bool) -> str:
    secret = sys.stdin.read().strip() if use_stdin else getpass.getpass("API Key: ").strip()
    if not secret:
        raise ConfigError("API Key cannot be empty.")
    return secret


def _redacted_config() -> dict[str, Any]:
    value = load_config()
    for provider in value.get("providers", {}).values():
        if isinstance(provider, dict) and provider.get("api_key"):
            provider["api_key"] = "<saved>"
    value["path"] = str(config_path().resolve())
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Configure dsvideo API providers")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("path", help="show the per-user JSON path")
    commands.add_parser("show", help="show saved providers without secrets")

    minimax = commands.add_parser("set-minimax", help="save the fixed MiniMax-H3 API key")
    minimax.add_argument("--api-key-stdin", action="store_true")

    provider = commands.add_parser(
        "set-provider", help="save an OpenAI-compatible video provider and fetch models"
    )
    provider.add_argument("--name", required=True)
    provider.add_argument("--base-url", required=True)
    provider.add_argument("--model")
    provider.add_argument("--api-key-stdin", action="store_true")

    models = commands.add_parser("models", help="refresh models for a saved provider")
    models.add_argument("--name", required=True)

    select = commands.add_parser("select-model", help="save one fetched model")
    select.add_argument("--name", required=True)
    select.add_argument("--model", required=True)
    return parser


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "path":
            _print({"path": str(config_path().resolve())})
            return 0
        if args.command == "show":
            _print(_redacted_config())
            return 0
        if args.command == "set-minimax":
            target = save_provider(
                "minimax",
                {"type": "minimax-h3", "api_key": _read_secret(args.api_key_stdin)},
            )
            _print({"provider": "minimax", "model": "MiniMax-H3", "saved": str(target.resolve())})
            return 0
        if args.command == "set-provider":
            api_key = _read_secret(args.api_key_stdin)
            base_url = normalize_base_url(args.base_url)
            models = fetch_models(base_url, api_key)
            selected = args.model
            if selected and selected not in models:
                raise ConfigError("Selected model was not returned by the provider.")
            if not selected and sys.stdin.isatty():
                for index, model in enumerate(models, start=1):
                    print(f"{index}. {model}", file=sys.stderr)
                choice = input("选择模型编号: ").strip()
                if not choice.isdigit() or not 1 <= int(choice) <= len(models):
                    raise ConfigError("Invalid model selection.")
                selected = models[int(choice) - 1]
            provider = {"type": "openai-video", "base_url": base_url, "api_key": api_key}
            if selected:
                provider["model"] = selected
            target = save_provider(args.name, provider)
            _print(
                {
                    "provider": args.name,
                    "models": models,
                    "selected_model": selected,
                    "selection_required": selected is None,
                    "saved": str(target.resolve()),
                }
            )
            return 0
        provider = get_provider(args.name)
        if provider.get("type") != "openai-video":
            raise ConfigError(f"Provider {args.name!r} is not configured as openai-video.")
        models = fetch_models(str(provider.get("base_url", "")), str(provider.get("api_key", "")))
        if args.command == "models":
            _print({"provider": args.name, "models": models})
            return 0
        if args.model not in models:
            raise ConfigError("Selected model was not returned by the provider.")
        provider["model"] = args.model
        target = save_provider(args.name, provider)
        _print({"provider": args.name, "selected_model": args.model, "saved": str(target.resolve())})
        return 0
    except ConfigError as error:
        _print({"error": str(error)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
