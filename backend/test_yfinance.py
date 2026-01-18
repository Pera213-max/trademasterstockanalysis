#!/usr/bin/env python3
"""
Test if yfinance works in your environment
Run: python test_yfinance.py
"""

import sys

print("=" * 60)
print("Testing yfinance installation...")
print("=" * 60)

# Test 1: Import yfinance
try:
    import yfinance as yf
    print("✓ yfinance imported successfully")
    print(f"  Version: {yf.__version__}")
except Exception as e:
    print(f"✗ yfinance import failed: {e}")
    print("\nInstall with: pip install --no-build-isolation yfinance")
    sys.exit(1)

# Test 2: Fetch real data
try:
    print("\nFetching AAPL data...")
    ticker = yf.Ticker("AAPL")
    info = ticker.info

    if info and 'currentPrice' in info:
        print(f"✓ yfinance works! AAPL price: ${info['currentPrice']}")
    else:
        hist = ticker.history(period="1d")
        if not hist.empty:
            price = hist['Close'].iloc[-1]
            print(f"✓ yfinance works! AAPL price: ${price:.2f}")
        else:
            print("⚠ Got data but no price info")

    print("\n" + "=" * 60)
    print("SUCCESS: yfinance is working correctly! 🎉")
    print("=" * 60)

except Exception as e:
    print(f"✗ yfinance test failed: {e}")
    print("\nTroubleshooting:")
    print("1. pip install --no-build-isolation yfinance")
    print("2. pip install multitasking")
    print("3. Try: conda install -c conda-forge yfinance")
    sys.exit(1)
