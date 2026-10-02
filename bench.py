"""Measure local Ollama inference and record GPU placement evidence."""

import argparse
import json
import platform
import statistics
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


PROMPT = (
    "In exactly three numbered lines, explain these non-invasive checks for a "
    "monitor with no image: power indicator, cable seating, and selected input "
    "source. Do not add other checks. /no_think"
)


def api_json(base_url, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.load(response)
    if not isinstance(result, dict):
        raise RuntimeError(f"{path} did not return a JSON object")
    return result


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
    parser.add_argument("--model", default="qwen3:1.7b")
    parser.add_argument("--url", default="http://127.0.0.1:11435")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be at least 1")

    try:
        version = api_json(args.url, "/api/version").get("version")
        tags = api_json(args.url, "/api/tags").get("models", [])
        installed = next((item for item in tags if item.get("name") == args.model), None)
        if installed is None:
            parser.error(f"model {args.model!r} is not installed; pull it first")

        running_before = api_json(args.url, "/api/ps").get("models", [])
        initial_model_loaded = any(
            item.get("name") == args.model
            or (installed.get("digest") and item.get("digest") == installed["digest"])
            for item in running_before
        )
        responses = []
        # A previously loaded model has a warm-up request, not a cold load.
        for index in range(args.runs + 1):
            result = api_json(args.url, "/api/generate", {
                "model": args.model,
                "prompt": PROMPT,
                "stream": False,
                "think": False,
                "keep_alive": "10m",
                "options": {"temperature": 0, "num_predict": 120},
            })
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

        running = api_json(args.url, "/api/ps").get("models", [])
        loaded = next((item for item in running if item.get("name") == args.model), None)
        if loaded is None:
            raise RuntimeError("model is not listed by /api/ps after inference")
        if type(loaded.get("size_vram")) is not int or loaded["size_vram"] < 0:
            raise RuntimeError("/api/ps did not report a valid VRAM allocation")
        warm = [item["generation_tokens_per_second"] for item in responses[1:]]
        record = {
            "measured_at_utc": datetime.now(timezone.utc).isoformat(),
            "host_os": platform.system(),
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
            "warm_generation_tokens_per_second_mean": round(statistics.mean(warm), 2),
            "runs": responses,
        }
        output = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(output, encoding="utf-8")
            print(f"Saved {args.output}")
        else:
            print(output)
        print(
            f"{args.model}: warm mean {record['warm_generation_tokens_per_second_mean']} token/s; "
            f"Ollama reports {record['loaded_model_vram_bytes']:,} bytes in VRAM"
        )
    except (OSError, RuntimeError, KeyError, ValueError) as exc:
        print(f"Benchmark failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

