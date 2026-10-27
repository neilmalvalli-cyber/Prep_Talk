# Dedicated isolated runner

This service executes only the authored Python 3.11 and C++20 stdin/stdout problems. It is a separate service for the dedicated Ubuntu runner computer. The application host must never execute candidate code as a fallback. No gVisor or Docker installation/execution was performed on the development computer while preparing this source.

## Install on the dedicated Ubuntu computer

Create a minimal source archive on the application computer (this does not install or run runner software):

```powershell
apps/api/.venv/Scripts/python.exe apps/runner/package_source.py data/fieldnote-runner-source.tar.gz
```

The packager uses an explicit runner-file allowlist plus authored `content/coding/*.json` and `content/coding-private/*.json`. It excludes provider keys, `.env`, owner keys, interview data, caches, and unrelated application content. It refuses to overwrite an existing archive. The archive contains private coding tests, so transfer it only to the trusted dedicated runner administrator; never publish it to candidates.

Transfer only that archive to the dedicated Ubuntu computer, extract it into a new directory, and run the installer from that directory:

```bash
mkdir fieldnote-runner-source
tar -xzf fieldnote-runner-source.tar.gz -C fieldnote-runner-source
cd fieldnote-runner-source
sudo bash apps/runner/install-dedicated-ubuntu.sh
```

The installer requires Ubuntu with Python 3.11 or 3.12 and x86_64 or aarch64. It installs Ubuntu's Docker package plus `zstd`, downloads the latest official gVisor `gvisor.tar.zstd` archive and its SHA-512 file, verifies the checksum before extraction, and extracts the archive into `/usr/local/bin`. The official archive contains `runsc`, `containerd-shim-runsc-v1`, and the adjacent `gvisor-bin/` sidecar directory; these are kept together because `runsc` finds its sidecars next to its executable. The installer registers `runsc`, builds three fixed local images, creates a 256-bit bearer secret in a root-readable environment file, and starts a systemd service. Review the installer before running it and keep this computer dedicated to runner work. Runtime Python dependencies are resolved in `uv.lock`; `requirements.lock` is its hash-pinned export used by pip's `--require-hashes` mode. Both files are checked in so target installs fail if the lock and declared project inputs diverge.

The API binds to `127.0.0.1:9000` by default. Its `/health` endpoint requires bearer authentication. Readiness is reported only after the Docker daemon advertises the `runsc` runtime and fixed preflight commands run successfully inside both configured images. If the token, Docker, runtime, or either image is unavailable, job creation returns an infrastructure/service error without trying another runtime.

The runner process can control the local Docker daemon through its Unix socket. Candidate containers are created with no host mounts or sockets, no network, a read-only root, no Linux capabilities, `no-new-privileges`, a finite CPU/memory/process budget, and an ephemeral 64 MiB tmpfs. The runner process is trusted infrastructure; the isolation claim applies only to candidate containers created by the fixed service. A successful startup preflight does not replace independent verification of gVisor/kernel hardening on the target machine.

Static source-contract checks are in `apps/runner/tests/test_runner_static.py`. On a development machine with Python, they can be run without Docker using `python -m unittest discover -s apps/runner/tests`.

The installer stores a random token at `/etc/fieldnote-runner.env` with mode `0600`. Transfer the value of `RUNNER_BEARER_TOKEN` to the application backend through an administrator-controlled secret channel. Do not paste it into browser configuration, commit it, or send it in a URL. The backend calls:

```http
POST /jobs
Authorization: Bearer <runner token>
Content-Type: application/json

{"id":"<immutable-submission-id>","language":"python","source":"print('hello')","problem_id":"backend_frequency_counts","mode":"run","content_digest":"<64-character SHA-256 from the session snapshot>"}
```

`language` is `python` or `cpp`; `mode` is `run` (public examples only) or `submit` (public plus hidden suite). IDs are idempotency keys: resending the identical request returns its saved job; changing the source or other fields under an existing ID returns 409. The database keeps a source hash for idempotency, not source text. Source files and compiled artifacts exist only in bounded container tmpfs during the job and are removed with the container. Poll `GET /jobs/{id}` until complete or infrastructure_error. `DELETE /jobs/{id}` kills the active container, cancels the job, and deletes its stored fingerprint and result; later completion cannot recreate the row. A runner restart marks unfinished jobs as infrastructure errors and does not silently rerun candidate code.

Candidate source is limited to 64 KiB. C++ compilation uses only the fixed compiler image and command `g++ -std=c++20 -O2 -pipe`; Python uses the fixed Python 3.11 image. A separate C++ runtime image contains Debian's `libstdc++6` and shell utilities but no compiler. Both stages use the base image's unprivileged `nobody` account. There are no custom build commands, package installs, user mounts, GPU, network access, or Docker socket inside candidate containers. Compilation has a 15 second, 1 GiB budget. Each case has a 2 second, 256 MiB budget and the suite has a 30 second wall limit. Captured output is capped at 64 KiB per case even if the stream ends immediately after exceeding the cap. Public diagnostics include stdout, expected stdout, stderr, and outcome. Hidden inputs and expected outputs stay under `content/coding-private`; responses expose only aggregate hidden passed/total counts. `run` omits hidden outcomes entirely.

The 64 KiB output budget combines stdout and stderr. A case timeout or output
breach kills its entire container and stops the suite before another candidate
container is created. Such a terminating budget outcome takes precedence over
earlier wrong-answer/runtime outcomes in the job summary. Hidden totals count
only cases actually attempted; skipped cases are not represented as failures.

## Connecting a separate application computer

Keep the service loopback-only and use an SSH tunnel from the application computer to the runner host. For example, run this from the application host and keep it supervised:

```bash
ssh -N -L 127.0.0.1:19000:127.0.0.1:9000 runner-admin@<runner-host>
```

Configure the backend with `RUNNER_URL=http://127.0.0.1:19000` and `RUNNER_BEARER_TOKEN` copied securely from the runner's root-only environment file. The SSH tunnel encrypts code and results in transit. A managed TLS reverse proxy is another option; do not open plain HTTP port 9000 to a LAN or the internet. Restrict SSH access and firewall the runner host. The bearer credential grants code execution on the dedicated host and should be rotated if disclosed; after rotation restart the runner and update the backend at the same time.

## Content records

The runner loads a public problem at `content/coding/<problem_id>.json`. That record contains the candidate-visible statement, fixed stdin/stdout contract, public examples, and the name of its private test-set record. Hidden expected outputs are in `content/coding-private/<test-set>.json`. Do not serialize private test files into browser/API responses. The API's submission response is the only place hidden outcomes may appear, and there they are aggregate counts only.

Every request requires `content_digest`: SHA-256 of UTF-8 `json.dumps({"problem": public_record, "hidden": private_record}, sort_keys=True, separators=(",", ":"))` using Python's default ASCII escaping. The application captures this value at session creation. The runner loads both records once, checks their digest, then executes the same in-memory tests. A mismatch fails before candidate container creation, including in public-example mode. Updating authored tests therefore requires a new session and matching content on both hosts. The digest also participates in immutable job-ID comparison. Legacy application sessions without a captured execution digest cannot submit code.

Role files in `content/roles/` use `levels.junior` and `levels.intermediate`, each with expectations, competencies, question objectives, and a coding problem ID. Public scenario files in `content/scenarios/` contain initial facts and individually disclosed cards. They contain only a `private_reference_id` pointer; private causal references and criterion anchors live in `content/scenario-private/`. Load scenario records by explicit allowlisted ID, reveal only named cards under backend state rules, and never give `content/scenario-private/` to the browser or live interviewer. Shared criterion anchors are in `content/rubrics/criteria.json`. Versioned role prompts are in `prompts/`; prompts supplement backend authorization checks and do not replace them.

## Limitations

The bundled verification fixtures are authored examples, not human calibration or evidence that numeric assessment gates pass. This source has not been deployed on the dedicated host. The host's actual `runsc` runtime, resource enforcement, network denial, image provenance, firewall, API connectivity, and cleanup behavior remain unverified until the dedicated-host acceptance work is performed. Never describe those hardware/security properties as measured before collecting that evidence.

## Dedicated-host acceptance

After installing on the dedicated Ubuntu PC, load the existing protected environment into a root shell and run:

```bash
sudo bash -c 'set -a; source /etc/fieldnote-runner.env; set +a; cd /opt/fieldnote-runner/app; /opt/fieldnote-runner/venv/bin/python acceptance_dedicated.py'
```

This script deliberately refuses non-Linux execution. It checks authenticated runsc readiness, rejects unauthenticated access, and submits real Python/C++ correctness, wrong-answer, compile/runtime-error, timeout and output-limit jobs. It checks immutable ID retries and deletes each job afterward, verifying its removal. It also probes absence of a default network route and one denied external connection, attempts a bounded 96-child fork within the sandbox to check a finite process budget, cancels an active job, and runs a known-good attempt afterward. It writes `runner-acceptance-results.json` without credentials. It has only been syntax-checked here; no acceptance job has run. These probes are not independent kernel/cgroup verification; memory/GPU/filesystem hardening and comprehensive host/network review remain separate required checks.
