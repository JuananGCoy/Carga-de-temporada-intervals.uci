import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from intervals_api import upload_to_intervals

def bulk_upload():
    api_key = "8yeez3v4p8i11ld1pdnvx3ur"
    athlete_id = "308429"
    default_hour = "08:00:00"
    
    # Lista de entrenamientos estructurados
    workouts = [
        # 2026-06-25
        {
            "date": "2026-06-25",
            "sport": "Ride",
            "name": "Rodaje con Aceleraciones",
            "description": "Warmup\n- 15m Z1\n\nMain Set\n- 45m Z2\n5x\n  - 10s Z4\n  - 2m Z2\n\nCooldown\n- 10m Z1",
            "category": "WORKOUT"
        },
        {
            "date": "2026-06-25",
            "sport": "WeightTraining",
            "name": "Mantenimiento Tren Inferior",
            "description": "- 45m\n\nTren inferior muy ligero:\n- Sentadillas muy ligeras (sin peso)\n- Zancadas libres\n- Elevación de talones\n- Core: Planchas y lumbar",
            "category": "WORKOUT"
        },
        # 2026-06-26
        {
            "date": "2026-06-26",
            "sport": "Swim",
            "name": "Series Cortas",
            "description": "Warmup\n- 400m Z1\n\nMain Set\n- 400m Técnica (crol/palas)\n10x\n  - 50m Z3 r: 15s\n- 1000m Z2 Continuo cómodo\n\nCooldown\n- 200m Z1",
            "category": "WORKOUT"
        },
        {
            "date": "2026-06-26",
            "sport": "Run",
            "name": "Rodaje y Progresivos",
            "description": "Warmup\n- 10m Z1 Pace\n\nMain Set\n- 25m Z2 Pace\n4x\n  - 100m Z4 Pace (Progresivos)\n  - 1m Z1 Pace",
            "category": "WORKOUT"
        },
        # 2026-06-27
        {
            "date": "2026-06-27",
            "sport": "Ride",
            "name": "Rodaje Aeróbico Z2",
            "description": "Warmup\n- 15m Z1\n\nMain Set\n- 1h35m Z2\n\nCooldown\n- 10m Z1",
            "category": "WORKOUT"
        },
        # 2026-06-28
        {
            "date": "2026-06-28",
            "sport": "Run",
            "name": "Carrera Larga",
            "description": "Warmup\n- 10m Z1 Pace\n\nMain Set\n- 35m Z2 Pace fluido\n\nCooldown\n- 5m Z1 Pace",
            "category": "WORKOUT"
        },
        # 2026-06-29
        {
            "date": "2026-06-29",
            "sport": "Swim",
            "name": "Bloque Umbral / CSS",
            "description": "Warmup\n- 500m Z1\n- 300m Técnica\n\nMain Set\n15x\n  - 100m Z3 r: 20s\n- 500m Z2 Pullbuoy\n\nCooldown\n- 200m Z1",
            "category": "WORKOUT"
        },
        {
            "date": "2026-06-29",
            "sport": "Run",
            "name": "Series de Ritmo 3k",
            "description": "Warmup\n- 15m Z1 Pace\n\nMain Set\n8x\n  - 1m Z5 Pace (Ritmo 3k)\n  - 1m Z1 Pace (Recuperación)\n\nCooldown\n- 14m Z1 Pace",
            "category": "WORKOUT"
        },
        # 2026-06-30
        {
            "date": "2026-06-30",
            "sport": "Ride",
            "name": "Series VO2Max (Z5)",
            "description": "Warmup\n- 20m Z1\n\nMain Set\n5x\n  - 3m Z5 (VO2Max)\n  - 3m Z1 (Recuperación)\n\nCooldown\n- 40m Z2",
            "category": "WORKOUT"
        },
        {
            "date": "2026-06-30",
            "sport": "WeightTraining",
            "name": "Potencia y Core",
            "description": "- 40m\n\nFuerza explosiva:\n- Saltos al cajón\n- Sentadillas con salto ligero\n- Zancadas explosivas\n- Core: Rueda abdominal y planchas dinámicas",
            "category": "WORKOUT"
        },
        # 2026-07-01
        {
            "date": "2026-07-01",
            "sport": "Swim",
            "name": "Ritmo Sprint",
            "description": "Warmup\n- 400m Z1\n- 200m Estilos\n\nMain Set\n- 4x 100m Z3 r: 15s\n- 8x 50m Z4 r: 20s\n- 1000m Z2\n\nCooldown\n- 200m Z1",
            "category": "WORKOUT"
        },
        {
            "date": "2026-07-01",
            "sport": "Run",
            "name": "Series de Ritmo de Carrera",
            "description": "Warmup\n- 15m Z1 Pace\n\nMain Set\n3x\n  - 5m Z4 Pace (Ritmo carrera)\n  - 90s Z1 Pace\n\nCooldown\n- 15m30s Z1 Pace",
            "category": "WORKOUT"
        },
        # 2026-07-02
        {
            "date": "2026-07-02",
            "sport": "Ride",
            "name": "Rodaje Regenerativo",
            "description": "Warmup\n- 10m Z1\n\nMain Set\n- 55m Z1 (Molinillo)\n\nCooldown\n- 10m Z1",
            "category": "WORKOUT"
        },
        {
            "date": "2026-07-02",
            "sport": "WeightTraining",
            "name": "Movilidad y Propiocepción",
            "description": "- 30m\n\nTrabajo de tobillo:\n- Equilibrio sobre bosu/fitball\n- Movilidad articular de tobillo\n- Fortalecimiento de tendones",
            "category": "WORKOUT"
        },
        # 2026-07-03
        {
            "date": "2026-07-03",
            "sport": "Swim",
            "name": "Técnica y Continuo",
            "description": "Warmup\n- 300m Z1\n- 200m Técnica\n\nMain Set\n- 1300m Z2 continuo cómodo\n\nCooldown\n- 200m Z1",
            "category": "WORKOUT"
        },
        {
            "date": "2026-07-03",
            "sport": "Run",
            "name": "Rodaje Suave",
            "description": "Warmup\n- 5m Z1 Pace\n\nMain Set\n- 20m Z1/Z2 Pace suave\n\nCooldown\n- 5m Z1 Pace",
            "category": "WORKOUT"
        },
        # 2026-07-04
        {
            "date": "2026-07-04",
            "sport": "Ride",
            "name": "Bloque de Transición (Bici)",
            "description": "Warmup\n- 25m Z1\n\nMain Set\n3x\n  - 5m Z4 (Vatios carrera)\n  - 3m Z1\n\nCooldown\n- 41m Z2",
            "category": "WORKOUT"
        },
        {
            "date": "2026-07-04",
            "sport": "Run",
            "name": "Bloque de Transición (Carrera)",
            "description": "Warmup\n- 2m Z1 Pace\n\nMain Set\n- 11m Z4 Pace (Ritmo Sprint)\n\nCooldown\n- 2m Z1 Pace",
            "category": "WORKOUT"
        },
        # 2026-07-05
        {
            "date": "2026-07-05",
            "sport": "Ride",
            "name": "Rodaje Z2 Fluido",
            "description": "Warmup\n- 15m Z1\n\nMain Set\n- 1h05m Z2 cómodo\n\nCooldown\n- 10m Z1",
            "category": "WORKOUT"
        },
        # 2026-07-06
        {
            "date": "2026-07-06",
            "sport": "Swim",
            "name": "Recuperación Activa",
            "description": "Warmup\n- 400m Z1\n\nMain Set\n- 1400m Z1/Z2 muy suave con aletas\n\nCooldown\n- 200m Z1",
            "category": "WORKOUT"
        },
        {
            "date": "2026-07-06",
            "sport": "Run",
            "name": "Rodaje Suave Z1/Z2",
            "description": "Warmup\n- 10m Z1 Pace\n\nMain Set\n- 20m Z1/Z2 Pace\n\nCooldown\n- 5m Z1 Pace",
            "category": "WORKOUT"
        },
        # 2026-07-07
        {
            "date": "2026-07-07",
            "sport": "Ride",
            "name": "Rodaje con Ritmo de Carrera",
            "description": "Warmup\n- 15m Z1\n\nMain Set\n4x\n  - 2m Z4 (Vatios de carrera)\n  - 2m Z1\n\nCooldown\n- 29m Z2",
            "category": "WORKOUT"
        },
        # 2026-07-08
        {
            "date": "2026-07-08",
            "sport": "Swim",
            "name": "Activación",
            "description": "Warmup\n- 300m Z1\n- 200m Técnica\n\nMain Set\n6x\n  - 50m Z4 r: 20s (Progresivos)\n- 500m Z2\n\nCooldown\n- 200m Z1",
            "category": "WORKOUT"
        },
        {
            "date": "2026-07-08",
            "sport": "Run",
            "name": "Activación",
            "description": "Warmup\n- 10m Z1 Pace\n\nMain Set\n- 15m Z2 Pace\n4x\n  - 100m Z4 Pace (Rectas)\n  - 1m Z1 Pace",
            "category": "WORKOUT"
        },
        # 2026-07-09
        {
            "date": "2026-07-09",
            "sport": "Ride",
            "name": "Rodaje Regenerativo Corto",
            "description": "Warmup\n- 5m Z1\n\nMain Set\n- 20m Z1 (Molinillo)\n\nCooldown\n- 5m Z1",
            "category": "WORKOUT"
        },
        # 2026-07-10
        {
            "date": "2026-07-10",
            "sport": "Run",
            "name": "Activación Pre-competición",
            "description": "Warmup\n- 5m Z1 Pace\n\nMain Set\n- 6m Z1 Pace\n3x\n  - 10s Z5 Pace (Arrancadas)\n  - 1m Z1 Pace",
            "category": "WORKOUT"
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
        # Al ser tu propia cuenta (mismo ID del API Key), use_athlete_key=True es obligatorio para evitar 403
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
            
        time.sleep(0.5)  # Evitar saturar la API
        
    print("\n--- RESUMEN ---")
    print(f"Subidas exitosas: {success_count}")
    print(f"Subidas fallidas: {fail_count}")

if __name__ == "__main__":
    bulk_upload()
