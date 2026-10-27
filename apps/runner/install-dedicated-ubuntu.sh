#!/usr/bin/env bash
set -euo pipefail

# Run only on the dedicated Ubuntu runner computer, from the repository root.
# This provisions Docker, gVisor, fixed images and a loopback-only API service.

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run with sudo: sudo bash apps/runner/install-dedicated-ubuntu.sh" >&2
  exit 1
fi
if [[ ! -f apps/runner/pyproject.toml || ! -f apps/runner/uv.lock || ! -f apps/runner/requirements.lock || ! -d content/coding || ! -d content/coding-private ]]; then
  echo "Run this script from the repository root containing the locked runner and content/." >&2
  exit 1
fi
if [[ "$(. /etc/os-release && echo "${ID:-}")" != "ubuntu" ]]; then
  echo "This installer supports Ubuntu only." >&2
  exit 1
fi
python3 - <<'PY'
import sys
if sys.version_info < (3, 11) or sys.version_info >= (3, 13):
    raise SystemExit("Python 3.11 or 3.12 is required; use a supported Ubuntu release.")
PY

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl docker.io python3-venv openssl zstd
systemctl enable --now docker

# Follow gVisor's documented checksum-verified release installation. The runsc
# binaries stay together in /usr/local/bin as required by the release archive.
arch="$(uname -m)"
case "$arch" in x86_64|aarch64) ;; *) echo "Unsupported gVisor architecture: $arch" >&2; exit 1 ;; esac
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
base="https://storage.googleapis.com/gvisor/releases/release/latest/${arch}"
curl --fail --location --silent --show-error "$base/gvisor.tar.zstd" -o "$tmpdir/gvisor.tar.zstd"
curl --fail --location --silent --show-error "$base/gvisor.tar.zstd.sha512" -o "$tmpdir/gvisor.tar.zstd.sha512"
(cd "$tmpdir" && sha512sum --check gvisor.tar.zstd.sha512)
tar --zstd -xf "$tmpdir/gvisor.tar.zstd" -C /usr/local/bin
/usr/local/bin/runsc install
systemctl restart docker

getent group docker >/dev/null || groupadd docker
getent group fieldnote-runner >/dev/null || groupadd --system fieldnote-runner
id -u fieldnote-runner >/dev/null 2>&1 || useradd --system --gid fieldnote-runner --create-home --shell /usr/sbin/nologin fieldnote-runner
usermod -a -G docker fieldnote-runner
install -d -m 0755 /opt/fieldnote-runner/app /srv/fieldnote-runner/content
install -d -o fieldnote-runner -g fieldnote-runner -m 0750 /var/lib/fieldnote-runner
cp -a apps/runner/. /opt/fieldnote-runner/app/
for folder in coding coding-private; do
  install -d -m 0755 "/srv/fieldnote-runner/content/$folder"
  cp -a "content/$folder/"*.json "/srv/fieldnote-runner/content/$folder/"
done
python3 -m venv /opt/fieldnote-runner/venv
/opt/fieldnote-runner/venv/bin/pip install --require-hashes -r /opt/fieldnote-runner/app/requirements.lock

docker build --pull -f /opt/fieldnote-runner/app/Dockerfile.python -t fieldnote-runner-python:3.11-v1 /opt/fieldnote-runner/app
docker build --pull -f /opt/fieldnote-runner/app/Dockerfile.cpp -t fieldnote-runner-cpp-compiler:20-v1 /opt/fieldnote-runner/app
docker build --pull -f /opt/fieldnote-runner/app/Dockerfile.cpp-runtime -t fieldnote-runner-cpp-runtime:20-v1 /opt/fieldnote-runner/app

install -d -m 0755 /etc/systemd/system
install -m 0644 /opt/fieldnote-runner/app/fieldnote-runner.service /etc/systemd/system/fieldnote-runner.service
if [[ ! -f /etc/fieldnote-runner.env ]]; then
  token="$(openssl rand -hex 32)"
  umask 077
  printf 'RUNNER_BEARER_TOKEN=%s\nRUNNER_DATABASE=/var/lib/fieldnote-runner/jobs.sqlite3\nRUNNER_CONTENT_ROOT=/srv/fieldnote-runner/content\nRUNNER_PYTHON_IMAGE=fieldnote-runner-python:3.11-v1\nRUNNER_CPP_COMPILE_IMAGE=fieldnote-runner-cpp-compiler:20-v1\nRUNNER_CPP_RUNTIME_IMAGE=fieldnote-runner-cpp-runtime:20-v1\nRUNNER_BIND=127.0.0.1\nRUNNER_PORT=9000\n' "$token" > /etc/fieldnote-runner.env
  chmod 0600 /etc/fieldnote-runner.env
fi
systemctl daemon-reload
systemctl enable --now fieldnote-runner.service

echo "Runner service installed. It listens on 127.0.0.1:9000 and remains unavailable until authenticated runsc preflight succeeds."
echo "Copy the bearer token securely to the application backend using: sudo cat /etc/fieldnote-runner.env"
echo "For a backend on another computer, use an SSH tunnel or a TLS reverse proxy; do not expose this HTTP port directly."
