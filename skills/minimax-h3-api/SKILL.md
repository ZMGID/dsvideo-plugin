---
name: minimax-h3-api
description: Generate, monitor, recover, and download MiniMax-H3 videos through MiniMax's official Video Generation V2 API. Use for paid H3 text-to-video, first/last-frame video, or multimodal reference video; do not use for local ComfyUI generation or legacy Hailuo models.
---

# MiniMax H3 Official API

Use the bundled `scripts/minimax_h3.py` client. It has no third-party Python dependencies and fixes the model to `MiniMax-H3` on the official `/v2/video_generation` API.

Before a paid request, read [references/h3-api.md](references/h3-api.md) for credentials, input constraints, task recovery, and failure handling.

Before presenting the API route for a new video, run `quote` for both resolution estimates and `balance` for the current pay-as-you-go balance. These commands do not create a video task. The bundled quote is a CNY estimate for `cn` accounts only; never present it as a USD or `global` estimate.

## Required Rules

1. Before constructing the final H3 prompt or running `--dry-run`, show the current user-readable video script and obtain explicit confirmation after it is displayed. Route choice, resolution choice, or an earlier request to generate does not confirm an unseen script. Any script or generation-spec change invalidates the confirmation and requires the revised script to be shown and confirmed again.
2. Use a Pay-as-you-go API key supplied through `MINIMAX_API_KEY`. Never print, repeat, save, or place a literal key in a command.
3. Select `global` or `cn` with `MINIMAX_REGION`. This plugin defaults to `cn`, using the official `https://api.minimaxi.com` endpoint; use `global` only when the user explicitly has an international API account.
4. Obtain an explicit `768P` or `2K` choice from the user for every paid create request. Never infer, default, upgrade, or downgrade the resolution.
5. Show the current balance with the currency returned by `balance` and the estimated cost before asking the user to choose the API route. If balance lookup fails, report that it is unavailable and still show the estimate. For `global`, stop before paid creation unless a reliable current international estimate is available; never reuse the bundled CNY quote. Never treat an estimate as the final charge.
6. Run `--dry-run` first and check `model`, `resolution`, `duration`, `ratio`, and mode against the request. The paid command prints the same billable request summary immediately before its single POST.
7. Run exactly one `generate` command when the user wants a completed file. The script submits once, prints the task ID immediately, polls that task, verifies the returned resolution and duration, and then downloads its result.
8. If the terminal remains active, wait on that exact execution session. Do not submit another task.
9. After a timeout or interruption, recover with `status` or `wait` and the existing task ID. Pass the originally requested resolution and duration to `wait` so the result contract is verified before download. Never create a replacement merely because polling or downloading stopped.
10. Use `submit` only when the user explicitly wants an asynchronous task ID without waiting for a file.
11. A dry run does not need credentials and cannot incur a charge, but it is not proof that the API key works or that a video was generated.

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

## Balance And Estimate

```text
python <skill-directory>/scripts/minimax_h3.py balance
python <skill-directory>/scripts/minimax_h3.py quote --duration <4-15> --reference-image-count <count> --reference-video-seconds <total-seconds>
```

`quote` returns both `768P` and `2K` estimates in CNY from the pricing snapshot documented in `references/h3-api.md`. It makes no network request and creates no task. `balance` performs only the official read-only account balance request and requires `MINIMAX_API_KEY`.

The client converts supported local files to Data URIs. Public `http(s)` URLs, existing Data URIs, and `mm_file://` IDs are passed through. Use URLs or file IDs when Base64 would exceed the 64 MB request limit.

## Existing Tasks

```text
python <skill-directory>/scripts/minimax_h3.py status <task-id>
python <skill-directory>/scripts/minimax_h3.py wait <task-id> --expect-resolution <768P-or-2K> --expect-duration <4-15> --output <output.mp4>
python <skill-directory>/scripts/minimax_h3.py list --page 1 --page-size 20 --status succeeded --model MiniMax-H3
```

V2 tasks remain queryable through the list endpoint for seven days. Retain the task ID in the user-visible result whenever the requested outcome is not yet downloaded and verified.

## Delivery

For a completed request, verify that the reported local MP4 exists and is non-empty, then return its path, task ID, input mode, verified resolution, verified duration, ratio, and that the user selected the paid API route. Do not describe submission or a running task as a completed video.
