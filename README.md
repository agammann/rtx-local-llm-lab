# RTX Local LLM Lab

A small, reproducible measurement of local language-model inference on a laptop NVIDIA GPU. The Python script queries a locally running Ollama server, separates a cold run from warm runs, calculates generation throughput from Ollama's token counters, and records the runtime's reported VRAM allocation. It uses only the Python standard library.

## Run locally

Start Ollama with NVIDIA GPU access, using a volume for downloaded model weights. This example binds the API to the local machine:

```powershell
docker run -d --gpus all --name alexander-rtx-ollama -p 127.0.0.1:11435:11434 -v alexander-rtx-ollama-models:/root/.ollama ollama/ollama
docker exec alexander-rtx-ollama ollama pull qwen3:1.7b
python bench.py --model qwen3:1.7b --output results/qwen3-1.7b.json
docker exec alexander-rtx-ollama ollama pull qwen3:4b-instruct
python bench.py --model qwen3:4b-instruct --output results/qwen3-4b-instruct.json
docker exec alexander-rtx-ollama ollama ps
```

To compare another model, pull it and pass its tag to `bench.py`. The script checks that the requested model is installed before making a generation request.

## Measurement method

- One fixed, public hardware-support prompt is used for all runs.
- The first request includes model loading and is labeled `cold`.
- Three subsequent requests are labeled `warm`; their mean generation tokens per second is reported.
- Generation throughput is `eval_count / (eval_duration / 1e9)` using Ollama's nanosecond timing fields. It excludes model loading and prompt processing.
- `/api/tags` supplies the installed model digest and quantization details. `/api/ps` supplies the loaded model's VRAM allocation. A nonzero VRAM value is evidence of GPU placement, but it is not a measure of end-to-end application speed.
- Results reflect one machine, driver, model build, prompt, and short run; they should not be treated as general model rankings.
- Qwen3's `/no_think` prompt switch and Ollama's `think: false` request setting are used to measure short direct responses.

The model weights are downloaded separately and are not included in this repository. Qwen3 model details and license are available on the [Ollama model page](https://ollama.com/library/qwen3:1.7b). Runtime request and timing fields are documented in the [Ollama Generate API](https://docs.ollama.com/api/generate).

## Results on this laptop

Measured September 26, 2026 UTC on an NVIDIA GeForce RTX 3050 6GB Laptop GPU (driver 581.86) with Ollama 0.34.4. Ollama's `ps` command reported **100% GPU** for both loaded models.

| Model tag | Warm mean generation | Loaded VRAM reported by Ollama |
| --- | ---: | ---: |
| [`qwen3:1.7b`](results/qwen3-1.7b.json) | 74.16 tokens/s | 1.70 GB |
| [`qwen3:4b-instruct`](results/qwen3-4b-instruct.json) | 40.03 tokens/s | 3.18 GB |

Each result is the mean of three warm requests after one cold request. The two tags use different checkpoints, so this is a local resource and latency comparison rather than a model-quality ranking. The linked JSON records include the exact model digests, quantization details, individual timings, generated responses, and Ollama's VRAM figures.

