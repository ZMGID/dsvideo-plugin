---
name: grok-video-api
description: Generate, monitor, recover, and download videos through xAI's Grok Imagine Video 1.5 API or an explicitly configured compatible gateway. Use for paid Grok text-to-video or single-image-to-video; do not use for MiniMax H3 or local ComfyUI generation.
---

# Grok Imagine Video Official API

Use the bundled dependency-free `scripts/grok_video.py` client. It reads the `grok` URL, API key, and selected model from the current user's `dsvideo/providers.json`, and falls back to `grok-imagine-video-1.5` on the official `https://api.x.ai` endpoint when no saved URL/model exists. The legacy `XAI_API_BASE`, `XAI_API_KEY`, and `XAI_VIDEO_MODEL` variables remain supported as overrides.

Before a paid request, read [references/grok-video-api.md](references/grok-video-api.md). Run `quote` before presenting this route. xAI does not document a balance-query endpoint, so state that account balance must be checked in xAI Console; do not invent a balance.

## Required rules

1. Show the final user-readable video script and obtain explicit confirmation before any paid request or dry run. A modification invalidates the prior confirmation.
2. Read credentials from the saved `grok` provider or the legacy `XAI_API_KEY` override. Never print or place a literal key in a command.
3. Obtain an explicit `480p`, `720p`, or `1080p` choice for every paid creation. Never infer or silently change it.
4. Show the USD estimate from `quote`, including the selected duration and whether one source image is charged, before asking the user to choose Grok.
5. Run `--dry-run` first and compare model, resolution, duration, aspect ratio, mode, and audio with the confirmed request.
6. Run exactly one `generate` command for a completed file. It submits once, prints the request ID, polls that request, checks returned duration, and downloads the MP4.
7. After timeout or interruption, resume with `status` or `wait` and the same request ID. Never resubmit automatically.
8. A dry run is free but does not verify credentials or produce a video.

## Quote

```text
python <skill-directory>/scripts/grok_video.py quote --duration <1-15> --image-count <0-or-1>
```

The current official output rates are USD $0.08/sec for 480p, $0.14/sec for 720p, and $0.25/sec for 1080p. Image input adds $0.01 per image. Treat the quote as an estimate and link the official pricing page.

## Generate

```text
python <skill-directory>/scripts/grok_video.py generate \
  --prompt "<confirmed prompt>" \
  --resolution <480p-or-720p-or-1080p> \
  --duration <1-15> \
  --ratio <ratio> \
  [--image <local-path-or-public-url>] \
  [--no-audio] \
  --output <output.mp4>
```

Run the same command with `--dry-run` before removing that flag for the paid call. Local JPG/JPEG/PNG/WebP images are converted to data URIs; public HTTP(S) URLs and existing data URIs pass through.

## Recover

```text
python <skill-directory>/scripts/grok_video.py status <request-id>
python <skill-directory>/scripts/grok_video.py wait <request-id> \
  --expect-resolution <resolution> --expect-duration <seconds> --output <output.mp4>
```

The result URL is temporary, so download promptly. The client accepts both absolute xAI URLs and gateway-relative `/v1/videos/.../content` URLs; it sends the API credential on relative same-gateway downloads only. Deliver the local MP4 path, request ID, mode, selected resolution, verified duration, aspect ratio, and that Grok was the paid route.
