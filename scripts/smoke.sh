#!/usr/bin/env bash
# Smoke test the built app image end-to-end:
#   1. SearXNG answers JSON on loopback   2. crw scrapes a page
#   3. the MCP bridge lists and executes both tools
# Search assertions check the response *scheme*, not live engine content,
# so rate-limited engines can't flake CI.
set -euo pipefail

IMAGE="${1:?usage: smoke.sh <image-tag>}"
NAME=crw-smoke
HERE="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  status=$?
  if [ "$status" -ne 0 ]; then
    echo "--- container logs (tail) ---"
    docker logs "$NAME" 2>&1 | tail -40 || true
  fi
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  exit "$status"
}
trap cleanup EXIT

docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" \
  -v "${HERE}/ci-options.json:/data/options.json:ro" "$IMAGE" >/dev/null

probe() { docker exec "$NAME" curl -sf -m "$1" "${@:2}"; }

echo "waiting for services …"
for _ in $(seq 1 45); do
  if probe 2 -o /dev/null http://127.0.0.1:8080/ 2>/dev/null \
     && probe 2 -o /dev/null -X POST http://127.0.0.1:8099/mcp \
          -H 'Content-Type: application/json' \
          -H 'Accept: application/json, text/event-stream' \
          -d '{"jsonrpc":"2.0","id":0,"method":"ping"}' 2>/dev/null; then
    break
  fi
  sleep 2
done

echo "1/4 searxng JSON API"
probe 25 'http://127.0.0.1:8080/search?q=test&format=json' | grep -q '"results"'

echo "2/4 crw /v1/scrape"
probe 45 -X POST http://127.0.0.1:3000/v1/scrape \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com"}' | grep -q '"success":true'

MCP=http://127.0.0.1:8099/mcp
H1='Content-Type: application/json'
H2='Accept: application/json, text/event-stream'

echo "3/4 mcp tools/list"
LIST=$(probe 10 -X POST "$MCP" -H "$H1" -H "$H2" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}')
echo "$LIST" | grep -q '"name":"web_search"'
echo "$LIST" | grep -q '"name":"web_scrape"'

echo "4/4 mcp tools/call web_search (scheme keys)"
OUT=$(probe 60 -X POST "$MCP" -H "$H1" -H "$H2" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"web_search","arguments":{"query":"home assistant"}}}')
for key in source query num_results results featured_image instruction; do
  echo "$OUT" | grep -q "\\\\\"${key}\\\\\"" || { echo "missing key: $key"; exit 1; }
done

echo "smoke OK"
