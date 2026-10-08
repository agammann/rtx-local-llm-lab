# RTX Local LLM Lab

Measure a local Ollama model's generation rate, first-request loading time and reported VRAM allocation. Keep the exact model digest, runtime settings and generated text beside the timings.

This is a small command-line lab for developers. It uses Python's standard library, runs against a local Ollama server, and needs no API key or paid model service. It measures one fixed monitor-check prompt; it does not establish general model speed or answer quality.

## Get a first result

1. Install **Python 3.10 or newer** and [Ollama](https://ollama.com/download). The real v1 check used native Windows Ollama **0.35.0**. Start Ollama and leave it running.
2. Download `rtx-local-llm-lab_1.0.0_source.zip` and `SHA256SUMS` from the [v1.0.0 release](https://github.com/agammann/rtx-local-llm-lab/releases/tag/v1.0.0), verify the checksum and extract the archive.
3. Open a terminal in the extracted `rtx-local-llm-lab_1.0.0` folder. In PowerShell:

```powershell
python .\bench.py --version
ollama pull qwen3:1.7b
python .\bench.py --model qwen3:1.7b --runs 2 --output outputs\my-first-result.json
ollama ps
```

Models reported as remote or cloud are rejected before generation. The tool uses locally installed weights only.

The default endpoint is `http://127.0.0.1:11434`, Ollama's desktop port. A first result makes **three requests**: one initial request and two measured warm requests. The output names the file saved, its warm mean generation rate and Ollama's VRAM figure. Open the JSON to inspect every response and timing. The source release contains no model weights; `ollama pull` separately downloads the selected model.

If another local server uses a different port, pass it explicitly:

```powershell
python .\bench.py --url http://127.0.0.1:11435 --model qwen3:1.7b --output outputs\another-session.json
```

The tool accepts loopback HTTP endpoints (`127.0.0.1`, `localhost` or `::1`). It records GPU metadata from this computer, so remote servers are outside its scope. Use the exact installed tag from `ollama list`; the tool checks it before generation. It does not download models, force GPU placement, start a server or unload another session's model.

If you started the model solely for this session, unload it when finished:

```powershell
ollama stop qwen3:1.7b
```

## Preserve and understand results

Choose a new filename for each measurement. An existing file is preserved by default, before any model request. `--overwrite` explicitly replaces it only after all required measurements succeed. Invalid counters, unavailable runtimes/models and interruption while collecting measurements produce no successful result. Keep the error rather than treating an incomplete run as a benchmark.

```powershell
python .\bench.py --model qwen3:1.7b --runs 3 --context 4096 --timeout 180 --output outputs\context-4096.json
```

`--runs` counts the warm requests; the default is three. The context request defaults to 4096 tokens. Generation uses temperature 0, an output cap of 120 tokens, `think: false`, the Qwen `/no_think` prompt switch and a ten-minute keep-alive. Both request settings and the runtime's reported loaded context are saved. Different models may interpret these settings differently; inspect their responses and `done_reason`.

| Field | Meaning |
| :--- | :--- |
| `initial_model_loaded` | Whether `/api/ps` reported the model or its digest before the first request |
| `cold` / `warmup` | Initial request with no reported loaded model / an already resident model |
| `warm_generation_tokens_per_second_mean` | Mean of the subsequent per-request generation rates; excludes the initial request |
| `generation_tokens_per_second` | `eval_count / (eval_duration / 1e9)`, rounded to two decimals |
| `loaded_model_vram_bytes` | Ollama's reported allocation, not total GPU capacity; zero is valid CPU placement |
| `loaded_context_length` | Context reported by the runtime after generation, separate from the requested setting |
| `done_reason` | How each response ended; `length` exposes an output-cap stop |
| `model_digest` | Exact installed model build used in that session |

These rates exclude loading and prompt processing. A `cold` label means the runtime did not report a resident model; it does not mean the operating system's file cache was empty. Other clients and background activity can change state and timing. Use a dedicated idle session for comparisons, retain all responses, and do not select a nicer answer from retries.

Results are ordinary JSON files. Back them up with their source release before changing machines or deleting a folder. There is no account, database or model-cache backup in this tool. Upgrades leave earlier result files untouched. See [Stability](STABILITY.md) for the v1 record and recovery boundaries.

## Observed sessions

**October 8, 2026 UTC v1 check:** Python 3.12 on Windows, native Ollama 0.35.0, NVIDIA GeForce RTX 3050 6GB Laptop GPU, driver 616.92, explicit 4096-token context. The existing Qwen3 1.7B Q4_K_M cache was reused, with no new download. One initial request and two warm requests completed normally. The warm mean was **111.87 tokens/s**, with **1,702,593,821 bytes** reported in VRAM. [Every response and timing](results/2026-10-08-v1-qwen3-1.7b.json) is retained.

The first response named power, cable and selected input but added an introduction, failing the requested exactly-three-line format. It was retained without a quality retry. This short session verifies the measurement path; it does not establish general reasoning quality or isolate why timing differs from earlier sessions.

Earlier records remain unchanged:

| Session | Model | Warm mean | Reported VRAM |
| :--- | :--- | ---: | ---: |
| October 2, 2026 UTC; Ollama 0.35.0, driver 616.92 | [Qwen3 1.7B](results/2026-10-02-qwen3-1.7b.json) | 79.26 tokens/s | 1.70 GB |
| October 2, 2026 UTC; same runtime/driver | [Qwen3 4B Instruct](results/2026-10-02-qwen3-4b-instruct.json) | 40.38 tokens/s | 3.18 GB |
| September 26, 2026 UTC; Ollama 0.34.4, driver 581.86 | [Qwen3 1.7B](results/qwen3-1.7b.json) | 74.16 tokens/s | 1.70 GB |
| September 26, 2026 UTC; same runtime/driver | [Qwen3 4B Instruct](results/qwen3-4b-instruct.json) | 40.03 tokens/s | 3.18 GB |

Each earlier mean uses three warm requests. The original script did not inspect residency for the September first request, so those historical records label it `initial`, with original timings and text preserved. Runtime, checkpoint, driver and session conditions differ; these rows are observations, not rankings or a controlled performance comparison.

## Build on the lab

Developers can clone the pinned source tag instead of downloading the release ZIP:

```powershell
git clone --branch v1.0.0 --depth 1 https://github.com/agammann/rtx-local-llm-lab.git
cd rtx-local-llm-lab
python -m unittest discover -s tests -v
python .\bench.py --help
```

The protocol tests run the actual CLI against local HTTP fixtures. They check residency labels, warm means, zero-VRAM CPU placement, invalid counters/metadata, unavailable models/endpoints and preservation of existing files. They require no model or GPU and do not measure answer quality. CI repeats them on Windows, macOS and Linux, then packages the exact committed source and tests a fresh ZIP consumer.

Read the [developer guide](docs/development.md) for the output contract and packaging, and [verification](VERIFICATION.md) for real-runtime evidence and its limits. Ollama's [Generate API](https://docs.ollama.com/api/generate) defines timing fields; [running models](https://docs.ollama.com/api/ps) defines allocation/context fields.

## Troubleshooting

| Result | Next step |
| :--- | :--- |
| Connection refused or request timeout | Start Ollama and check its exact listening port; `--timeout` is the per-request deadline |
| Model not installed | Pull the exact tag into that server; an `OLLAMA_HOST` setting can make the CLI target another server |
| Remote model rejected | Select locally installed weights rather than a cloud model descriptor |
| Existing output rejected | Choose a new filename; use `--overwrite` only when you intend to replace the earlier result |
| Zero GPU allocation | Inspect `ollama ps` and [Ollama GPU support](https://docs.ollama.com/gpu); CPU placement remains visible as zero |
| Invalid counters or metadata | Keep the failure and inspect the local runtime log; no successful benchmark file was produced |
| Cannot save output | Choose a writable local folder; the previous result remains intact on failure |

[MIT license](LICENSE) · [Third-party terms](THIRD_PARTY_NOTICES.md)
