import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from intervals_api import upload_to_intervals

def bulk_upload():
    api_key = "8yeez3v4p8i11ld1pdnvx3ur"
    athlete_id = "308429"
    default_hour = "08:00:00"
    
    workouts = [
        # 2026-06-14
        {
            "date": "2026-06-14",
            "sport": "Ride",
            "name": "Rodaje Regenerativo (Bici)",
            "description": "Warmup\n- 10m Z1\n\nMain Set\n- 1h10m Z1 (Molinillo)\n\nCooldown\n- 10m Z1",
            "category": "WORKOUT"
        },
        # 2026-06-15
        {
            "date": "2026-06-15",
            "sport": "Swim",
            "name": "Recuperación Activa",
            "description": "Warmup\n- 400m Z1\n\nMain Set\n- 1900m Z1/Z2 Nado suave regenerativo\n\nCooldown\n- 200m Z1",
            "category": "WORKOUT"
        },
        # 2026-06-16
        {
            "date": "2026-06-16",
            "sport": "Ride",
            "name": "Rodaje Ágil Z2",
            "description": "Warmup\n- 15m Z1\n\nMain Set\n- 50m Z2 (Mantener cadencia > 95 rpm)\n\nCooldown\n- 10m Z1",
            "category": "WORKOUT"
        },
        {
            "date": "2026-06-16",
            "sport": "WeightTraining",
            "name": "Sesión Movilidad",
            "description": "- 30m\n\nMovilidad General:\n- Movilidad de cadera\n- Estiramientos dinámicos\n- Flexibilidad y propiocepción",
            "category": "WORKOUT"
        },
        # 2026-06-17
        {
            "date": "2026-06-17",
            "sport": "Swim",
            "name": "Aeróbico Medio",
            "description": "Warmup\n- 400m Z1\n- 200m Técnica\n\nMain Set\n- 1700m Z2 Aeróbico medio constante\n\nCooldown\n- 200m Z1",
            "category": "WORKOUT"
        },
        {
            "date": "2026-06-17",
            "sport": "Run",
            "name": "Rodaje Z2",
            "description": "Warmup\n- 10m Z1 Pace\n\nMain Set\n- 30m Z2 Pace\n\nCooldown\n- 5m Z1 Pace",
            "category": "WORKOUT"
        },
        # 2026-06-18
        {
            "date": "2026-06-18",
            "sport": "Ride",
            "name": "Rodaje Post-Viaje (Molinillo)",
            "description": "Warmup\n- 5m Z1\n\nMain Set\n- 25m Z1 (Molinillo, soltar piernas)\n\nCooldown\n- 5m Z1",
            "category": "WORKOUT"
        },
        # 2026-06-19
        {
            "date": "2026-06-19",
            "sport": "Ride",
            "name": "Paseo Libre (Pre-Competición)",
            "description": "- 30m\n\nPaseo libre suave pre-competición para verificar que la bicicleta funciona perfectamente.",
            "category": "WORKOUT"
        },
        # 2026-06-20
        {
            "date": "2026-06-20",
            "sport": "Ride",
            "name": "QUEBRANTAHUESOS (Objetivo: Paseo y Fondo)",
            "description": "QUEBRANTAHUESOS\nObjetivo: Paseo y Fondo.\nDisfrutar de la marcha cicloturista sin presiones, manteniendo el ritmo controlado.",
            "category": "RACE_A"
        }
    ]
    
    print(f"Iniciando subida masiva de {len(workouts)} entrenamientos a tu cuenta ({athlete_id})...\n")
    
    success_count = 0
    fail_count = 0
    
    for idx, w in enumerate(workouts, 1):
        iso_date = f"{w['date']}T{default_hour}"
        payload = {
            "start_date_local": iso_date,
            "type": w["sport"],
            "category": w["category"],
            "name": w["name"],
            "workout_text": w["description"]
        }
        
        print(f"[{idx}/{len(workouts)}] Subiendo {w['date']} - {w['name']} ({w['sport']})...")
        success, msg = upload_to_intervals(
            athlete_id=athlete_id,
            api_key=api_key,
            payload=payload,
            use_athlete_key=True
        )
        
        if success:
            print("  -> ¡ÉXITO!")
            success_count += 1
        else:
            print(f"  -> ERROR: {msg}")
            fail_count += 1
            
        time.sleep(0.5)
        
    print("\n--- RESUMEN ---")
    print(f"Subidas exitosas: {success_count}")
    print(f"Subidas fallidas: {fail_count}")

if __name__ == "__main__":
    bulk_upload()
