# ComfyUI Workflow Safety

Read this file before running a local ComfyUI workflow for a user who already has a configured workflow.

## Authority And Mutation Boundary

The exact workflow file or template selected by the user is the authoritative graph. Do not reconstruct it from node schemas, replace it with a similar gallery template, or overwrite the source file.

Create a one-run derived copy. Change only exact fields needed for the current request and only after identifying their existing node/slot addresses:

- Positive generation prompt requested for this run.
- Input image or input video references.
- Video width and height needed for the requested aspect ratio or resolution.
- The workflow's existing duration or frame-count field. If duration must be represented as frames, calculate it from the workflow's existing FPS and keep FPS unchanged.

An output directory passed to `run_workflow` is outside the graph and does not require a workflow mutation. Do not change negative prompts, seeds, batch size, or any other convenient-looking field unless the user explicitly requests that exact change.

## Protected By Default

Do not change any of the following unless the user explicitly requests that field:

- Model, checkpoint, VAE, text encoder, CLIP, LoRA, quantization, precision, device, or offload settings.
- `steps`, `video_steps`, sampling steps, CFG/guidance, sampler, scheduler, denoise, shift, sigma, or noise controls.
- FPS, interpolation, upscaling, decoding, color, audio, or post-processing settings.
- Node class, node ID, graph links, subgraphs, disabled/bypassed state, or graph topology.
- Custom-node implementation settings or local/partner API provider selection.

Changing `video_steps` from `10` to `4` is a protected-field violation, not an optimization. A slow run, queue delay, validation error, OOM, or runtime crash does not authorize quality degradation. Diagnose and report the failure against the unchanged graph.

## Safe comfy-mcp Procedure

1. Resolve the user's exact workflow path or exact template name. If it cannot be identified unambiguously, stop and ask; do not choose a substitute.
2. Read the workflow, record its path and SHA-256, and keep the source file read-only for the run.
3. Inspect the existing slots and identify the exact addresses for only the requested prompt, media, dimensions, and duration. Do not guess a slot because its label looks similar.
4. Prefer `set_workflow_slot` with `stdout=True`, which returns a modified workflow without mutating the source. Save that result as a separate temporary candidate when a file is needed for validation or execution.
5. Validate the candidate against the live ComfyUI installation. A missing model, node, or option is a failure to report, not permission to replace it.
6. Compare the source and candidate JSON. Declare each permitted changed JSON Pointer explicitly and run the bundled guard. Any undeclared difference blocks submission.
7. Run the validated candidate with `run_workflow` and `confirm_spend=False`. Do not use a generic generation helper that constructs a different default graph.
8. Retain the returned `prompt_id`; monitor and download that exact job. Do not rebuild the graph after a wait timeout.
9. Confirm the original workflow SHA-256 is unchanged, then report the changed fields and their before/after values.

Official `comfy-mcp` exposes non-destructive slot editing and workflow execution separately. Keep them separate so the proposed graph can be audited before it is queued.

## Deterministic Difference Guard

For two workflow JSON files in the same format, run:

```text
python <skill-directory>/scripts/comfy_workflow_guard.py <original.json> <candidate.json> \
  --allow /6/inputs/text \
  --allow /12/inputs/image \
  --allow /20/inputs/width \
  --allow /20/inputs/height \
  --allow /20/inputs/num_frames
```

`--allow` accepts an exact JSON Pointer and may be repeated. The command succeeds only when every changed leaf path is declared. Do not allow an entire node or `inputs` object; list the exact leaf fields.

Compare like with like: API-format source to API-format candidate, or UI-format source to UI-format candidate. Conversion itself changes structure and must not be mistaken for a generation-input edit.

If the tool path cannot expose a stable original and candidate for comparison, stop before queuing and tell the user that the workflow mutation boundary could not be verified.
