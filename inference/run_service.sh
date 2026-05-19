#!/bin/sh
set -eu

start_service() {
  exec python run_service.py
}

if [ "${RDS_TUNNEL_ENABLED:-false}" != "true" ]; then
  start_service
fi

: "${BASTION_HOST:?BASTION_HOST is required when RDS_TUNNEL_ENABLED=true}"
: "${BASTION_USER:?BASTION_USER is required when RDS_TUNNEL_ENABLED=true}"
: "${BASTION_SSH_KEY_PATH:?BASTION_SSH_KEY_PATH is required when RDS_TUNNEL_ENABLED=true}"
: "${RDS_TUNNEL_REMOTE_HOST:?RDS_TUNNEL_REMOTE_HOST is required when RDS_TUNNEL_ENABLED=true}"

LOCAL_PORT="${RDS_TUNNEL_LOCAL_PORT:-3307}"
REMOTE_PORT="${RDS_TUNNEL_REMOTE_PORT:-3306}"

export DB_HOST=127.0.0.1
export DB_PORT="${LOCAL_PORT}"

chmod 600 "${BASTION_SSH_KEY_PATH}" 2>/dev/null || true

ssh \
  -o ExitOnForwardFailure=yes \
  -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  -o ServerAliveInterval=60 \
  -i "${BASTION_SSH_KEY_PATH}" \
  -N \
  -L "127.0.0.1:${LOCAL_PORT}:${RDS_TUNNEL_REMOTE_HOST}:${REMOTE_PORT}" \
  "${BASTION_USER}@${BASTION_HOST}" &

SSH_PID=$!

cleanup() {
  kill "${SSH_PID}" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

python - <<'PY'
import os
import socket
import sys
import time

host = "127.0.0.1"
port = int(os.environ.get("DB_PORT", "3307"))

deadline = time.time() + 20
while time.time() < deadline:
    sock = socket.socket()
    sock.settimeout(1)
    try:
        sock.connect((host, port))
        sock.close()
        sys.exit(0)
    except OSError:
        time.sleep(0.5)
    finally:
        try:
            sock.close()
        except OSError:
            pass

print(f"Tunnel did not become available on {host}:{port}", file=sys.stderr)
sys.exit(1)
PY

start_service
