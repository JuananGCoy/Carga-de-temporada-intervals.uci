import requests
import json

def list_athletes():
    coach_api_key = "8yeez3v4p8i11ld1pdnvx3ur"
    url = "https://intervals.icu/api/v1/athletes"
    headers = {
        "Accept": "application/json",
        "User-Agent": "TriathlonUploader/1.0"
    }
    try:
        r = requests.get(url, auth=("API_KEY", coach_api_key), headers=headers, timeout=10)
        if r.status_code == 200:
            athletes = r.json()
            print("--- ATLETAS VINCULADOS EN LA API ---")
            for idx, a in enumerate(athletes):
                print(f"{idx+1}. Name: {a.get('name')} | ID: {a.get('id')}")
        else:
            print("Error retrieving athletes:", r.text)
    except Exception as e:
        print("Exception:", e)

if __name__ == "__main__":
    list_athletes()
