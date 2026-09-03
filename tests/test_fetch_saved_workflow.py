import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).parents[1]
    / "skills"
    / "ecom-h3-video"
    / "scripts"
    / "fetch_saved_workflow.py"
)
SPEC = importlib.util.spec_from_file_location("fetch_saved_workflow", SCRIPT)
fetcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fetcher)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class WorkflowFetchTests(unittest.TestCase):
    def test_fetches_only_the_exact_server_workflow(self):
        workflow_payload = json.dumps({"nodes": [{"id": 1}]}).encode()
        requested_urls = []

        def opener(request, timeout):
            requested_urls.append((request.full_url, timeout))
            if "?dir=workflows" in request.full_url:
                return FakeResponse(json.dumps([fetcher.WORKFLOW_NAME]).encode())
            return FakeResponse(workflow_payload)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "h3.original.json"
            result = fetcher.fetch_saved_workflow(
                output,
                "http://comfy.example:8188/",
                opener=opener,
            )

            self.assertEqual(output.read_bytes(), workflow_payload)
            self.assertEqual(result["nodes"], 1)
            self.assertEqual(len(requested_urls), 2)
            self.assertIn("/userdata/workflows%2F", requested_urls[1][0])
            self.assertNotIn("/userdata/workflows/", requested_urls[1][0])

    def test_stops_when_the_exact_workflow_is_missing(self):
        def opener(_request, timeout):
            return FakeResponse(json.dumps(["other.json"]).encode())

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "h3.original.json"
            with self.assertRaisesRegex(fetcher.WorkflowFetchError, "未找到指定工作流"):
                fetcher.fetch_saved_workflow(output, opener=opener)
            self.assertFalse(output.exists())

    def test_rejects_a_non_workflow_json(self):
        responses = iter(
            [
                json.dumps([fetcher.WORKFLOW_NAME]).encode(),
                json.dumps({"not_nodes": []}).encode(),
            ]
        )

        def opener(_request, timeout):
            return FakeResponse(next(responses))

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "h3.original.json"
            with self.assertRaisesRegex(fetcher.WorkflowFetchError, "缺少 nodes"):
                fetcher.fetch_saved_workflow(output, opener=opener)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
