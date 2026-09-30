import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from intervals_api import upload_to_intervals

def upload_notes():
    coach_api_key = "8yeez3v4p8i11ld1pdnvx3ur"
    athletes = [
        {"name": "Manuel Esparcia Gómez", "id": "599534"},
        {"name": "Jesús Ruiz", "id": "602664"}
    ]
    
    # 17 semanas de planificación
    weekly_notes = [
        {
            "date": "2026-06-08",
            "title": "Semana 1 · Objetivo: Romper el hielo tras el parón",
            "body": "Objetivo: Romper el hielo tras el parón.\n\nLógica: El fartlek del lunes y el progresivo del miércoles buscan activar tus sistemas cardiovascular y muscular sin el estrés psicológico de ritmos fijos. La tirada larga se queda en un suspiro (50 min totales) para evaluar cómo reaccionan tus tendones al impacto."
        },
        {
            "date": "2026-06-15",
            "title": "Semana 2 · Objetivo: Introducir la Zona 4 de forma fraccionada",
            "body": "Objetivo: Introducir la Zona 4 (Umbral) de forma fraccionada y jugada.\n\nLógica: En el fartlek del miércoles metemos 15 minutos acumulados en Z4, pero con recuperaciones en Z2 (trote activo). No te dejamos parar para empezar a trabajar la eficiencia metabólica. La tirada larga sube ligeramente a 1h 00m totales."
        },
        {
            "date": "2026-06-22",
            "title": "Semana 3 · Objetivo: Asimilar el impacto de las dos primeras semanas",
            "body": "Objetivo: Asimilar el impacto de las dos primeras semanas.\n\nLógica: Semana de impacto reducido. No hay ritmos exigentes, solo rodajes alegres cortos y un juego de ritmos muy suave el miércoles. Es vital para que tu estructura ósea y muscular repare tejidos antes de empezar el bloque duro."
        },
        {
            "date": "2026-06-29",
            "title": "Semana 4 · Objetivo: Subir un escalón la intensidad aeróbica",
            "body": "Objetivo: Subir un escalón la intensidad aeróbica y extender la tirada larga.\n\nLógica: Entramos en el Fartlek en Escalón, combinando Z3 y Z4 consecutivas para enseñarle al cuerpo a reciclar lactato a ritmos vivos. La tirada larga del sábado toca ya la 1h 05m con un bloque final exigente en Z3 para simular el final de una carrera."
        },
        {
            "date": "2026-07-06",
            "title": "Semana 5 · Objetivo: Maximizar el volumen aeróbico",
            "body": "Objetivo: Maximizar el volumen aeróbico del primer bloque.\n\nLógica: El miércoles jugamos con una pirámide invertida para tocar ritmos rápidos con menos fatiga. El sábado hacemos la tirada larga más extensa de la base (1h 10m totales) con los últimos 10 minutos en Z3 para trabajar la fatiga acumulada."
        },
        {
            "date": "2026-07-13",
            "title": "Semana 6 · Objetivo: Resetear el organismo para ritmos de carrera",
            "body": "Objetivo: Resetear el organismo y preparar las piernas para los ritmos de carrera.\n\nLógica: Segunda descarga del plan. Bajamos drásticamente el tiempo de entrenamiento. El miércoles es un juego de ritmos muy controlado. Llegarás al domingo con ganas de comerte el asfalto."
        },
        {
            "date": "2026-07-20",
            "title": "Semana 7 · Objetivo: Densidad en Zona 4 (Umbral Lactato)",
            "body": "Objetivo: Densidad en Zona 4 (Umbral Lactato).\n\nLógica: Entramos oficialmente en la fase de Construcción. El fartlek del miércoles ya exige bloques de 4 minutos seguidos en Z4. La tirada larga sube a 1h 10m metiendo calidad intermedia."
        },
        {
            "date": "2026-07-27",
            "title": "Semana 8 · Objetivo: Ampliar el tiempo límite corriendo a ritmo umbral",
            "body": "Objetivo: Ampliar el tiempo límite corriendo a ritmo umbral.\n\nLógica: Pasamos a bloques de 6 minutos en Z4 el miércoles (18 minutos totales de la sesión en zona crítica). El sábado la tirada larga estira el cuerpo hasta la 1h 25m totales combinando Z2 y Z3."
        },
        {
            "date": "2026-08-03",
            "title": "Semana 9 · Objetivo: Calibrar tu ritmo real bajo presión competitiva",
            "body": "Objetivo: Calibrar tu ritmo real bajo presión competitiva.\n\nLógica: Semana de descarga en los días previos para limpiar piernas. El domingo compites en una carrera popular de 10k a tope (Z4 alta). Este test nos dará los ritmos exactos para el tramo final de cara a Albacete."
        },
        {
            "date": "2026-08-10",
            "title": "Semana 10 · Objetivo: Elevación del Techo (VO2máx)",
            "body": "Objetivo: Elevación del Techo (VO2máx).\n\nLógica: El miércoles metemos el entrenamiento más agónico: fartlek en Z5 (VO2máx). Bloques cortos de 2 minutos donde el corazón sube a mil, seguidos de recuperaciones generosas. Esto hace que tu ritmo de 4:15 min/km parezca 'fácil' en comparación."
        },
        {
            "date": "2026-08-17",
            "title": "Semana 11 · Objetivo: Automatizar mecánicamente el ritmo de la Media Maratón",
            "body": "Objetivo: Automatizar mecánicamente el ritmo de la Media Maratón (Z3 alta).\n\nLógica: El miércoles nos olvidamos de la agonía y nos centramos en el ritmo específico: bloques largos de 8 minutos en Z3. El sábado, la tirada larga se vuelve un reto mental combinando dos bloques de 35 minutos de carrera con ritmos variables."
        },
        {
            "date": "2026-08-24",
            "title": "Semana 12 · Objetivo: Soportar la máxima fatiga de toda la preparación",
            "body": "Objetivo: Soportar la máxima fatiga de toda la preparación.\n\nLógica: El miércoles realizas un fartlek exigente de 2x12 minutos en Z4. El sábado ejecutas la tirada larga cumbre de la temporada: 1h 35m totales, finalizando con 15 minutos exigentes en Z3. Aquí se forja la resistencia para el día de la carrera."
        },
        {
            "date": "2026-08-31",
            "title": "Semana 13 · Objetivo: Absorber el impacto de la semana 12",
            "body": "Objetivo: Absorber el impacto del pico de volumen de la semana 12.\n\nLógica: Rodajes cortos, fartlek muy suave de solo 4 cambios el miércoles y tirada larga reducida a 1h 05m totales. Tus piernas asimilarán todo el entrenamiento de agosto aquí."
        },
        {
            "date": "2026-09-07",
            "title": "Semana 14 · Objetivo: Ensayo general de ritmos y estrategia",
            "body": "Objetivo: Ensayo general de ritmos y estrategia.\n\nLógica: El miércoles haces bloques específicos a ritmo objetivo (Z3). El domingo realizas un segundo test de 10k en carrera popular para terminar de pulir sensaciones competitivas y comprobar la ganancia aeróbica."
        },
        {
            "date": "2026-09-14",
            "title": "Semana 15 · Objetivo: Inicio del Tapering (-25%)",
            "body": "Objetivo: Inicio del Tapering (-25%).\n\nLógica: Reducimos la duración de los rodajes un 25% para eliminar la fatiga acumulada, pero el miércoles seguimos recordando el ritmo rápido con un fartlek de 4x3 minutos en Z4. Mantienes la chispa pero descansas."
        },
        {
            "date": "2026-09-21",
            "title": "Semana 16 · Objetivo: Provocar la supercompensación total del cuerpo",
            "body": "Objetivo: Provocar la supercompensación total del cuerpo.\n\nLógica: Caída drástica del volumen. Los rodajes son casi testimoniales (30-35 minutos). El miércoles solo hacemos un breve recordatorio de 3x3 minutos a ritmo de carrera. Notarás las piernas increíblemente ligeras y con una respuesta nerviosa óptima."
        },
        {
            "date": "2026-09-28",
            "title": "Semana 17 · Objetivo: Llegar al 100% de frescura y clavar la estrategia",
            "body": "Objetivo: Llegar al 100% de frescura y clavar la estrategia en Albacete.\n\nLógica: Lunes rodaje suave de soltura, miércoles un estímulo mínimo para activar el sistema neuromuscular y viernes descanso total. El domingo sales a por esa 1h 30min con los depósitos llenos y las piernas completamente descansadas."
        }
    ]
    
    total_uploads = len(weekly_notes) * len(athletes)
    print(f"Iniciando subida masiva de {total_uploads} notas semanales...\n")
    
    success_count = 0
    fail_count = 0
    
    for athlete in athletes:
        print(f"\n>>> Subiendo notas para {athlete['name']} (ID: {athlete['id']}) <<<")
        for idx, note in enumerate(weekly_notes, 1):
            iso_date = f"{note['date']}T08:00:00"
            payload = {
                "start_date_local": iso_date,
                "type": "Workout",
                "category": "NOTE",
                "name": note["title"],
                "workout_text": note["body"]
            }
            
            print(f"[{idx}/{len(weekly_notes)}] Subiendo {note['date']} - {note['title']}...")
            # use_athlete_key=False porque es a un deportista entrenado usando clave del coach
            success, msg = upload_to_intervals(
                athlete_id=athlete["id"],
                api_key=coach_api_key,
                payload=payload,
                use_athlete_key=False
            )
            
            if success:
                print("  -> ¡ÉXITO!")
                success_count += 1
            else:
                print(f"  -> ERROR: {msg}")
                fail_count += 1
                
            time.sleep(0.5)
            
    print("\n--- RESUMEN ---")
    print(f"Subidas exitosas: {success_count} de {total_uploads}")
    print(f"Subidas fallidas: {fail_count}")

if __name__ == "__main__":
    upload_notes()
