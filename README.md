# RTX Local LLM Lab

A small, reproducible measurement of local language-model inference on a laptop NVIDIA GPU. The Python script queries a locally running Ollama server, records whether the model was already loaded, calculates warm generation throughput from Ollama's token counters, and records the runtime's reported VRAM allocation. It uses only the Python standard library. This is a command-line measurement tool; its short prompt does not evaluate general model quality.

## Run locally

You need Python 3 and a working [Ollama installation](https://ollama.com/download). No Python packages or API key are required. With the Ollama desktop app running on its default local port:

```powershell
ollama pull qwen3:1.7b
python bench.py --url http://127.0.0.1:11434 --model qwen3:1.7b --output results/my-qwen3-1.7b.json
ollama ps
```

For a server on another port, pass its URL with `--url`. The script defaults to `http://127.0.0.1:11435` for the Docker setup below. Use `--runs 5` to collect five measured warm requests instead of three. Output files are overwritten if they already exist, so choose a new filename when preserving an earlier measurement.

Alternatively, start Docker with NVIDIA GPU access, using a volume for downloaded model weights. This example binds the API to the local machine:

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
- Before generation, `/api/ps` checks whether the requested model or its digest is already loaded. The first request is labeled `warmup` if it is resident, or `cold` otherwise; `initial_model_loaded` records the observed state. A cold label means Ollama did not report it loaded at that check, not that the operating system's file cache was empty. Other clients can change server state during a run.
- Three subsequent requests are labeled `warm`; their mean generation tokens per second is reported. The initial request is always excluded from this mean. Use a dedicated idle server for comparisons. The script does not unload models belonging to another session.
- Generation throughput is `eval_count / (eval_duration / 1e9)` using Ollama's nanosecond timing fields. It excludes model loading and prompt processing.
- `/api/tags` supplies the installed model digest and quantization details. `/api/ps` supplies the loaded model's VRAM allocation. A nonzero VRAM value is evidence of GPU placement, but it is not a measure of end-to-end application speed.
- Results reflect one machine, driver, model build, prompt, and short run; they should not be treated as general model rankings.
- Qwen3's `/no_think` prompt switch and Ollama's `think: false` request setting are used to measure short direct responses.
- `done_reason` records why each response ended; `length` indicates the output limit was reached. Missing or invalid timing counters cause a clear error instead of an incomplete throughput result. A CPU-only model can validly report zero VRAM.

The model weights are downloaded separately and are not included in this repository. Qwen3 model details and license are available on the [Ollama model page](https://ollama.com/library/qwen3:1.7b). Runtime request and timing fields are documented in the [Ollama Generate API](https://docs.ollama.com/api/generate).

## Results on this laptop

Measured again on **October 2, 2026 UTC** with native Windows Ollama **0.35.0**, NVIDIA GeForce RTX 3050 6GB Laptop GPU, driver **616.92**, and a 4096-token context. Both models were initially unloaded; `ollama ps` reported **100% GPU** after the measurements. Browser model inference was held during these runs.

| Model tag | Warm mean generation | Loaded VRAM reported by Ollama |
| --- | ---: | ---: |
| [`qwen3:1.7b`](results/2026-10-02-qwen3-1.7b.json) | 79.26 tokens/s | 1.70 GB |
| [`qwen3:4b-instruct`](results/2026-10-02-qwen3-4b-instruct.json) | 40.38 tokens/s | 3.18 GB |

Each mean uses three warm requests. All responses stopped normally. The 1.7B model added an introductory sentence despite the request for exactly three numbered lines; the 4B model returned three numbered checks. These observations describe this one prompt, not a broad accuracy assessment. The runtime and driver differ from the earlier results, so the tables do not isolate a performance change in either component.

### Earlier measurement

Measured September 26, 2026 UTC on an NVIDIA GeForce RTX 3050 6GB Laptop GPU (driver 581.86) with Ollama 0.34.4. Ollama's `ps` command reported **100% GPU** for both loaded models.

| Model tag | Warm mean generation | Loaded VRAM reported by Ollama |
| --- | ---: | ---: |
| [`qwen3:1.7b`](results/qwen3-1.7b.json) | 74.16 tokens/s | 1.70 GB |
| [`qwen3:4b-instruct`](results/qwen3-4b-instruct.json) | 40.03 tokens/s | 3.18 GB |

Each earlier result is the mean of three warm requests after one initial request. The old script did not inspect prior model residency, so that first request is now labeled `initial` in the historical records; its timings and generated text are unchanged. The two tags use different checkpoints, so this is a local resource and latency comparison rather than a model-quality ranking. The linked JSON records include the exact model digests, quantization details, individual timings, generated responses, and Ollama's VRAM figures.

## Verification and troubleshooting

```powershell
python -m unittest discover -s tests -v
```

The three standard-library tests run the actual CLI against a local HTTP fixture. They check resident versus unloaded labels, CPU allocation, the warm mean, and rejection of invalid counters without writing results. They do not simulate model quality or establish GPU performance.

The October 2 real-server check reproduced an already-loaded model being incorrectly labeled `cold` with a 3.66 ms load time. The corrected script reported `warmup` and `initial_model_loaded: true` on an immediate repeat. The two fresh result files above came from actual GPU inference, separately from the protocol tests.

- **Connection refused:** start Ollama and check that `--url` points to its listening port.
- **Model is not installed:** pull the exact tag into the same server used by `--url`. An `OLLAMA_HOST` setting may make the CLI talk to a different server.
- **No GPU placement:** inspect `ollama ps`, the driver and Ollama's GPU support. The script records the server's VRAM figure even if it is zero; it does not force GPU execution.
- **Invalid counters or incomplete generation:** keep the error and inspect the server logs; no successful benchmark file is produced for that run.

