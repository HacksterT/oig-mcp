#!/usr/bin/env bash
# Register oig-mcp in watsonx Orchestrate as a local (stdio) MCP toolkit.
#
# Orchestrate uploads a staged copy of the server, installs its pinned
# dependencies, and runs `python server.py` over stdio inside its own runtime.
# The server reaches the data API with four values. They go into a key_value
# connection, which Orchestrate passes to the server as environment variables.
#
# Run from anywhere, with the ADK installed and the repository's .env filled in:
#   bash deploy/ibm/local-mcp-toolkit/register-toolkit.sh
#
# Values are read from the environment first, then from the repository's .env.
# Nothing is printed. Safe to rerun: it replaces the toolkit with a fresh import.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

ADK_ENV="${WXO_ENV_NAME:-gsa-hackathon}"
TOOLKIT="${TOOLKIT_NAME:-oig_mcp_TES}"
CONNECTION="${CONNECTION_NAME:-oig_mcp_data_TES}"

# Read one value from the environment, else from .env, without printing it.
value() {
  local name="$1" v="${!1:-}"
  if [[ -z "$v" && -f "$ENV_FILE" ]]; then
    v="$(grep -E "^${name}=" "$ENV_FILE" | tail -1 | cut -d= -f2- || true)"
    v="${v%\"}"; v="${v#\"}"; v="${v%\'}"; v="${v#\'}"
  fi
  printf '%s' "$v"
}

require() {
  local v
  v="$(value "$1")"
  if [[ -z "$v" ]]; then
    echo "FATAL: $1 is not set in the environment or in ${ENV_FILE}" >&2
    exit 1
  fi
  printf '%s' "$v"
}

command -v orchestrate >/dev/null || { echo "FATAL: install the ADK: uv tool install ibm-watsonx-orchestrate" >&2; exit 1; }
command -v uv >/dev/null || { echo "FATAL: uv is needed to pin dependencies from uv.lock" >&2; exit 1; }

BASE_URL="$(require OIG_DATA_API_BASE_URL)"
CF_ID="$(require CF_ACCESS_CLIENT_ID)"
CF_SECRET="$(require CF_ACCESS_CLIENT_SECRET)"
API_KEY="$(require OIG_DATA_API_KEY)"
[[ "$BASE_URL" == https://* ]] || { echo "FATAL: OIG_DATA_API_BASE_URL must start with https://" >&2; exit 1; }

# The Orchestrate instance URL and API key, under either naming.
WXO_URL="$(value WXO_INSTANCE_URL)"; [[ -n "$WXO_URL" ]] || WXO_URL="$(value IBM_URL)"
WXO_KEY="$(value WXO_API_KEY)"; [[ -n "$WXO_KEY" ]] || WXO_KEY="$(value IBM_API_KEY)"
if [[ -z "$WXO_KEY" ]]; then
  read -r -s -p "watsonx Orchestrate API key (hidden): " WXO_KEY; echo
fi

echo "=== ADK environment '${ADK_ENV}' ==="
if ! orchestrate env list 2>/dev/null | grep -q "${ADK_ENV}"; then
  [[ -n "$WXO_URL" ]] || { echo "FATAL: set WXO_INSTANCE_URL (or IBM_URL in .env)" >&2; exit 1; }
  orchestrate env add --name "${ADK_ENV}" --url "${WXO_URL}" --type ibm_iam
fi
orchestrate env activate "${ADK_ENV}" --api-key "${WXO_KEY}" >/dev/null
echo "  active"

echo "=== Connection '${CONNECTION}' (key_value, passed to the server as environment variables) ==="
if ! orchestrate connections list 2>/dev/null | grep -q "${CONNECTION}"; then
  orchestrate connections add -a "${CONNECTION}" >/dev/null
fi
for env in draft live; do
  orchestrate connections configure -a "${CONNECTION}" --env "${env}" --type team --kind key_value >/dev/null
  orchestrate connections set-credentials -a "${CONNECTION}" --env "${env}" \
    -e "OIG_DATA_API_BASE_URL=${BASE_URL}" \
    -e "CF_ACCESS_CLIENT_ID=${CF_ID}" \
    -e "CF_ACCESS_CLIENT_SECRET=${CF_SECRET}" \
    -e "OIG_DATA_API_KEY=${API_KEY}" >/dev/null
  echo "  ${env}: set"
done

# Stage only what the server needs, flattened out of src/, with dependencies
# pinned to exactly what uv.lock records (the versions the tests ran against).
STAGE="$(mktemp -d)"
trap 'rm -rf "${STAGE}"' EXIT
cp -R "${REPO_ROOT}/src/oig_mcp" "${STAGE}/oig_mcp"
cp "${SCRIPT_DIR}/server.py" "${STAGE}/server.py"
find "${STAGE}" -type d -name '__pycache__' -prune -exec rm -rf {} +
chmod -R a+rX "${STAGE}"
(cd "${REPO_ROOT}" && uv export --frozen --no-default-groups --no-hashes \
  --no-emit-project --no-header --format requirements-txt -o "${STAGE}/requirements.txt" >/dev/null)

cat > "${STAGE}/toolkit.yaml" <<YAML
spec_version: v1
kind: mcp
name: ${TOOLKIT}
description: "$(sed -n 's/^description: "\(.*\)"$/\1/p' "${SCRIPT_DIR}/toolkit.yaml")"
command: python server.py
env: []
tools:
  - "*"
connections:
  - ${CONNECTION}
package_root: .
YAML

echo "=== Toolkit '${TOOLKIT}' ($(du -sh "${STAGE}" | cut -f1) staged) ==="
if orchestrate toolkits list 2>/dev/null | grep -q "${TOOLKIT}"; then
  orchestrate toolkits remove --name "${TOOLKIT}" || true
fi
orchestrate toolkits import -f "${STAGE}/toolkit.yaml" -a "${CONNECTION}"

echo
orchestrate toolkits list
echo
echo "Done. If an agent used the old toolkit, re-add the ${TOOLKIT} tools to it in the Orchestrate UI."
