import requests
import json

api_key = "AIzaSyCjzN7sIx0WQ1W6Usyp4k0yR6qSA4T1Bz0"
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    res = requests.get(url)
    print(f"Status: {res.status_code}")
    data = res.json()
    if 'models' in data:
        for m in data['models']:
            if 'generateContent' in m['supportedGenerationMethods']:
                print(f"MODELO DISPONIBLE: {m['name']}")
    else:
        print(f"Respuesta sin modelos: {data}")
except Exception as e:
    print(f"Error: {e}")
