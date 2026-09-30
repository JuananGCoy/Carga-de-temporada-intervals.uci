import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from intervals_api import upload_to_intervals

def upload_note():
    api_key = "8yeez3v4p8i11ld1pdnvx3ur"
    athlete_id = "308429"
    default_hour = "08:00:00"
    
    payload = {
        "start_date_local": f"2026-06-15T{default_hour}",
        "type": "Run",
        "category": "NOTE",
        "name": "Carrera: Descanso",
        "workout_text": "Descanso Total"
    }
    
    print(f"Subiendo Nota de Descanso para el 2026-06-15...")
    success, msg = upload_to_intervals(
        athlete_id=athlete_id,
        api_key=api_key,
        payload=payload,
        use_athlete_key=True
    )
    
    if success:
        print("¡Éxito! Nota de descanso subida correctamente.")
    else:
        print(f"Error al subir: {msg}")

if __name__ == "__main__":
    upload_note()
