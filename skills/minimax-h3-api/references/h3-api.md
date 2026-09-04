# MiniMax H3 V2 API Guide

Read this file before sending a paid request or recovering an existing task.

## Official References

- [创建视频生成任务](https://platform.minimaxi.com/docs/api-reference/video-generation-v2-create)
- [查询任务](https://platform.minimaxi.com/docs/api-reference/video-generation-v2-query)
- [查询任务列表](https://platform.minimaxi.com/docs/api-reference/video-generation-v2-list)
- [Pay-as-you-go pricing](https://platform.minimaxi.com/docs/guides/pricing-paygo)
- [Official CLI balance endpoint](https://github.com/MiniMax-AI/cli/blob/main/src/client/endpoints.ts)

## Credentials And Region

- H3 requires a Pay-as-you-go/Credit API key, not an OAuth or Token Plan subscription credential.
- The bundled client reads the key from the current user's `dsvideo/providers.json`; `MINIMAX_API_KEY` remains a legacy override. It sends the key as a Bearer credential.
- It reads the region from `MINIMAX_REGION`: `cn` uses the official `https://api.minimaxi.com`; `global` uses `https://api.minimax.io`. When neither the environment nor `--region` selects a region, the client defaults to `cn`.
- `MINIMAX_API_BASE` is an advanced endpoint override. Do not use it unless the user explicitly configured a compatible gateway or a local test server.
- Never put a key in a command, repository file, skill file, shell transcript, or final response. If no saved key is available, run `scripts/dsvideo_config.py set-minimax` and let the user enter it through the hidden prompt.

## API Lifecycle

The client uses only the official V2 lifecycle:

1. `POST /v2/video_generation` creates one task and returns `task_id`.
2. `GET /v2/query/video_generation/{task_id}` returns its status and result.
3. On `succeeded`, `task.content.url` is downloaded directly.
4. `GET /v2/query/video_generation` lists tasks from the last seven days.

Statuses are `queued`, `running`, `succeeded`, `failed`, `cancelled`, and, for task recovery, `expired`.

Once a task ID exists, all recovery must use that ID. A polling timeout, terminal interruption, or download failure never authorizes another paid `POST`.

## Paid Request Guard

- `resolution` is required by the official create API. For `MiniMax-H3`, select exactly `768P` or `2K`; the client has no default.
- Before the POST, the client prints the actual `model`, `resolution`, output duration, ratio, and input mode that it will submit. Check these fields against the user's request.
- A successful task response must report the same resolution and duration. The client stops before download if either field is missing or mismatched, retaining the task ID for diagnosis without another paid submission.
- The China-region price snapshot checked on 2026-09-03 is `¥0.50/output second` for `768P` and `¥0.80/output second` for `2K`. Reference audio is free; up to 5 reference images are free and each additional image costs `¥0.20`; reference-video input seconds use the selected output resolution's per-second rate. The `quote` command applies these CNY rules only to `cn` accounts and must link the official [Pay-as-you-go pricing](https://platform.minimaxi.com/docs/guides/pricing-paygo). Treat its result as an estimate because pricing may change. Never relabel or reuse it as a `global` USD estimate; without a reliable current international quote, stop before paid creation.
- The `balance` command calls `GET /account/query_balance`, the read-only balance route used by MiniMax's official CLI. It does not create a video task.

## Input Modes

- Text-to-video: prompt only. Ratio must be a concrete value; the client defaults to `16:9` when none is supplied.
- First/last-frame video: prompt plus one first frame, one last frame, or both. The API derives the ratio from the frame and uses `adaptive`.
- Reference-to-video: prompt plus reference images, videos, and/or audio. Ratio defaults to `adaptive` but may be set explicitly.

Frame mode and reference mode are mutually exclusive. Reference audio requires at least one reference image or reference video.

## Limits

- Prompt: 1-7000 characters.
- Output: `MiniMax-H3`, explicitly selected `768P` or `2K`, integer duration 4-15 seconds.
- Ratio: `adaptive`, `21:9`, `16:9`, `4:3`, `1:1`, `3:4`, or `9:16`.
- Reference images: at most 9; JPG/JPEG/PNG/WebP/HEIC/HEIF; at most 30 MB each; sides 256-5760 px; aspect ratio 0.4-2.5.
- Reference videos: at most 3; MP4/MOV with H.264/H.265 video; at most 50 MB each; 2-15 seconds each and 15 seconds total; 23.976-60 FPS.
- Reference audio: at most 3; MP3/WAV; at most 15 MB each; 2-15 seconds each and 15 seconds total.
- Mixed reference media: at most 12 items total.
- Complete JSON request body: at most 64 MB.

The client validates paths, extensions, individual file sizes, counts, mode compatibility, output duration, ratio, prompt length, and total encoded request size. It does not inspect video/audio codecs, frame rate, duration, or image dimensions. Inspect unknown local media before a paid request; do not transcode media that already satisfies the limits.

## Commands

Dry-run request construction without a key or charge:

```text
python <script> generate --prompt "<prompt>" --resolution 768P --duration 5 --ratio 9:16 --output result.mp4 --dry-run
```

Balance and estimates before route selection:

```text
python <script> balance
python <script> quote --duration 10 --reference-image-count 1 --reference-video-seconds 0
```

Completed text-to-video:

```text
python <script> generate --prompt "<prompt>" --resolution 768P --duration 5 --ratio 9:16 --output result.mp4
```

Completed first/last-frame video:

```text
python <script> generate --prompt "<prompt>" --resolution 768P --first-frame start.png --last-frame end.png --duration 5 --output result.mp4
```

Completed reference video:

```text
python <script> generate --prompt "<prompt>" --resolution 768P --reference-image product.png --reference-video motion.mp4 --duration 5 --ratio 9:16 --output result.mp4
```

Async task ID only:

```text
python <script> submit --prompt "<prompt>" --resolution 768P --duration 5 --ratio 9:16
```

Resume rather than resubmit:

```text
python <script> wait <task-id> --expect-resolution 768P --expect-duration 5 --output result.mp4 --poll-interval 10 --timeout 1800
```

Global options such as `--region` appear before the subcommand.

The list command supports the official status, repeated task ID, model, and task-type filters, for example:

```text
python <script> list --status succeeded --task-id <task-id> --model MiniMax-H3 --task-type generation
```

## Failure Handling

| Failure | Action |
|---|---|
| Missing key | Run the plugin's `scripts/dsvideo_config.py set-minimax` flow and use hidden input. |
| HTTP 401/403 or code 1004/2049 | Stop. Check the configured region and key outside the paid create path. |
| HTTP 402 or code 1008 | Stop and report insufficient balance. |
| HTTP 422 or code 1026/1027 | Report the rejected prompt/media and ask the user to revise it; do not silently rewrite. |
| HTTP 429 or code 1002 before task creation | Wait, then retry the unchanged request only when the response proves no task was created. |
| HTTP 5xx before task creation | Do not assume the request was unbilled. Check the V2 task list before considering another create request. |
| Existing-task query 5xx | Wait at least 10 seconds and query the same task again, up to three times. |
| `failed`, `cancelled`, or `expired` | Report task ID and error. Require user approval before any new paid task. |
| Polling timeout | Report the existing task ID and resume with `wait`; do not resubmit. |
| Download failure after `succeeded` | Retry downloading the same result URL; never regenerate. |

The API does not promise an exact completion time or progress percentage. Do not invent either.
