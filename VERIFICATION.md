# Verification

## October 8, 2026 UTC v1 check

The exact current nine-file native source baseline was reconstructed before changes. The existing three protocol tests passed. Eight current tests now exercise the actual CLI against a loopback fixture: resident/unloaded labels, the warm mean, zero-VRAM CPU allocation, invalid counters/metadata, unavailable models/endpoints, remote-model rejection and preservation of existing output files. They make no model or paid request.

A separate real run used Python 3.12.14 on Windows, Ollama 0.35.0, NVIDIA GeForce RTX 3050 6GB Laptop GPU and driver 616.92. The owned Qwen3 1.7B Q4_K_M cache was reused; no weights were downloaded. The prompt, settings and first-response criteria were fixed before generation. An isolated loopback server was initially empty. The actual CLI made one initial request and two warm requests with an explicit 4096-token context.

All three completed normally with positive generation counters. The warm mean was 111.87 tokens/s. Ollama reported 1,702,593,821 bytes in VRAM and a loaded context of 4096; the runner log identified CUDA0 buffers. The result retains every first response and its timings. The initial response named all three monitor checks but added an introductory sentence, failing exactly-three-line formatting. No response was selected or regenerated to improve that outcome.

The initial cold request took 52,236.2 ms total, including 27,802.81 ms reported load time. Those values reflect this session's actual initialization and caching conditions. They are not promises about another machine or a controlled explanation of the differences from earlier records. The two warm requests are a small demonstration of the measurement path, not a model ranking or accuracy benchmark.

After measurement, only the owned test model was unloaded, `/api/ps` was empty and the isolated server/runner were stopped. Other applications, existing model weights and the four historical result files were preserved. Calling the stopped endpoint failed clearly without creating a result.

The source release and checksum consumer are checked independently from the live model run. Protocol checks on other CI operating systems do not establish their Ollama/GPU compatibility. This pass did not reinstall Ollama, test Docker, certify every GPU/model/context, or assess general factual accuracy.

## Historical records

The September 26 and October 2 JSON measurements remain unchanged. Their runtime/model/driver fields, initial-request labels and original generated text are retained. The README explains their separate conditions. A passing timing record does not prove that a response followed its formatting instruction or that an application built with that model will answer correctly.
