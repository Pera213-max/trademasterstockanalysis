#!/usr/bin/env python3
"""
Test macro indicators API endpoint
Run: python test_macro_api.py
"""

import requests
import json

print("=" * 60)
print("Testing Macro Indicators API")
print("=" * 60)

# Test backend health
print("\n1. Testing backend health...")
try:
    response = requests.get("http://localhost:8000/docs", timeout=5)
    if response.status_code == 200:
        print("✓ Backend is running on port 8000")
    else:
        print(f"⚠ Backend responded with status {response.status_code}")
except requests.exceptions.RequestException as e:
    print(f"✗ Backend not accessible: {e}")
    print("\nMake sure backend is running:")
    print("  cd /home/user/pera/backend")
    print("  python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
    exit(1)

# Test macro indicators endpoint
print("\n2. Testing /api/macro/indicators...")
try:
    response = requests.get("http://localhost:8000/api/macro/indicators", timeout=15)

    if response.status_code == 200:
        data = response.json()

        print(f"✓ API responded successfully!")
        print(f"\n  Response structure:")
        print(f"    - success: {data.get('success')}")
        print(f"    - count: {data.get('count')}")
        print(f"    - indicators: {len(data.get('data', []))}")

        if data.get('data'):
            print(f"\n  Sample indicator:")
            indicator = data['data'][0]
            print(f"    - {indicator.get('shortName')}: {indicator.get('currentValue')} {indicator.get('unit', '')}")
            print(f"    - Change: {indicator.get('changePercent', 0):.2f}%")
            print(f"    - Impact: {indicator.get('impact')}")

            print(f"\n  All indicators:")
            for ind in data['data']:
                value = ind.get('currentValue', 0)
                unit = ind.get('unit', '')
                change = ind.get('changePercent', 0)
                print(f"    - {ind.get('shortName'):15} {value:>10.2f} {unit:3} ({change:+.2f}%)")

        print("\n" + "=" * 60)
        print("SUCCESS: Backend is working correctly! 🎉")
        print("=" * 60)

        # Save response for inspection
        with open('/tmp/macro_response.json', 'w') as f:
            json.dump(data, f, indent=2)
        print("\nFull response saved to: /tmp/macro_response.json")

    else:
        print(f"✗ API returned status {response.status_code}")
        print(f"  Response: {response.text[:200]}")

except requests.exceptions.RequestException as e:
    print(f"✗ Request failed: {e}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
