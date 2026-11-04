#!/usr/bin/env bash
# Build the image and check how it behaves with good and bad credentials.
#
#   deploy/verify_image.sh
#
# Needs docker or podman, and MCP_AUTH_TOKEN, OIG_DATA_API_BASE_URL,
# CF_ACCESS_CLIENT_ID, and CF_ACCESS_CLIENT_SECRET in the environment or `.env`.
# Secrets reach the containers through a private env file, never through argv,
# and are never printed. Exit code 0 means every check passed.

set -u
cd "$(dirname "$0")/.."

ENGINE="${CONTAINER_ENGINE:-$(command -v podman || command -v docker)}"
IMAGE="oig-mcp-verify:local"
PORT="${VERIFY_PORT:-18080}"
WORK="$(mktemp -d)"
FAILED=0
PASSED=0

read_setting() {
  local value="${!1:-}"
  if [ -z "$value" ] && [ -f .env ]; then
    value="$(grep -E "^$1=" .env | tail -1 | cut -d= -f2- | tr -d "\"'")"
  fi
  printf '%s' "$value"
}

TOKEN="$(read_setting MCP_AUTH_TOKEN)"
API_URL="$(read_setting OIG_DATA_API_BASE_URL)"
CF_ID="$(read_setting CF_ACCESS_CLIENT_ID)"
CF_SECRET="$(read_setting CF_ACCESS_CLIENT_SECRET)"

for setting in TOKEN API_URL CF_ID CF_SECRET; do
  if [ -z "${!setting}" ]; then
    echo "Missing a required setting: $setting"
    exit 2
  fi
done

report() { # name, 0 for pass
  if [ "$2" -eq 0 ]; then
    PASSED=$((PASSED + 1)); echo "  PASS  $1"
  else
    FAILED=$((FAILED + 1)); echo "  FAIL  $1"
  fi
}

env_file() { # name, then KEY=VALUE lines
  local file="$WORK/$1.env"; shift
  ( umask 077; printf '%s\n' "$@" > "$file" )
  printf '%s' "$file"
}

no_secrets_in() { # file
  for secret in "$TOKEN" "$CF_ID" "$CF_SECRET"; do
    if grep -qF -- "$secret" "$1"; then return 1; fi
  done
  return 0
}

stop_server() {
  "$ENGINE" rm -f oig-mcp-verify >/dev/null 2>&1
}

cleanup() {
  stop_server
  rm -rf "$WORK"
}
trap cleanup EXIT

start_server() { # env file
  stop_server
  "$ENGINE" run -d --name oig-mcp-verify -p "127.0.0.1:$PORT:8080" \
    --env-file "$1" "$IMAGE" >/dev/null
  for _ in $(seq 1 30); do
    curl -fs -m 2 "http://127.0.0.1:$PORT/health" >/dev/null && return 0
    sleep 1
  done
  return 1
}

call_status_tool() { # prints the tool's text result
  uv run python - "http://127.0.0.1:$PORT/mcp" <<'PY'
import asyncio, os, sys
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

async def main():
    transport = StreamableHttpTransport(
        sys.argv[1], headers={"Authorization": "Bearer " + os.environ["VERIFY_TOKEN"]}
    )
    async with Client(transport, timeout=60) as client:
        result = await client.call_tool(
            "vaoig_get_dataset_status", {}, raise_on_error=False
        )
        print(result.content[0].text)

asyncio.run(main())
PY
}

echo "Building with $ENGINE"
if ! "$ENGINE" build -q -t "$IMAGE" . >/dev/null; then
  echo "Build failed"; exit 1
fi

echo
echo "Image contents"
"$ENGINE" run --rm --entrypoint sh "$IMAGE" -c 'test ! -e /app/.env && test "$(id -u)" != 0'
report "no .env in the image, and it runs as non-root" $?
"$ENGINE" history --no-trunc "$IMAGE" > "$WORK/history.txt" 2>&1
"$ENGINE" inspect "$IMAGE" > "$WORK/inspect.txt" 2>&1
no_secrets_in "$WORK/history.txt" && no_secrets_in "$WORK/inspect.txt"
report "no secret in the image's layers or configuration" $?

echo
echo "Refuses to start unsafe"
"$ENGINE" run --rm --env-file "$(env_file notoken "OIG_DATA_API_BASE_URL=$API_URL")" \
  "$IMAGE" > "$WORK/notoken.log" 2>&1
[ $? -ne 0 ] && grep -q "MCP_AUTH_TOKEN must be set" "$WORK/notoken.log"
report "exits without MCP_AUTH_TOKEN" $?
"$ENGINE" run --rm --env-file "$(env_file short MCP_AUTH_TOKEN=short)" \
  "$IMAGE" > "$WORK/short.log" 2>&1
[ $? -ne 0 ]
report "exits with a token under 32 characters" $?
"$ENGINE" run --rm --env-file "$(env_file plain \
  "MCP_AUTH_TOKEN=$TOKEN" OIG_DATA_API_BASE_URL=http://example.com/v1/)" \
  "$IMAGE" > "$WORK/plain.log" 2>&1
[ $? -ne 0 ]
report "exits with a plain http remote API URL" $?
no_secrets_in "$WORK/plain.log"
report "startup failure does not print the token" $?

export VERIFY_TOKEN="$TOKEN"

echo
echo "Bad Access token: the server runs, the data API refuses it, nothing leaks"
for case_name in missing wrong; do
  if [ "$case_name" = missing ]; then
    file="$(env_file nocf "MCP_AUTH_TOKEN=$TOKEN" "OIG_DATA_API_BASE_URL=$API_URL")"
  else
    file="$(env_file badcf "MCP_AUTH_TOKEN=$TOKEN" "OIG_DATA_API_BASE_URL=$API_URL" \
      CF_ACCESS_CLIENT_ID=wrong.access CF_ACCESS_CLIENT_SECRET=wrong)"
  fi
  start_server "$file"
  report "$case_name Access token: server starts" $?
  call_status_tool > "$WORK/$case_name.out" 2>&1
  grep -q "status 401" "$WORK/$case_name.out" && ! grep -q '"data_as_of": "20' "$WORK/$case_name.out"
  report "$case_name Access token: tool reports a refusal and returns no data" $?
  ! grep -qF "${API_URL#https://}" "$WORK/$case_name.out"
  report "$case_name Access token: error does not reveal the API address" $?
done

echo
echo "Good credentials"
start_server "$(env_file good "MCP_AUTH_TOKEN=$TOKEN" "OIG_DATA_API_BASE_URL=$API_URL" \
  "CF_ACCESS_CLIENT_ID=$CF_ID" "CF_ACCESS_CLIENT_SECRET=$CF_SECRET")"
report "server starts" $?
MCP_AUTH_TOKEN="$TOKEN" OIG_DATA_API_BASE_URL="$API_URL" \
  CF_ACCESS_CLIENT_ID="$CF_ID" CF_ACCESS_CLIENT_SECRET="$CF_SECRET" \
  uv run python deploy/verify_deployment.py --url "http://127.0.0.1:$PORT"
report "verify_deployment.py against this container" $?

"$ENGINE" logs oig-mcp-verify > "$WORK/server.log" 2>&1
no_secrets_in "$WORK/server.log"
report "server log contains no secret" $?

echo
echo "$PASSED passed, $FAILED failed"
[ "$FAILED" -eq 0 ]
