# Security policy and threat model

Jojo Code accepts Python code in its hosted execution environment. Security requirements are documented here while the hosted runner is hardened.

## Current hosted execution state

The hosted copy enables `WEB=1` or `SANDBOX=1`. The runner then applies a Python-level import, builtin, and pattern blocklist before starting the one-shot trace runner.

This is a first line of defence, not a substitute for an operating-system-enforced sandbox.

## Required hardening

- Disposable isolated worker/container per run.
- Unprivileged user.
- Disabled network access.
- Read-only root filesystem and fresh temporary workspace.
- CPU, memory, process, file-size, output-size, and wall-clock limits outside Python code.
- Kill the whole process tree on timeout or cancellation.
- No secrets in execution environment.
- Rate limits and concurrent-run protection.
- Controlled hostile-code testing.

## Reporting

Report security issues privately to the repository maintainer. Do not open public issues for exploitable hosted-runner concerns.
