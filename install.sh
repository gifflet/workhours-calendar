#!/bin/sh
# Workhours Calendar installer — pulls the prebuilt images and starts
# MongoDB + the API with Docker. Safe to re-run: it updates the containers
# and keeps the data (stored in the workhours_mongo volume).
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/gifflet/workhours-calendar/main/install.sh | sh
#
# Options (environment variables):
#   WORKHOURS_PORT  Host port for the API (default: 8001)
#   MONGO_URL       Use an external MongoDB instead of starting a container
set -eu

API_IMAGE="ghcr.io/gifflet/workhours-calendar-api:latest"
NETWORK="workhours"
API_PORT="${WORKHOURS_PORT:-8001}"

say() { printf '%s\n' "$*"; }
fail() { printf 'Error: %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 \
  || fail "Docker is required. Install it from https://docs.docker.com/get-docker/ and re-run."
docker info >/dev/null 2>&1 \
  || fail "Docker is installed but not running. Start it and re-run."

# Pick a MongoDB image the hardware can run: Mongo 5+ needs ARMv8.2-A,
# which Raspberry Pi 3/4 CPUs lack, and 32-bit ARM has no official image.
MONGO_IMAGE="mongo:7"
case "$(uname -m)" in
  armv7l|armv6l)
    [ -n "${MONGO_URL:-}" ] \
      || fail "MongoDB has no official 32-bit ARM image. Set MONGO_URL to an external MongoDB and re-run."
    ;;
  aarch64|arm64)
    model=$(tr -d '\0' < /proc/device-tree/model 2>/dev/null || true)
    case "$model" in
      *"Raspberry Pi 3"*|*"Raspberry Pi 4"*) MONGO_IMAGE="mongo:4.4" ;;
    esac
    ;;
esac

# Fail early if the port is served by something we don't manage.
if curl -fs -o /dev/null --max-time 2 "http://localhost:$API_PORT/health" 2>/dev/null; then
  docker ps --format '{{.Names}}' | grep -qx workhours-api \
    || fail "Port $API_PORT is already in use by something else. Set WORKHOURS_PORT to a free port and re-run."
fi

say "Setting up Workhours Calendar (API on port $API_PORT)..."
docker network inspect "$NETWORK" >/dev/null 2>&1 \
  || docker network create "$NETWORK" >/dev/null

if [ -z "${MONGO_URL:-}" ]; then
  MONGO_URL="mongodb://workhours-mongo:27017"
  docker pull "$MONGO_IMAGE"
  docker rm -f workhours-mongo >/dev/null 2>&1 || true
  docker run -d --name workhours-mongo --network "$NETWORK" \
    --restart unless-stopped -v workhours_mongo:/data/db "$MONGO_IMAGE" >/dev/null
fi

docker pull "$API_IMAGE"
docker rm -f workhours-api >/dev/null 2>&1 || true
docker run -d --name workhours-api --network "$NETWORK" \
  --restart unless-stopped -p "$API_PORT:8000" \
  -e MONGO_URL="$MONGO_URL" "$API_IMAGE" >/dev/null

say "Waiting for the API to become healthy..."
health=""
i=0
while [ "$i" -lt 30 ]; do
  health=$(curl -fs "http://localhost:$API_PORT/health" 2>/dev/null || true)
  case "$health" in *'"mongodb":"up"'*) break ;; esac
  i=$((i + 1))
  sleep 1
done
case "$health" in
  *'"mongodb":"up"'*) ;;
  *) fail "API did not become healthy in 30s. Check: docker logs workhours-api" ;;
esac

say ""
say "Workhours Calendar is up:"
say "  API:        http://localhost:$API_PORT"
say "  Swagger UI: http://localhost:$API_PORT/docs"
say ""
say "Containers restart with Docker on boot. Re-run this script to update."
say "Uninstall: docker rm -f workhours-api workhours-mongo && docker volume rm workhours_mongo"
