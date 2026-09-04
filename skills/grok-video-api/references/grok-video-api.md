# Grok Imagine Video 1.5 API Guide

## Official references

- [Video generation](https://docs.x.ai/developers/model-capabilities/video/generation)
- [Image-to-video](https://docs.x.ai/developers/model-capabilities/video/image-to-video)
- [Pricing](https://docs.x.ai/developers/pricing)

## Contract

- Model: `grok-imagine-video-1.5`.
- Create: `POST https://api.x.ai/v1/videos/generations`.
- Query: `GET https://api.x.ai/v1/videos/{request_id}`.
- Statuses: `pending`, `done`, `failed`, `expired`.
- Duration: integer 1–15 seconds.
- Ratios: `1:1`, `16:9`, `9:16`, `4:3`, `3:4`, `3:2`, `2:3`.
- Resolution: `480p`, `720p`, or `1080p` for text-to-video and image-to-video.
- Input mode in this integration: prompt only, or prompt plus one starting image.
- Generated video includes audio by default; `generate_audio: false` requests silent output.
- Output URLs are temporary and must be downloaded promptly.
- The saved `grok` provider supplies the URL, key, and selected model. `XAI_API_BASE`, `XAI_API_KEY`, and `XAI_VIDEO_MODEL` remain legacy overrides.
- Official xAI responses normally return absolute temporary URLs. Compatible gateways may return relative same-host content URLs that require the Bearer credential; the bundled client supports both forms.

The price snapshot checked on 2026-09-04 is $0.08/output second for 480p, $0.14/output second for 720p, and $0.25/output second for 1080p. Image media input is $0.01 per image. xAI publishes no balance-query endpoint in the referenced API documentation; use xAI Console for account balance and final billing.

## Failure handling

| Failure | Action |
|---|---|
| Missing key | Run the plugin's `scripts/dsvideo_config.py set-provider --name grok --base-url <URL>` flow and use hidden input. |
| HTTP 401/403 | Stop and verify key/team access without creating another request. |
| HTTP 429 | Retry only when the response proves no request was created. |
| HTTP 5xx during creation | Do not assume it was unbilled; investigate before another paid POST. |
| `failed` or `expired` | Report the request ID and error; require approval for a new paid request. |
| Poll timeout | Resume the same request with `wait`. |
| Download failure | Retry the temporary URL; do not regenerate. |
