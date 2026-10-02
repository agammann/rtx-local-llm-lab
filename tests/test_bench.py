"""Exercise the CLI against a local HTTP fixture; no model or GPU is required."""
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "bench.py"


class BenchmarkTests(unittest.TestCase):
    def run_benchmark(self, resident=False, invalid=None):
        calls = []
        model = {"name": "fixture:latest", "digest": "fixture-digest", "size": 123, "size_vram": 0}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                calls.append(self.path)
                if self.path == "/api/version":
                    body = {"version": "fixture"}
                elif self.path == "/api/tags":
                    body = {"models": [model]}
                else:
                    body = {"models": [model] if resident or "/api/generate" in calls else []}
                self.reply(body)

            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                calls.append(self.path)
                assert request["stream"] is False
                body = {"done": True, "done_reason": "stop", "response": "fixture response",
                        "total_duration": 2_000_000_000, "load_duration": 1_000_000,
                        "eval_duration": 1_000_000_000, "eval_count": 10}
                if invalid:
                    body.update(invalid)
                self.reply(body)

            def reply(self, body):
                raw = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server, tempfile.TemporaryDirectory() as tmp:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                output = Path(tmp) / "result.json"
                result = subprocess.run([sys.executable, str(SCRIPT), "--url",
                    f"http://127.0.0.1:{server.server_port}", "--model", model["name"],
                    "--runs", "2", "--output", str(output)], capture_output=True, text=True, timeout=30)
                record = json.loads(output.read_text()) if output.exists() else None
                return result, record, calls
            finally:
                server.shutdown()
                worker.join()

    def test_resident_model_is_warmup_not_cold(self):
        result, record, calls = self.run_benchmark(resident=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([run["phase"] for run in record["runs"]], ["warmup", "warm", "warm"])
        self.assertTrue(record["initial_model_loaded"])
        self.assertEqual(record["warm_generation_tokens_per_second_mean"], 10)
        self.assertEqual(calls.count("/api/generate"), 3)

    def test_unloaded_model_is_cold_and_cpu_allocation_is_valid(self):
        result, record, _calls = self.run_benchmark()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(record["initial_model_loaded"])
        self.assertEqual(record["runs"][0]["phase"], "cold")
        self.assertEqual(record["loaded_model_vram_bytes"], 0)

    def test_invalid_measurements_fail_without_writing_results(self):
        for invalid in ({"eval_duration": 0}, {"eval_count": None}, {"load_duration": -1}):
            with self.subTest(invalid=invalid):
                result, record, _calls = self.run_benchmark(invalid=invalid)
                self.assertEqual(result.returncode, 1)
                self.assertIn("Benchmark failed:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertIsNone(record)


if __name__ == "__main__":
    unittest.main()
