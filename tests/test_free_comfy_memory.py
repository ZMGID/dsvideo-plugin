import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "skills"
    / "ecom-h3-video"
    / "scripts"
    / "free_comfy_memory.py"
)
SPEC = importlib.util.spec_from_file_location("free_comfy_memory", SCRIPT)
cleaner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cleaner)


class FakeResponse:
    def __init__(self, payload=b""):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class ComfyMemoryTests(unittest.TestCase):
    def test_empty_queue_unloads_models_and_frees_memory(self):
        requests = []

        def opener(request, timeout):
            requests.append((request, timeout))
            if request.full_url.endswith("/queue"):
                return FakeResponse(
                    json.dumps({"queue_running": [], "queue_pending": []}).encode()
                )
            return FakeResponse()

        result = cleaner.free_comfy_memory(
            "http://comfy.example:8188/", opener=opener
        )

        self.assertEqual(result["status"], "freed")
        self.assertEqual([request.get_method() for request, _ in requests], ["GET", "POST"])
        self.assertEqual(requests[1][0].full_url, "http://comfy.example:8188/free")
        self.assertEqual(
            json.loads(requests[1][0].data),
            {"unload_models": True, "free_memory": True},
        )

    def test_consecutive_task_skips_unload(self):
        cases = [([[1]], []), ([], [[2]])]

        for running, pending in cases:
            with self.subTest(running=len(running), pending=len(pending)):
                requests = []

                def opener(request, timeout):
                    requests.append(request)
                    return FakeResponse(
                        json.dumps(
                            {"queue_running": running, "queue_pending": pending}
                        ).encode()
                    )

                result = cleaner.free_comfy_memory(opener=opener)

                self.assertEqual(result["status"], "skipped_consecutive_tasks")
                self.assertEqual(result["running"], len(running))
                self.assertEqual(result["pending"], len(pending))
                self.assertEqual(len(requests), 1)

    def test_invalid_queue_response_is_rejected(self):
        def opener(_request, timeout):
            return FakeResponse(json.dumps({"queue_running": []}).encode())

        with self.assertRaisesRegex(cleaner.ComfyMemoryError, "queue_pending"):
            cleaner.free_comfy_memory(opener=opener)


if __name__ == "__main__":
    unittest.main()
