#!/bin/sh
set -e

: "${YFINANCE_CACHE_DIR:=/tmp/py-yfinance}"
mkdir -p "$YFINANCE_CACHE_DIR"

if [ "${YFINANCE_AUTO_UPDATE:-true}" = "true" ]; then
  echo "Updating yfinance..."
  python -m pip uninstall -y yfinance >/dev/null 2>&1 || true
  python -m pip install --no-cache-dir --user --upgrade yfinance
fi

exec "$@"
