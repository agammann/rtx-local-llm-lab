# Development

The lab has one standard-library CLI, protocol tests and standalone result files. Python 3.10 or newer is required. No package install, model download or GPU is needed for deterministic checks.

```powershell
python -m unittest discover -s tests -v
python bench.py --version
python bench.py --help
```

`api_json` calls Ollama's local JSON API. `models` validates model-list responses, and `tokens_per_second` rejects missing/noninteger/zero generation counters. Results include every measured response, the installed model digest and request settings; the warm mean excludes the initial request. GPU metadata is optional and separate from allocation reported by Ollama.

The tests start a loopback HTTP fixture and invoke the actual CLI as a subprocess. They prove request/error/storage behavior, not real inference speed or model quality. Keep a new prompt or performance experiment separate from those protocol expectations and retain its first outcome. A model, runtime, driver or context change needs a new record, rather than editing an older result.

## Result contract

New results identify `format: rtx-local-llm-lab` and `version: 1`. Earlier unversioned records are historical observations and remain readable JSON. There is no import, migration, database or account synchronization.

Each result records requested settings and reported context separately. A model reaching the output cap still has usable timing counters, so its `done_reason` remains visible. Zero reported VRAM remains valid CPU placement. Do not label either case as a general performance or accuracy pass.

Saving uses a temporary file in the destination folder, flushes it, then exposes the completed file. Default creation refuses an existing filename; explicit overwrite uses an atomic replacement. Keep output directories on a writable local filesystem. Output-write errors leave an earlier record untouched.

## Package a source release

The repository's version command, `VERSION` and changelog must agree. Packaging requires a clean committed Git tree. From the repository root:

```powershell
python scripts/package-release.py
python scripts/check-consumer.py --out ../rtx-source-consumer
```

The source ZIP contains every tracked regular file, with the exact commit in its ZIP comment, plus a ZIP checksum and `SHA256SUMS`. Model weights, credentials, runtime/server state, Python environments and user outputs are excluded. Packaging fails on private/generated tracked paths or secret patterns.

The consumer check verifies checksums, commit, safe ZIP paths and every tracked file's exact bytes, then runs the CLI version command and protocol suite in a new folder outside the checkout. Release CI repeats this on Windows, macOS and Linux. Publication runs only after all main-commit checks succeed and verifies the complete asset set before publishing.

Published assets are a snapshot. Later commits do not rewrite an existing published version; change the version and verify another snapshot for a subsequent release. Keep result JSON files with the source/runtime/model details used to produce them.
