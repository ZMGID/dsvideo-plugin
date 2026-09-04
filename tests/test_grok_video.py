import importlib.util
import io
import json
import os
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "skills" / "grok-video-api" / "scripts" / "grok_video.py"
SPEC = importlib.util.spec_from_file_location("grok_video", SCRIPT)
grok_video = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(grok_video)


class RequestTests(unittest.TestCase):
    def test_saved_provider_supplies_url_key_and_selected_model(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "providers.json"
            config.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "providers": {
                            "grok": {
                                "type": "openai-video",
                                "base_url": "https://gateway.example",
                                "api_key": "saved-secret",
                                "model": "grok-imagine-video-1.5",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"DSVIDEO_CONFIG_PATH": str(config)},
                clear=True,
            ):
                settings = grok_video._settings(
                    SimpleNamespace(provider=None, base_url=None, model=None)
                )

        self.assertEqual(
            settings,
            ("https://gateway.example", "saved-secret", "grok-imagine-video-1.5"),
        )

    def test_text_request_uses_official_model_and_explicit_resolution(self):
        request = grok_video.build_video_request(prompt="Ocean waves", resolution="720p")
        self.assertEqual(request["model"], "grok-imagine-video-1.5")
        self.assertEqual(request["resolution"], "720p")
        self.assertEqual(request["duration"], 5)
        self.assertEqual(request["aspect_ratio"], "16:9")
        self.assertTrue(request["generate_audio"])

    def test_resolution_is_required(self):
        with self.assertRaisesRegex(ValueError, "explicitly selected"):
            grok_video.build_video_request(prompt="Ocean waves")

    def test_duration_range_is_enforced(self):
        with self.assertRaisesRegex(ValueError, "1 to 15"):
            grok_video.build_video_request(prompt="Ocean waves", resolution="480p", duration=16)

    def test_local_image_becomes_data_uri(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "product.png"
            image.write_bytes(b"image-data")
            request = grok_video.build_video_request(
                prompt="Show the product", resolution="1080p", image=str(image)
            )
        self.assertTrue(request["image"]["url"].startswith("data:image/png;base64,"))

    def test_quote_includes_image_input(self):
        result = grok_video.cost_quote(duration=10, image_count=1)
        self.assertEqual(
            result["estimated_cost"],
            {"480p": "0.81", "720p": "1.41", "1080p": "2.51"},
        )

    def test_quote_command_needs_no_api_key(self):
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), redirect_stdout(output):
            code = grok_video.main(["quote", "--duration", "10"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["estimated_cost"]["1080p"], "2.50")


class _ApiHandler(BaseHTTPRequestHandler):
    create_count = 0
    query_count = 0
    request_body = None
    fail = False
    video_bytes = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"

    def do_POST(self):
        if self.path != "/v1/videos/generations":
            self.send_error(404)
            return
        type(self).create_count += 1
        length = int(self.headers["Content-Length"])
        type(self).request_body = json.loads(self.rfile.read(length))
        self._json({"request_id": "request-123"})

    def do_GET(self):
        if self.path == "/v1/videos/request-123":
            type(self).query_count += 1
            if type(self).fail:
                self._json({"status": "failed", "error": {"message": "rejected"}})
                return
            status = "pending" if type(self).query_count == 1 else "done"
            result = {"status": status}
            if status == "done":
                result.update(
                    {
                        "model": "grok-imagine-video-1.5",
                        "video": {"url": "/result.mp4", "duration": 10},
                    }
                )
            self._json(result)
            return
        if self.path == "/result.mp4":
            if self.headers.get("Authorization") != "Bearer test-secret":
                self.send_error(401)
                return
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(len(type(self).video_bytes)))
            self.end_headers()
            self.wfile.write(type(self).video_bytes)
            return
        self.send_error(404)

    def _json(self, value):
        body = json.dumps(value).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


class ClientTests(unittest.TestCase):
    def setUp(self):
        _ApiHandler.create_count = 0
        _ApiHandler.query_count = 0
        _ApiHandler.request_body = None
        _ApiHandler.fail = False
        _ApiHandler.video_bytes = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _ApiHandler)
        self.server.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_generate_submits_once_waits_and_downloads(self):
        client = grok_video.GrokVideoClient(self.server.base_url, "test-secret")
        request = grok_video.build_video_request(
            prompt="Show the product", resolution="720p", duration=10
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.mp4"
            result = grok_video.generate_video(
                client, request, output, poll_interval=0, timeout=5
            )
            self.assertEqual(output.read_bytes(), _ApiHandler.video_bytes)
        self.assertEqual(_ApiHandler.create_count, 1)
        self.assertEqual(result["request_id"], "request-123")
        self.assertEqual(_ApiHandler.request_body["model"], "grok-imagine-video-1.5")

    def test_failed_request_is_not_resubmitted(self):
        _ApiHandler.fail = True
        client = grok_video.GrokVideoClient(self.server.base_url, "test-secret")
        request = grok_video.build_video_request(
            prompt="Show the product", resolution="480p", duration=10
        )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(grok_video.ApiError, "rejected"):
                grok_video.generate_video(
                    client, request, Path(directory) / "result.mp4", poll_interval=0, timeout=5
                )
        self.assertEqual(_ApiHandler.create_count, 1)

    def test_download_rejects_non_mp4(self):
        _ApiHandler.video_bytes = b"<html>expired</html>"
        client = grok_video.GrokVideoClient(self.server.base_url, "test-secret")
        request = grok_video.build_video_request(
            prompt="Show the product", resolution="480p", duration=10
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.mp4"
            with self.assertRaisesRegex(grok_video.ApiError, "not an MP4"):
                grok_video.generate_video(
                    client, request, output, poll_interval=0, timeout=5
                )
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
