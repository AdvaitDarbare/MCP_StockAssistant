import requests
import json
import time

BASE_URL = "http://127.0.0.1:8001/api/reports"
OWNER_KEY = "dev-test"

REPORTS = [
    ("citadel_technical", {"ticker": "PLTR"}),
    ("goldman_screener", {"limit": 5}),
    ("morgan_dcf", {"ticker": "AAPL"}),
    ("bridgewater_risk", {"holdings": [{"symbol": "AAPL", "weight": 0.5}, {"symbol": "MSFT", "weight": 0.5}]}),
    ("jpm_earnings", {"ticker": "NVDA"}),
    ("blackrock_builder", {"details": {"age": 34, "risk_tolerance": "aggressive"}}),
    ("harvard_dividend", {"investment_amount": 1000000}),
    ("bain_competitive", {"sector": "semiconductors"}),
    ("renaissance_pattern", {"ticker": "AMD"}),
    ("mckinsey_macro", {"biggest_concern": "inflation"})
]

def run_test():
    results = {}
    for report_id, payload in REPORTS:
        print(f"--- Testing {report_id} ---")
        try:
            start_time = time.time()
            resp = requests.post(
                f"{BASE_URL}/{report_id}",
                json={"payload": payload, "owner_key": OWNER_KEY},
                timeout=120
            )
            duration = time.time() - start_time
            if resp.status_code == 200:
                data = resp.json()
                print(f"SUCCESS: {data.get('title')} ({duration:.2f}s)")
                results[report_id] = "OK"
            else:
                print(f"FAILED: {resp.status_code} - {resp.text[:200]}")
                results[report_id] = f"ERROR {resp.status_code}"
        except Exception as e:
            print(f"EXCEPTION: {str(e)}")
            results[report_id] = "TIMEOUT/EXCEPTION"
        print("\n")
        time.sleep(0.5)
    
    print("\n--- Summary ---")
    for r, status in results.items():
        print(f"{r:25}: {status}")

if __name__ == "__main__":
    run_test()
