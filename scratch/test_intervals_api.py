import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("INTERVALS_API_KEY")

def test_intervals():
    url = f"https://intervals.icu/api/v1/athlete/0/events"
    data = {
        "start_date_local": "2024-05-02T08:00:00",
        "type": "Run",
        "name": "Test Race C",
        "description": "Test description",
        "category": "RACE_C"
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    print("Testing RACE_C category...")
    res = requests.post(url, json=data, auth=('API_KEY', api_key), headers=headers)
    print(f"Status: {res.status_code}, Body: {res.text}")

if __name__ == "__main__":
    test_intervals()
