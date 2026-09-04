import importlib.util
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "dsvideo_config.py"
SPEC = importlib.util.spec_from_file_location("dsvideo_config_test", SCRIPT)
dsvideo_config = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dsvideo_config)


class _ModelsHandler(BaseHTTPRequestHandler):
    authorization = None

    def do_GET(self):
        if self.path != "/v1/models":
            self.send_error(404)
            return
        type(self).authorization = self.headers.get("Authorization")
        body = json.dumps(
            {
                "data": [
                    {"id": "chat-model"},
                    {"id": "grok-imagine-video-1.5"},
                    {"id": "seedance-2.5"},
                ]
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


class ConfigTests(unittest.TestCase):
    def test_minimax_provider_contains_only_type_and_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "providers.json"
            dsvideo_config.save_provider(
                "minimax", {"type": "minimax-h3", "api_key": "minimax-secret"}, path
            )
            saved = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            saved["providers"]["minimax"],
            {"type": "minimax-h3", "api_key": "minimax-secret"},
        )

    def test_openai_model_discovery_filters_video_models(self):
        _ModelsHandler.authorization = None
        server = ThreadingHTTPServer(("127.0.0.1", 0), _ModelsHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            models = dsvideo_config.fetch_models(
                f"http://127.0.0.1:{server.server_port}/v1", "provider-secret"
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

        self.assertEqual(models, ["grok-imagine-video-1.5", "seedance-2.5"])
        self.assertEqual(_ModelsHandler.authorization, "Bearer provider-secret")

    def test_config_path_can_be_overridden(self):
        with tempfile.TemporaryDirectory() as directory:
            expected = Path(directory) / "custom.json"
            with patch.dict(os.environ, {"DSVIDEO_CONFIG_PATH": str(expected)}):
                self.assertEqual(dsvideo_config.config_path(), expected)


if __name__ == "__main__":
    unittest.main()
