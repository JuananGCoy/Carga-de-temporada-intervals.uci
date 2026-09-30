import requests
import json

def test_api():
    coach_api_key = "8yeez3v4p8i11ld1pdnvx3ur"
    
    url = "https://intervals.icu/api/v1/athletes"
    headers = {
        "Accept": "application/json",
        "User-Agent": "TriathlonUploader/1.0"
    }
    
    print("--- DIAGNÓSTICO DE LISTA DE DEPORTISTAS ---")
    try:
        r = requests.get(url, auth=("API_KEY", coach_api_key), headers=headers, timeout=10)
        print(f"Status Code: {r.status_code}")
        if r.status_code == 200:
            athletes = r.json()
            print(f"Número de deportistas encontrados: {len(athletes)}")
            for idx, a in enumerate(athletes):
                print(f"\nDeportista {idx+1}:")
                # Imprimir todos los datos disponibles
                for k, v in a.items():
                    print(f"  {k}: {v}")
        else:
            print(f"Response Error: {r.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
