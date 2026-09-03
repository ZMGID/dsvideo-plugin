import importlib.util
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "skills"
    / "ecom-h3-video"
    / "scripts"
    / "comfy_workflow_guard.py"
)
SPEC = importlib.util.spec_from_file_location("comfy_workflow_guard", SCRIPT)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


ORIGINAL = {
    "1": {
        "class_type": "LoadModel",
        "inputs": {"model_name": "MiniMax-H3.safetensors"},
    },
    "2": {
        "class_type": "VideoSampler",
        "inputs": {
            "video_steps": 10,
            "cfg": 6.0,
            "sampler_name": "euler",
            "scheduler": "normal",
        },
    },
    "3": {
        "class_type": "VideoInput",
        "inputs": {
            "prompt": "old prompt",
            "image": "old.png",
            "width": 1280,
            "height": 720,
            "num_frames": 121,
            "fps": 24,
        },
    },
}


class WorkflowGuardTests(unittest.TestCase):
    def test_allows_only_declared_generation_inputs(self):
        candidate = deepcopy(ORIGINAL)
        candidate["3"]["inputs"].update(
            {
                "prompt": "new prompt",
                "image": "product.png",
                "width": 720,
                "height": 1280,
                "num_frames": 241,
            }
        )

        changed = guard.assert_only_allowed_changes(
            ORIGINAL,
            candidate,
            {
                "/3/inputs/prompt",
                "/3/inputs/image",
                "/3/inputs/width",
                "/3/inputs/height",
                "/3/inputs/num_frames",
            },
        )

        self.assertEqual(
            changed,
            [
                "/3/inputs/height",
                "/3/inputs/image",
                "/3/inputs/num_frames",
                "/3/inputs/prompt",
                "/3/inputs/width",
            ],
        )
        self.assertEqual(ORIGINAL["2"]["inputs"]["video_steps"], 10)

    def test_rejects_video_steps_change(self):
        candidate = deepcopy(ORIGINAL)
        candidate["2"]["inputs"]["video_steps"] = 4

        with self.assertRaisesRegex(
            guard.WorkflowMutationError,
            "/2/inputs/video_steps",
        ):
            guard.assert_only_allowed_changes(ORIGINAL, candidate, set())

    def test_rejects_model_change(self):
        candidate = deepcopy(ORIGINAL)
        candidate["1"]["inputs"]["model_name"] = "another-model.safetensors"

        with self.assertRaisesRegex(
            guard.WorkflowMutationError,
            "/1/inputs/model_name",
        ):
            guard.assert_only_allowed_changes(ORIGINAL, candidate, set())

    def test_rejects_topology_change(self):
        candidate = deepcopy(ORIGINAL)
        candidate["4"] = {"class_type": "Upscaler", "inputs": {}}

        with self.assertRaisesRegex(guard.WorkflowMutationError, "/4"):
            guard.assert_only_allowed_changes(ORIGINAL, candidate, set())

    def test_cli_reads_original_without_overwriting_it(self):
        candidate = deepcopy(ORIGINAL)
        candidate["3"]["inputs"]["prompt"] = "new prompt"

        with tempfile.TemporaryDirectory() as directory:
            original_path = Path(directory) / "original.json"
            candidate_path = Path(directory) / "candidate.json"
            original_path.write_text(json.dumps(ORIGINAL), encoding="utf-8")
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            original_bytes = original_path.read_bytes()

            with redirect_stdout(StringIO()):
                exit_code = guard.main(
                    [
                        str(original_path),
                        str(candidate_path),
                        "--allow",
                        "/3/inputs/prompt",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(original_path.read_bytes(), original_bytes)


if __name__ == "__main__":
    unittest.main()
