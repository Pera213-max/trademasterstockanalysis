#!/usr/bin/env bash
set -euo pipefail

# Mixed load test for key endpoints (FI analysis/history/screener + US analysis + portfolio POST).
# Uses ApacheBench (ab) only.
#
# Usage:
#   BASE_URL=http://localhost:8000 CONCURRENCY=200 REQUESTS=2000 PARALLEL=1 ./scripts/load_test_mix.sh

BASE_URL="${BASE_URL:-http://localhost:8000}"
CONCURRENCY="${CONCURRENCY:-200}"
REQUESTS="${REQUESTS:-2000}"
PARALLEL="${PARALLEL:-0}"
TICKER_FI="${TICKER_FI:-NDA}"
TICKER_US="${TICKER_US:-AAPL}"

if [[ "${TICKER_FI}" != *".HE" ]]; then
  TICKER_FI="${TICKER_FI}.HE"
fi

if ! command -v ab >/dev/null 2>&1; then
  echo "ApacheBench (ab) not found. Install apache2-utils."
  exit 1
fi

PAYLOAD_FILE="$(mktemp)"
cat > "${PAYLOAD_FILE}" <<'JSON'
{
  "holdings": [
    {"ticker": "NOKIA.HE", "shares": 100, "avg_cost": 3.5},
    {"ticker": "AAPL", "shares": 10, "avg_cost": 150}
  ]
}
JSON

banner() {
  echo "== $1 =="
}

run_get() {
  local url="$1"
  banner "GET ${url}"
  ab -n "${REQUESTS}" -c "${CONCURRENCY}" "${url}"
  echo
}

run_post() {
  local url="$1"
  banner "POST ${url}"
  ab -n "${REQUESTS}" -c "${CONCURRENCY}" -p "${PAYLOAD_FILE}" -T "application/json" "${url}"
  echo
}

ENDPOINTS=(
  "${BASE_URL}/api/fi/analysis/${TICKER_FI}"
  "${BASE_URL}/api/fi/history/${TICKER_FI}?range=1y&interval=1d"
  "${BASE_URL}/api/fi/screener?sort_by=score&sort_order=desc&limit=25"
  "${BASE_URL}/api/stocks/stock/${TICKER_US}/analysis"
)

banner "Base URL: ${BASE_URL}"
banner "Concurrency: ${CONCURRENCY}"
banner "Requests: ${REQUESTS}"
banner "FI Ticker: ${TICKER_FI}"
banner "US Ticker: ${TICKER_US}"

if [[ "${PARALLEL}" == "1" ]]; then
  for url in "${ENDPOINTS[@]}"; do
    run_get "${url}" &
  done
  run_post "${BASE_URL}/api/portfolio/analyze" &
  wait
else
  for url in "${ENDPOINTS[@]}"; do
    run_get "${url}"
  done
  run_post "${BASE_URL}/api/portfolio/analyze"
fi

rm -f "${PAYLOAD_FILE}"
