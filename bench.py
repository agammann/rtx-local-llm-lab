"""Measure local Ollama inference and record GPU placement evidence."""

import argparse
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


PROMPT = (
    "In exactly three numbered lines, explain these non-invasive checks for a "
    "monitor with no image: power indicator, cable seating, and selected input "
    "source. Do not add other checks. /no_think"
)
VERSION = "1.0.0"


def api_json(base_url, path, payload=None, timeout=180):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        result = json.load(response)
    if not isinstance(result, dict):
        raise RuntimeError(f"{path} did not return a JSON object")
    if result.get("error"):
        raise RuntimeError(f"{path}: {result['error']}")
    return result


def models(response, endpoint):
    items = response.get("models")
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise RuntimeError(f"{endpoint} did not return a model list")
    return items


def save_record(output, content, overwrite=False):
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix="." + output.name + ".", suffix=".tmp", dir=output.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        if overwrite:
            os.replace(temporary, output)
        else:
            # A hard link exposes the completed file and refuses a collision.
            # This also preserves an earlier result if another process wins.
            os.link(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)


def gpu_info():
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def tokens_per_second(response):
    duration = response.get("eval_duration")
    count = response.get("eval_count")
    if type(duration) is not int or duration <= 0 or type(count) is not int or count <= 0:
        raise RuntimeError("generation returned missing or invalid token timing counters")
    return round(count * 1_000_000_000 / duration, 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version="RTX Local LLM Lab " + VERSION)
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument("--url", default="http://127.0.0.1:11434")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--context", type=int, default=4096)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing result only after every measurement succeeds")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be at least 1")
    if args.context < 1 or not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--context and --timeout must be positive")
    try:
        endpoint = urllib.parse.urlsplit(args.url)
        _port = endpoint.port
    except ValueError:
        parser.error("--url is not a valid local Ollama URL")
    if endpoint.scheme != "http" or endpoint.hostname not in {"localhost", "127.0.0.1", "::1"} or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment or endpoint.path not in {"", "/"}:
        parser.error("--url must be a loopback HTTP Ollama URL without credentials, a path or query")
    if args.output and args.output.exists() and not args.overwrite:
        parser.error("output already exists; choose a new filename or use --overwrite")

    try:
        request = lambda path, payload=None: api_json(args.url, path, payload, timeout=args.timeout)
        version = request("/api/version").get("version")
        if not isinstance(version, str) or not version.strip():
            raise RuntimeError("/api/version did not report a runtime version")
        tags = models(request("/api/tags"), "/api/tags")
        installed = next((item for item in tags if item.get("name") == args.model), None)
        if installed is None:
            parser.error(f"model {args.model!r} is not installed; pull it first")
        if installed.get("remote_host") or installed.get("remote_model"):
            raise RuntimeError("the selected model is remote; choose locally installed weights")

        running_before = models(request("/api/ps"), "/api/ps")
        initial_model_loaded = any(
            item.get("name") == args.model
            or (installed.get("digest") and item.get("digest") == installed["digest"])
            for item in running_before
        )
        responses = []
        # A previously loaded model has a warm-up request, not a cold load.
        for index in range(args.runs + 1):
            result = request("/api/generate", {
                "model": args.model,
                "prompt": PROMPT,
                "stream": False,
                "think": False,
                "keep_alive": "10m",
                "options": {"temperature": 0, "num_predict": 120, "num_ctx": args.context},
            })
            if result.get("remote_host") or result.get("remote_model"):
                raise RuntimeError("runtime returned a remote response; no local measurement was saved")
            if result.get("done") is not True:
                raise RuntimeError("generation did not complete")
            for field in ("total_duration", "load_duration"):
                if type(result.get(field)) is not int or result[field] < 0:
                    raise RuntimeError(f"generation returned missing or invalid {field}")
            if not isinstance(result.get("response"), str):
                raise RuntimeError("generation did not return response text")
            responses.append({
                "phase": ("warmup" if initial_model_loaded else "cold") if index == 0 else "warm",
                "total_ms": round(result["total_duration"] / 1_000_000, 2),
                "load_ms": round(result["load_duration"] / 1_000_000, 2),
                "prompt_tokens": result.get("prompt_eval_count"),
                "output_tokens": result.get("eval_count"),
                "generation_tokens_per_second": tokens_per_second(result),
                "done_reason": result.get("done_reason"),
                "response": result.get("response", "").strip(),
            })

        running = models(request("/api/ps"), "/api/ps")
        loaded = next((item for item in running if item.get("name") == args.model or (installed.get("digest") and item.get("digest") == installed["digest"])), None)
        if loaded is None:
            raise RuntimeError("model is not listed by /api/ps after inference")
        if type(loaded.get("size_vram")) is not int or loaded["size_vram"] < 0:
            raise RuntimeError("/api/ps did not report a valid VRAM allocation")
        warm = [item["generation_tokens_per_second"] for item in responses[1:]]
        record = {
            "format": "rtx-local-llm-lab",
            "version": 1,
            "measured_at_utc": datetime.now(timezone.utc).isoformat(),
            "host_os": platform.system(),
            "python_version": platform.python_version(),
            "gpu": gpu_info(),
            "ollama_version": version,
            "model": args.model,
            "model_digest": installed.get("digest"),
            "model_size_bytes": installed.get("size"),
            "model_details": installed.get("details"),
            "initial_model_loaded": initial_model_loaded,
            "loaded_model_size_bytes": loaded.get("size"),
            "loaded_model_vram_bytes": loaded.get("size_vram"),
            "prompt": PROMPT,
            "request_settings": {"temperature": 0, "num_predict": 120, "num_ctx": args.context, "think": False, "keep_alive": "10m"},
            "loaded_context_length": loaded.get("context_length"),
            "warm_generation_tokens_per_second_mean": round(statistics.mean(warm), 2),
            "runs": responses,
        }
        output = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            save_record(args.output, output, overwrite=args.overwrite)
            print(f"Saved {args.output}")
        else:
            print(output)
        print(
            f"{args.model}: warm mean {record['warm_generation_tokens_per_second_mean']} token/s; "
            f"Ollama reports {record['loaded_model_vram_bytes']:,} bytes in VRAM"
        )
    except KeyboardInterrupt:
        print("Benchmark stopped. No incomplete result was saved.", file=sys.stderr)
        return 130
    except (OSError, RuntimeError, KeyError, ValueError) as exc:
        print(f"Benchmark failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

