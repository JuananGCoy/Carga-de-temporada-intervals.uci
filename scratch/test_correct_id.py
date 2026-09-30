import requests
import json

def test_correct_id():
    coach_api_key = "8yeez3v4p8i11ld1pdnvx3ur"
    correct_athlete_id = "599534"
    
    urls = [
        f"https://intervals.icu/api/v1/athlete/{correct_athlete_id}/events",
        f"https://intervals.icu/api/v1/athlete/i{correct_athlete_id}/events"
    ]
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "TriathlonUploader/1.0",
        "Content-Type": "application/json"
    }
    
    post_data = {
        "start_date_local": "2026-06-08T08:00:00",
        "type": "Ride",
        "name": "Test Coach API (Typo Fix)",
        "description": "Warmup\n- 10m Z1\nMain Set\n- 5m Z2",
        "category": "WORKOUT"
    }
    
    for url in urls:
        print(f"\nTesting POST to: {url}")
        try:
            r = requests.post(url, json=post_data, auth=("API_KEY", coach_api_key), headers=headers, timeout=10)
            print(f"Status Code: {r.status_code}")
            print(f"Response: {r.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_correct_id()
