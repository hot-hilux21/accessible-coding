# Hosted execution security design

## Current boundary

- Public copy sets `WEB=1` or `SANDBOX=1`.
- Hosted runner applies Python-level blocked imports, builtins, and patterns.
- One-shot runner writes submitted code to a temporary file and executes through the trace runner.
- 10-second timeout enforced.
- Output is captured through temporary files and capped at 200 KiB.
- Process tree kill on timeout.
- Access code and rate limits enforced on run, answer, and stop routes.

## Outstanding boundary

- Move execution to an isolated container or equivalent OS sandbox.
- Disable network and enforce host-based file/network policy.
- Enforce CPU, memory, process, file-size, and output limits in the isolation layer.
- Preserve secrets separation.
