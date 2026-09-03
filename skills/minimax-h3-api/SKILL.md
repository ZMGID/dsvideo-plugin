---
name: minimax-h3-api
description: Generate, monitor, recover, and download MiniMax-H3 videos through MiniMax's official Video Generation V2 API. Use for paid H3 text-to-video, first/last-frame video, or multimodal reference video; do not use for local ComfyUI generation or legacy Hailuo models.
---

# MiniMax H3 Official API

Use the bundled `scripts/minimax_h3.py` client. It has no third-party Python dependencies and fixes the model to `MiniMax-H3` on the official `/v2/video_generation` API.

Before a paid request, read [references/h3-api.md](references/h3-api.md) for credentials, input constraints, task recovery, and failure handling.

## Required Rules

1. Use a Pay-as-you-go API key supplied through `MINIMAX_API_KEY`. Never print, repeat, save, or place a literal key in a command.
2. Select `global` or `cn` with `MINIMAX_REGION`. This plugin defaults to `cn`, using the official `https://api.minimax.cn` endpoint; use `global` only when the user explicitly has an international API account.
3. Obtain an explicit `768P` or `2K` choice from the user for every paid create request. Never infer, default, upgrade, or downgrade the resolution.
4. Run `--dry-run` first and check `model`, `resolution`, `duration`, `ratio`, and mode against the request. The paid command prints the same billable request summary immediately before its single POST.
5. Run exactly one `generate` command when the user wants a completed file. The script submits once, prints the task ID immediately, polls that task, verifies the returned resolution and duration, and then downloads its result.
6. If the terminal remains active, wait on that exact execution session. Do not submit another task.
7. After a timeout or interruption, recover with `status` or `wait` and the existing task ID. Pass the originally requested resolution and duration to `wait` so the result contract is verified before download. Never create a replacement merely because polling or downloading stopped.
8. Use `submit` only when the user explicitly wants an asynchronous task ID without waiting for a file.
9. A dry run does not need credentials and cannot incur a charge, but it is not proof that the API key works or that a video was generated.

## Resolve The Client

Resolve this skill's directory, then invoke its bundled script with an available Python 3 interpreter:

```text
python <skill-directory>/scripts/minimax_h3.py --help
```

Do not install `mmx-cli`, Node packages, or Python packages for this client.

## Completed Video

```text
python <skill-directory>/scripts/minimax_h3.py --region <global-or-cn> generate \
  --prompt "<video prompt>" \
  --resolution <768P-or-2K> \
  --duration <4-15> \
  --ratio <ratio> \
  --output <output.mp4> \
  --poll-interval 10 \
  --timeout 1800
```

For frame-based generation, add `--first-frame`, `--last-frame`, or both. For reference generation, repeat `--reference-image`, `--reference-video`, and `--reference-audio` once per input. Frame inputs and reference inputs cannot be mixed.

The client converts supported local files to Data URIs. Public `http(s)` URLs, existing Data URIs, and `mm_file://` IDs are passed through. Use URLs or file IDs when Base64 would exceed the 64 MB request limit.

## Existing Tasks

```text
python <skill-directory>/scripts/minimax_h3.py status <task-id>
python <skill-directory>/scripts/minimax_h3.py wait <task-id> --expect-resolution <768P-or-2K> --expect-duration <4-15> --output <output.mp4>
python <skill-directory>/scripts/minimax_h3.py list --page 1 --page-size 20 --status succeeded --model MiniMax-H3
```

V2 tasks remain queryable through the list endpoint for seven days. Retain the task ID in the user-visible result whenever the requested outcome is not yet downloaded and verified.

## Delivery

For a completed request, verify that the reported local MP4 exists and is non-empty, then return its path, task ID, input mode, verified resolution, verified duration, ratio, and whether the paid API fallback was used. Do not describe submission or a running task as a completed video.
