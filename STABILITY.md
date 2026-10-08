# RTX Local LLM Lab v1

Version 1.0.0 is a Python command-line measurement tool for a local Ollama runtime. It uses a fixed public prompt, records the exact installed model digest and available runtime details, distinguishes initial residency, and calculates generation throughput from Ollama's own counters. It does not rank models or establish general answer quality.

## Supported behavior

- Python 3.10 or newer, with no additional Python packages. Protocol and source-consumer checks run on Windows, macOS and Linux; the real Ollama/GPU acceptance run used Windows, Ollama 0.35.0 and an NVIDIA RTX 3050 laptop GPU.
- Loopback HTTP Ollama endpoints, including a nondefault local port. The default is the desktop runtime's port 11434. Locally installed weights only; reported remote/cloud model descriptors are rejected before generation. The script does not download weights, start servers, force GPU placement or select a hosted provider.
- An initial request followed by the requested number of warm requests. The initial request is excluded from the mean. Context length is requested explicitly and the runtime's reported loaded context is recorded separately.
- Zero VRAM is a valid CPU allocation. `done_reason: length` remains visible when a response reaches the output cap. Formatting and factual quality need separate review.
- Results are written only after every required measurement succeeds. Existing files are preserved unless `--overwrite` is explicit; failure still preserves an earlier result. Output creation exposes a completed temporary file, rather than a partly written JSON result.
- Clear errors for unavailable runtimes/models and invalid metadata or counters. Stopping while collecting measurements saves no incomplete result. Previously loaded models are not unloaded by the tool.

## Recovery and changes

Keep raw JSON records and their source release together. Choose a new filename for each measurement. After a failure, correct the endpoint, model or output path, then run again with a new filename; do not substitute a later response for an earlier observation.

The results are standalone files, with no database or account state. Back them up before changing machines or deleting a folder. Upgrades do not convert or overwrite existing results. The four earlier measurement records retain their original bytes and interpretation; v1 records add a format version, request settings, Python version and reported context length.

Downloaded model weights, Ollama state and GPU drivers belong to their respective installations. The source release contains no models, credentials or server data. Model downloads may change a tag's digest; every result records the installed digest so that difference remains visible.

## Boundaries

Remote servers, authenticated endpoints, universal GPU support, Docker installation and performance comparisons across every model/context are outside this v1 acceptance. A local GPU name comes from `nvidia-smi`; it is separate from Ollama's reported allocation. Real runtime evidence is one dedicated local session, not a hardware certification or accuracy benchmark.
