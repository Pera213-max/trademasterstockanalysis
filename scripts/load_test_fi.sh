#!/usr/bin/env bash
set -euo pipefail

# Simple load test helper for FI endpoints.
# Usage:
#   BASE_URL=http://localhost:8000 CONCURRENCY=50 REQUESTS=2000 ./load_test_fi.sh
#   MODE=duration DURATION=30s CONCURRENCY=100 ./load_test_fi.sh
# Optional:
#   WARM_CACHE=1 to pre-hit endpoints once before load.

BASE_URL="${BASE_URL:-http://localhost:8000}"
CONCURRENCY="${CONCURRENCY:-50}"
REQUESTS="${REQUESTS:-2000}"
DURATION="${DURATION:-30s}"
MODE="${MODE:-requests}" # "requests" or "duration"
WARM_CACHE="${WARM_CACHE:-0}"

ENDPOINTS=(
  "/api/fi/screener?sort_by=score&sort_order=desc&limit=25"
  "/api/fi/rank?limit=25"
  "/api/fi/movers?limit=10"
)

banner() {
  echo "== $1 =="
}

warm_cache() {
  banner "Warming cache"
  for path in "${ENDPOINTS[@]}"; do
    curl -s "${BASE_URL}${path}" >/dev/null || true
  done
}

run_hey() {
  local url="$1"
  if [[ "${MODE}" == "duration" ]]; then
    hey -z "${DURATION}" -c "${CONCURRENCY}" "${url}"
  else
    hey -n "${REQUESTS}" -c "${CONCURRENCY}" "${url}"
  fi
}

run_wrk() {
  local url="$1"
  # wrk supports duration only
  wrk -t4 -c"${CONCURRENCY}" -d"${DURATION}" "${url}"
}

run_ab() {
  local url="$1"
  if [[ "${MODE}" == "duration" ]]; then
    echo "ab does not support duration mode; using REQUESTS=${REQUESTS} instead."
  fi
  ab -n "${REQUESTS}" -c "${CONCURRENCY}" "${url}"
}

run_docker_hey() {
  local url="$1"
  if [[ "${MODE}" == "duration" ]]; then
    docker run --rm --network host rakyll/hey -z "${DURATION}" -c "${CONCURRENCY}" "${url}"
  else
    docker run --rm --network host rakyll/hey -n "${REQUESTS}" -c "${CONCURRENCY}" "${url}"
  fi
}

if [[ "${WARM_CACHE}" == "1" ]]; then
  warm_cache
fi

if command -v hey >/dev/null 2>&1; then
  RUNNER="hey"
elif command -v wrk >/dev/null 2>&1; then
  RUNNER="wrk"
elif command -v ab >/dev/null 2>&1; then
  RUNNER="ab"
else
  RUNNER="docker-hey"
fi

banner "Runner: ${RUNNER}"
banner "Base URL: ${BASE_URL}"
banner "Concurrency: ${CONCURRENCY}"
banner "Mode: ${MODE}"
if [[ "${MODE}" == "duration" ]]; then
  banner "Duration: ${DURATION}"
else
  banner "Requests: ${REQUESTS}"
fi

for path in "${ENDPOINTS[@]}"; do
  url="${BASE_URL}${path}"
  banner "Testing ${url}"
  case "${RUNNER}" in
    hey) run_hey "${url}" ;;
    wrk) run_wrk "${url}" ;;
    ab) run_ab "${url}" ;;
    docker-hey) run_docker_hey "${url}" ;;
  esac
  echo
done
