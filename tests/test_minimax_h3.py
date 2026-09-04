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
from urllib.parse import parse_qs, urlparse


SCRIPT = (
    Path(__file__).parents[1]
    / "skills"
    / "minimax-h3-api"
    / "scripts"
    / "minimax_h3.py"
)
SPEC = importlib.util.spec_from_file_location("minimax_h3", SCRIPT)
minimax_h3 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(minimax_h3)


class RequestTests(unittest.TestCase):
    def test_saved_minimax_key_is_used(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "providers.json"
            config.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "providers": {
                            "minimax": {"type": "minimax-h3", "api_key": "saved-secret"}
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
                client = minimax_h3._client(SimpleNamespace(base_url=None, region=None))

        self.assertEqual(client.api_key, "saved-secret")

    def test_default_region_uses_official_cn_endpoint(self):
        args = SimpleNamespace(base_url=None, region=None)

        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(minimax_h3._base_url(args), "https://api.minimaxi.com")

    def test_global_region_uses_official_global_endpoint(self):
        args = SimpleNamespace(base_url=None, region="global")

        self.assertEqual(minimax_h3._base_url(args), "https://api.minimax.io")

    def test_text_request_uses_explicit_768p_five_seconds_and_16_by_9(self):
        request = minimax_h3.build_video_request(prompt="Ocean waves", resolution="768P")

        self.assertEqual(request["model"], "MiniMax-H3")
        self.assertEqual(request["resolution"], "768P")
        self.assertEqual(request["duration"], 5)
        self.assertEqual(request["ratio"], "16:9")
        self.assertEqual(request["content"], [{"type": "text", "text": "Ocean waves"}])

    def test_resolution_is_required(self):
        with self.assertRaisesRegex(ValueError, "explicitly set"):
            minimax_h3.build_video_request(prompt="Ocean waves")

    def test_2k_resolution_is_supported(self):
        request = minimax_h3.build_video_request(prompt="Ocean waves", resolution="2K")

        self.assertEqual(request["resolution"], "2K")

    def test_frame_request_forces_adaptive_ratio(self):
        request = minimax_h3.build_video_request(
            prompt="Walk forward",
            resolution="768P",
            first_frame="https://example.com/start.png",
            ratio="9:16",
        )

        self.assertEqual(request["ratio"], "adaptive")
        self.assertEqual(request["content"][1]["role"], "first_frame")

    def test_frame_and_reference_modes_cannot_be_mixed(self):
        with self.assertRaisesRegex(ValueError, "cannot be mixed"):
            minimax_h3.build_video_request(
                prompt="Keep the product",
                resolution="768P",
                first_frame="https://example.com/start.png",
                reference_images=["https://example.com/reference.png"],
            )

    def test_reference_audio_requires_image_or_video(self):
        with self.assertRaisesRegex(ValueError, "requires at least one"):
            minimax_h3.build_video_request(
                prompt="Follow the beat",
                resolution="768P",
                reference_audios=["https://example.com/music.mp3"],
            )

    def test_reference_inputs_have_a_combined_limit_of_twelve(self):
        with self.assertRaisesRegex(ValueError, "12 total"):
            minimax_h3.build_video_request(
                prompt="Use every reference",
                resolution="768P",
                reference_images=[f"https://example.com/{index}.png" for index in range(9)],
                reference_videos=[f"https://example.com/{index}.mp4" for index in range(3)],
                reference_audios=["https://example.com/audio.mp3"],
            )

    def test_local_image_is_encoded_as_a_data_uri(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "product.png"
            image.write_bytes(b"png-test-data")

            request = minimax_h3.build_video_request(
                prompt="Show the product",
                resolution="768P",
                first_frame=str(image),
            )

        self.assertTrue(request["content"][1]["image_url"]["url"].startswith("data:image/png;base64,"))

    def test_cli_requires_resolution_for_paid_request_commands(self):
        parser = minimax_h3.build_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(["submit", "--prompt", "Ocean waves"])

    def test_paid_request_summary_exposes_billable_fields(self):
        request = minimax_h3.build_video_request(
            prompt="Show the product",
            resolution="768P",
            duration=11,
            first_frame="https://example.com/start.png",
        )

        self.assertEqual(
            minimax_h3.paid_request_summary(request),
            {
                "model": "MiniMax-H3",
                "resolution": "768P",
                "duration_seconds": 11,
                "ratio": "adaptive",
                "mode": "first-frame",
            },
        )

    def test_last_frame_request_is_reported_as_last_frame(self):
        request = minimax_h3.build_video_request(
            prompt="End on the product",
            resolution="768P",
            last_frame="https://example.com/end.png",
        )

        self.assertEqual(minimax_h3.paid_request_summary(request)["mode"], "last-frame")

    def test_cost_quote_shows_both_resolutions(self):
        quote = minimax_h3.cost_quote(duration=10, reference_image_count=1)

        self.assertEqual(quote["estimated_cost"], {"768P": "5.00", "2K": "8.00"})

    def test_quote_command_does_not_require_an_api_key(self):
        output = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), redirect_stdout(output):
            exit_code = minimax_h3.main(["quote", "--duration", "10"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(output.getvalue())["estimated_cost"]["2K"], "8.00")

    def test_cost_quote_includes_paid_images_and_reference_video(self):
        quote = minimax_h3.cost_quote(
            duration=10,
            reference_image_count=7,
            reference_video_seconds="2.5",
        )

        self.assertEqual(quote["estimated_cost"], {"768P": "6.65", "2K": "10.40"})


class _ApiHandler(BaseHTTPRequestHandler):
    create_count = 0
    query_count = 0
    balance_query_count = 0
    request_body = None
    video_bytes = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"
    fail_task = False
    result_resolution = "768P"
    result_duration = 11
    list_query = None

    def do_POST(self):
        if self.path != "/v2/video_generation":
            self.send_error(404)
            return
        type(self).create_count += 1
        length = int(self.headers["Content-Length"])
        type(self).request_body = json.loads(self.rfile.read(length))
        self._json({"task_id": "task-123"})

    def do_GET(self):
        if self.path == "/account/query_balance":
            type(self).balance_query_count += 1
            self._json(
                {
                    "available_amount": "98.00",
                    "cash_balance": "20.00",
                    "voucher_balance": "78.00",
                    "credit_balance": "0.00",
                    "owed_amount": "0.00",
                }
            )
            return
        if self.path.startswith("/v2/query/video_generation?"):
            type(self).list_query = parse_qs(urlparse(self.path).query)
            self._json({"items": [], "total": 0})
            return
        if self.path == "/v2/query/video_generation/task-123":
            type(self).query_count += 1
            if type(self).fail_task:
                self._json(
                    {
                        "task": {
                            "id": "task-123",
                            "status": "failed",
                            "error": {"code": "1026", "message": "rejected"},
                        }
                    }
                )
                return
            status = "running" if type(self).query_count == 1 else "succeeded"
            task = {"id": "task-123", "status": status}
            if status == "succeeded":
                task["content"] = {"url": f"{self.server.base_url}/result.mp4"}
                task["resolution"] = type(self).result_resolution
                task["duration"] = type(self).result_duration
            self._json({"task": task})
            return
        if self.path == "/result.mp4":
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
        _ApiHandler.balance_query_count = 0
        _ApiHandler.request_body = None
        _ApiHandler.video_bytes = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"
        _ApiHandler.fail_task = False
        _ApiHandler.result_resolution = "768P"
        _ApiHandler.result_duration = 11
        _ApiHandler.list_query = None
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _ApiHandler)
        self.server.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_generate_submits_once_waits_and_downloads(self):
        client = minimax_h3.MiniMaxClient(self.server.base_url, "secret-for-test")
        request = minimax_h3.build_video_request(
            prompt="Show the product",
            resolution="768P",
            duration=11,
        )

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.mp4"
            result = minimax_h3.generate_video(
                client,
                request,
                output,
                poll_interval=0,
                timeout=5,
            )

            self.assertEqual(output.read_bytes(), _ApiHandler.video_bytes)

        self.assertEqual(_ApiHandler.create_count, 1)
        self.assertEqual(result["task_id"], "task-123")
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(_ApiHandler.request_body["model"], "MiniMax-H3")
        self.assertEqual(_ApiHandler.request_body["resolution"], "768P")
        self.assertEqual(_ApiHandler.request_body["duration"], 11)

    def test_balance_query_is_read_only(self):
        client = minimax_h3.MiniMaxClient(self.server.base_url, "secret-for-test")

        balance = client.get_balance()

        self.assertEqual(balance["available_amount"], "98.00")
        self.assertEqual(_ApiHandler.balance_query_count, 1)
        self.assertEqual(_ApiHandler.create_count, 0)

    def test_failed_task_is_not_resubmitted(self):
        _ApiHandler.fail_task = True
        client = minimax_h3.MiniMaxClient(self.server.base_url, "secret-for-test")
        request = minimax_h3.build_video_request(
            prompt="Show the product",
            resolution="768P",
            duration=11,
        )

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(minimax_h3.ApiError, "1026"):
                minimax_h3.generate_video(
                    client,
                    request,
                    Path(directory) / "result.mp4",
                    poll_interval=0,
                    timeout=5,
                )

        self.assertEqual(_ApiHandler.create_count, 1)

    def test_contract_mismatch_is_not_downloaded_or_resubmitted(self):
        _ApiHandler.result_resolution = "2K"
        client = minimax_h3.MiniMaxClient(self.server.base_url, "secret-for-test")
        request = minimax_h3.build_video_request(
            prompt="Show the product",
            resolution="768P",
            duration=11,
        )

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.mp4"
            with self.assertRaisesRegex(minimax_h3.ApiError, "resolution mismatch"):
                minimax_h3.generate_video(
                    client,
                    request,
                    output,
                    poll_interval=0,
                    timeout=5,
                )
            self.assertFalse(output.exists())

        self.assertEqual(_ApiHandler.create_count, 1)

    def test_missing_contract_fields_are_not_treated_as_verified(self):
        task = {"id": "task-123", "status": "succeeded"}
        request = minimax_h3.build_video_request(
            prompt="Show the product",
            resolution="768P",
            duration=11,
        )

        with self.assertRaisesRegex(minimax_h3.ApiError, "cannot verify"):
            minimax_h3.verify_task_contract(task, request, "task-123")

    def test_wait_download_requires_expected_contract(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {"MINIMAX_API_KEY": "secret-for-test"},
        ):
            output = Path(directory) / "result.mp4"
            exit_code = minimax_h3.main(
                [
                    "--base-url",
                    self.server.base_url,
                    "wait",
                    "task-123",
                    "--output",
                    str(output),
                ]
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(_ApiHandler.query_count, 0)
            self.assertFalse(output.exists())

    def test_download_rejects_non_mp4_body(self):
        _ApiHandler.video_bytes = b"<html>expired</html>"
        client = minimax_h3.MiniMaxClient(self.server.base_url, "secret-for-test")
        request = minimax_h3.build_video_request(
            prompt="Show the product",
            resolution="768P",
            duration=11,
        )

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.mp4"
            with self.assertRaisesRegex(minimax_h3.ApiError, "not an MP4"):
                minimax_h3.generate_video(
                    client,
                    request,
                    output,
                    poll_interval=0,
                    timeout=5,
                )
            self.assertFalse(output.exists())

    def test_list_supports_official_filters(self):
        client = minimax_h3.MiniMaxClient(self.server.base_url, "secret-for-test")

        result = client.list_tasks(
            page_num=2,
            page_size=10,
            status="succeeded",
            task_ids=["task-1", "task-2"],
            model="MiniMax-H3",
            task_type="generation",
        )

        self.assertEqual(result, {"items": [], "total": 0})
        self.assertEqual(
            _ApiHandler.list_query,
            {
                "page_num": ["2"],
                "page_size": ["10"],
                "filter.status": ["succeeded"],
                "filter.task_ids": ["task-1", "task-2"],
                "filter.model": ["MiniMax-H3"],
                "filter.task_type": ["generation"],
            },
        )


if __name__ == "__main__":
    unittest.main()
