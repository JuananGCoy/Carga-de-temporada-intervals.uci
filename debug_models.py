import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print("DEBUG: Iniciando diagnostico...")
if not api_key:
    print("DEBUG: No se encontro API KEY")
else:
    try:
        genai.configure(api_key=api_key)
        print("DEBUG: API configurada. Listando modelos...")
        models = genai.list_models()
        found = False
        for m in models:
            print(f"DEBUG: Encontrado -> {m.name}")
            found = True
        if not found:
            print("DEBUG: No se encontraron modelos asociados a esta clave.")
    except Exception as e:
        print(f"DEBUG: Error -> {str(e)}")
