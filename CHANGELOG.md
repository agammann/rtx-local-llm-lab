# Changelog

## 1.0.1

- Benchmark requests now stay at the selected loopback endpoint: proxy handling is disabled and HTTP redirects are rejected.
- Synthetic GET and POST redirect regressions cover the local connection boundary without requiring Ollama or a GPU.
- Earlier result files and the v1.0.0 release remain unchanged.

## 1.0.0

- The default endpoint matches Ollama's desktop port 11434; context length is explicit and recorded with the request settings.
- Existing result files are preserved by default. Explicit overwrite replaces a result only after the complete measurement succeeds.
- Invalid runtime metadata, unavailable endpoints/models and interrupted measurements fail clearly without a successful result.
- Models reported as remote/cloud are rejected before generation, preserving the local measurement scope.
- Versioned source ZIPs, checksums, developer instructions and fresh consumer checks provide a reproducible starting point.
- Earlier measurement files remain unchanged. The new short real run retains every first response and does not make a general speed or quality claim.
