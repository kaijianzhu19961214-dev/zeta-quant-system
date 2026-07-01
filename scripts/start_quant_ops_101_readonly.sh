#!/usr/bin/env bash
set -euo pipefail

REMOTE_101_HOST="${REMOTE_101_HOST:-192.168.2.101}"
REMOTE_101_APP_ENV_FILE="${REMOTE_101_APP_ENV_FILE:-/home/ddd/ZeTa-quant-data-ingestion-layer/.env}"
REMOTE_101_MINIO_ENV_FILE="${REMOTE_101_MINIO_ENV_FILE:-/home/ddd/minio/quant_factor_api.env}"

LOCAL_101_POSTGRES_PORT="${LOCAL_101_POSTGRES_PORT:-15433}"
LOCAL_101_MINIO_PORT="${LOCAL_101_MINIO_PORT:-19001}"
LOCAL_101_CLICKHOUSE_PORT="${LOCAL_101_CLICKHOUSE_PORT:-18123}"

REMOTE_101_POSTGRES_PORT="${REMOTE_101_POSTGRES_PORT:-5432}"
REMOTE_101_MINIO_PORT="${REMOTE_101_MINIO_PORT:-9000}"
REMOTE_101_CLICKHOUSE_PORT="${REMOTE_101_CLICKHOUSE_PORT:-18123}"

ARTIFACT_LEDGER_DATABASE_SCHEMA="${ARTIFACT_LEDGER_DATABASE_SCHEMA:-zeta_quant_factor_validation}"
ARTIFACT_LEDGER_QUERY_LIMIT="${ARTIFACT_LEDGER_QUERY_LIMIT:-20}"
RUN_SMOKE="${RUN_SMOKE:-1}"
PYTHON_BIN="${PYTHON:-python3}"
QUANT_OPS_API_BASE_URL="${QUANT_OPS_API_BASE_URL:-http://127.0.0.1:${QUANT_OPS_API_PORT:-18030}}"

ensure_tunnel() {
  local local_port="$1"
  local remote_port="$2"
  local label="$3"

  if lsof -nP -iTCP:"${local_port}" -sTCP:LISTEN >/dev/null; then
    echo "${label} tunnel already listening on 127.0.0.1:${local_port}"
    return
  fi

  echo "starting ${label} tunnel: 127.0.0.1:${local_port} -> ${REMOTE_101_HOST}:127.0.0.1:${remote_port}"
  ssh -fN -L "127.0.0.1:${local_port}:127.0.0.1:${remote_port}" "${REMOTE_101_HOST}"
}

load_remote_quant_ops_exports() {
  ssh "${REMOTE_101_HOST}" \
    REMOTE_101_APP_ENV_FILE="${REMOTE_101_APP_ENV_FILE}" \
    REMOTE_101_MINIO_ENV_FILE="${REMOTE_101_MINIO_ENV_FILE}" \
    LOCAL_101_POSTGRES_PORT="${LOCAL_101_POSTGRES_PORT}" \
    LOCAL_101_MINIO_PORT="${LOCAL_101_MINIO_PORT}" \
    ARTIFACT_LEDGER_DATABASE_SCHEMA="${ARTIFACT_LEDGER_DATABASE_SCHEMA}" \
    ARTIFACT_LEDGER_QUERY_LIMIT="${ARTIFACT_LEDGER_QUERY_LIMIT}" \
    python3 - <<'PY'
from pathlib import Path
from urllib.parse import quote, quote_plus, urlsplit
import os
import shlex


def read_env_files(*, paths: list[Path]) -> dict[str, str]:
    values: dict[str, str] = {}
    for path in paths:
        if not path.exists():
            continue

        for raw_line in path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")

    return values


def build_asyncpg_url(*, database_url: str, local_postgres_port: str) -> str:
    parsed = urlsplit(database_url)
    username = quote_plus(parsed.username or "")
    password = quote_plus(parsed.password or "")
    userinfo = username if not password else f"{username}:{password}"
    path = parsed.path or "/postgres"
    query = f"?{parsed.query}" if parsed.query else ""

    if not userinfo:
        raise SystemExit("missing database user info in remote READ_DATABASE_URL")

    return (
        "postgresql+asyncpg://"
        f"{userinfo}@host.docker.internal:{local_postgres_port}{quote(path, safe='/')}{query}"
    )


app_env_file = Path(os.environ["REMOTE_101_APP_ENV_FILE"])
minio_env_file = Path(os.environ["REMOTE_101_MINIO_ENV_FILE"])
values = read_env_files(paths=[app_env_file, minio_env_file])

database_url = (
    values.get("READ_DATABASE_URL")
    or values.get("DATABASE_URL")
    or values.get("WRITE_DATABASE_URL")
)
if not database_url:
    raise SystemExit("missing required remote setting: READ_DATABASE_URL")

minio_secure = values.get("MINIO_SECURE") or "false"
minio_scheme = "https" if minio_secure.strip().lower() in {"1", "true", "yes", "on"} else "http"

exports = {
    "ARTIFACT_LEDGER_DATABASE_URL": build_asyncpg_url(
        database_url=database_url,
        local_postgres_port=os.environ["LOCAL_101_POSTGRES_PORT"],
    ),
    "ARTIFACT_LEDGER_DATABASE_SCHEMA": os.environ["ARTIFACT_LEDGER_DATABASE_SCHEMA"],
    "ARTIFACT_LEDGER_QUERY_LIMIT": os.environ["ARTIFACT_LEDGER_QUERY_LIMIT"],
    "ARTIFACT_OBJECT_STORE_ENDPOINT": (
        f"{minio_scheme}://host.docker.internal:{os.environ['LOCAL_101_MINIO_PORT']}"
    ),
    "ARTIFACT_OBJECT_STORE_ACCESS_KEY": (
        values.get("MINIO_ACCESS_KEY") or values.get("MINIO_ROOT_USER") or ""
    ),
    "ARTIFACT_OBJECT_STORE_SECRET_KEY": (
        values.get("MINIO_SECRET_KEY") or values.get("MINIO_ROOT_PASSWORD") or ""
    ),
    "ARTIFACT_OBJECT_STORE_SECURE": "true" if minio_scheme == "https" else "false",
}

missing_keys = [
    key
    for key, value in exports.items()
    if not value and key not in {"ARTIFACT_OBJECT_STORE_SECURE"}
]
if missing_keys:
    raise SystemExit("missing required remote settings: " + ", ".join(missing_keys))

for key, value in exports.items():
    print(f"export {key}={shlex.quote(value)}")
PY
}

ensure_tunnel "${LOCAL_101_POSTGRES_PORT}" "${REMOTE_101_POSTGRES_PORT}" "PostgreSQL"
ensure_tunnel "${LOCAL_101_MINIO_PORT}" "${REMOTE_101_MINIO_PORT}" "MinIO"
ensure_tunnel "${LOCAL_101_CLICKHOUSE_PORT}" "${REMOTE_101_CLICKHOUSE_PORT}" "ClickHouse"

remote_exports="$(load_remote_quant_ops_exports)"
eval "${remote_exports}"

docker compose up -d --force-recreate quant_ops_api quant_ops_web

if [[ "${RUN_SMOKE}" == "1" ]]; then
  QUANT_OPS_API_BASE_URL="${QUANT_OPS_API_BASE_URL}" \
    QUANT_OPS_EXPECTED_ARTIFACT_READ_STATUS=artifact_loaded \
    "${PYTHON_BIN}" scripts/smoke_quant_ops_api_comparison_artifact.py
fi
