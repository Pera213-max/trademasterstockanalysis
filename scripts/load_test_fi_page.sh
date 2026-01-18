#!/usr/bin/env bash
set -euo pipefail

# Load test a single FI stock analysis page by hitting the same endpoints
# the page uses (analysis + history + screener). Optionally include the
# frontend HTML route.
#
# Usage:
#   TICKER=NDA BASE_URL=http://localhost:8000 CONCURRENCY=200 REQUESTS=2000 ./load_test_fi_page.sh
#   MODE=duration DURATION=30s CONCURRENCY=200 ./load_test_fi_page.sh
#   PARALLEL=1 CONCURRENCY=1000 REQUESTS=1000 ./load_test_fi_page.sh
#
# Optional:
#   FRONT_URL=https://trademaster.guru INCLUDE_FRONT=1
#   WARM_CACHE=1

BASE_URL="${BASE_URL:-http://localhost:8000}"
FRONT_URL="${FRONT_URL:-https://trademaster.guru}"
TICKER="${TICKER:-NDA}"
CONCURRENCY="${CONCURRENCY:-200}"
REQUESTS="${REQUESTS:-2000}"
DURATION="${DURATION:-30s}"
MODE="${MODE:-requests}" # "requests" or "duration"
PARALLEL="${PARALLEL:-0}"
WARM_CACHE="${WARM_CACHE:-0}"
INCLUDE_FRONT="${INCLUDE_FRONT:-0}"
INCLUDE_SCREENER="${INCLUDE_SCREENER:-0}"

if [[ "${TICKER}" != *".HE" ]]; then
  TICKER="${TICKER}.HE"
fi

ENDPOINTS=(
  "/api/fi/analysis/${TICKER}"
  "/api/fi/history/${TICKER}?range=1y&interval=1d"
)
if [[ "${INCLUDE_SCREENER}" == "1" ]]; then
  ENDPOINTS+=("/api/fi/screener?sort_by=score&sort_order=desc&limit=188")
fi

FRONT_PATH="/fi/stocks/${TICKER%.HE}"

banner() {
  echo "== $1 =="
}

warm_cache() {
  banner "Warming cache"
  for path in "${ENDPOINTS[@]}"; do
    curl -s "${BASE_URL}${path}" >/dev/null || true
  done
  if [[ "${INCLUDE_FRONT}" == "1" ]]; then
    curl -s "${FRONT_URL}${FRONT_PATH}" >/dev/null || true
  fi
}

run_ab() {
  local url="$1"
  if [[ "${MODE}" == "duration" ]]; then
    echo "ab does not support duration mode; using REQUESTS=${REQUESTS} instead."
  fi
  ab -n "${REQUESTS}" -c "${CONCURRENCY}" "${url}"
}

run_wrk() {
  local url="$1"
  wrk -t4 -c"${CONCURRENCY}" -d"${DURATION}" "${url}"
}

run_hey() {
  local url="$1"
  if [[ "${MODE}" == "duration" ]]; then
    hey -z "${DURATION}" -c "${CONCURRENCY}" "${url}"
  else
    hey -n "${REQUESTS}" -c "${CONCURRENCY}" "${url}"
  fi
}

if command -v hey >/dev/null 2>&1; then
  RUNNER="hey"
elif command -v wrk >/dev/null 2>&1; then
  RUNNER="wrk"
elif command -v ab >/dev/null 2>&1; then
  RUNNER="ab"
else
  echo "No load test tool found (hey/wrk/ab). Install apache2-utils or wrk."
  exit 1
fi

if [[ "${WARM_CACHE}" == "1" ]]; then
  warm_cache
fi

banner "Runner: ${RUNNER}"
banner "Base URL: ${BASE_URL}"
banner "Ticker: ${TICKER}"
banner "Concurrency: ${CONCURRENCY}"
banner "Mode: ${MODE}"
if [[ "${MODE}" == "duration" ]]; then
  banner "Duration: ${DURATION}"
else
  banner "Requests: ${REQUESTS}"
fi
if [[ "${PARALLEL}" == "1" ]]; then
  banner "Parallel: enabled"
fi

run_one() {
  local url="$1"
  banner "Testing ${url}"
  case "${RUNNER}" in
    hey) run_hey "${url}" ;;
    wrk) run_wrk "${url}" ;;
    ab) run_ab "${url}" ;;
  esac
  echo
}

if [[ "${PARALLEL}" == "1" ]]; then
  for path in "${ENDPOINTS[@]}"; do
    run_one "${BASE_URL}${path}" &
  done
  wait
else
  for path in "${ENDPOINTS[@]}"; do
    run_one "${BASE_URL}${path}"
  done
fi

if [[ "${INCLUDE_FRONT}" == "1" ]]; then
  run_one "${FRONT_URL}${FRONT_PATH}"
fi
