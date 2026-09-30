import requests
import json
import time

def get_gemini_client(api_key):
    """Necesario para que app.py no falle al importar."""
    return api_key

def process_workout_text(api_key, sport_type, entrenamiento_text, principal_text="", retries=3):
    """
    Usa la IA de Gemini para transformar el texto de entrenamiento en un formato
    técnico que Intervals.icu pueda parsear nativamente.
    """
    clean_key = str(api_key).strip()
    
    if sport_type == "WeightTraining":
        prompt = f"""
        Transforma el siguiente texto de entrenamiento al formato técnico de Intervals.icu para GIMNASIO / FUERZA.
        Reglas estrictas para GIMNASIO:
        1. NO uses zonas de intensidad (Z1, Z2, etc.).
        2. El formato debe ser un único bloque de tiempo total. Por defecto, asigna "- 40m" como tiempo total si no se especifica.
        3. Debajo del tiempo, añade el desglose de los ejercicios como texto libre o en formato viñetas.
        
        Ejemplo:
        - 40m
        
        Mantenimiento y Core:
        - Planchas
        - Abdominales
        - Sentadillas
        
        Texto a transformar: {entrenamiento_text} {principal_text}
        
        Devuelve ÚNICAMENTE el texto formateado, sin markdown (```), sin preámbulos.
        """
    elif sport_type == "Swim":
        prompt = f"""
        Eres un entrenador de natación para triatlón. Transforma el siguiente texto en una sesión de natación detallada.
        Reglas para NATACIÓN:
        1. Si el texto original solo especifica una distancia total (ej. "Natación (2600m): Recuperamos la sesión..."), DEBES INVENTAR un entrenamiento estructurado y equilibrado que sume EXACTAMENTE esa distancia total.
        2. Divide la sesión en: Calentamiento, Técnica, Principal, Secundario (opcional) y Enfriamiento.
        3. MUY IMPORTANTE: Sé creativo y varía los entrenamientos. No pongas siempre lo mismo. Cambia los ejercicios de técnica (remadas, punto muerto, un brazo, crol waterpolo, etc.), varía el uso de material (aletas, pullbuoy, palas, tabla) y adapta la intensidad al objetivo del texto original (si pone "recuperar" hazlo suave, si no pone nada, pon algo equilibrado).
        4. El formato debe ser de lectura humana para apuntar en un papel, usando viñetas (•) y distancias en metros (m).
        5. Opcionalmente puedes sugerir zonas de esfuerzo (Z2, Z3) o descansos (r: 20") dentro del texto, pero sin formato técnico estricto de máquina.
        
        Ejemplo de formato esperado:
        • Calentamiento: 400m (100 Estilos / 100 Crol / 100 Estilos / 100 Crol).
        • Técnica: 4 x 50m (25m punto muerto / 25m nado completo).
        • Principal: 6 x 200m en Z2 (ritmo cómodo, constante) r: 20".
        • Secundario: 4 x 150m en Z3 (ritmo medio-alto) r: 30".
        • Enfriamiento: 200m muy suaves.
          
        Texto a transformar: {entrenamiento_text} {principal_text}
        
        Devuelve ÚNICAMENTE el texto formateado, sin markdown (```), sin preámbulos.
        """
    else:
        pace_rule = " Debes añadir SIEMPRE la palabra \"Pace\" a continuación de la zona (ejemplo: Z1 Pace, Z3 Pace)." if sport_type == "Run" else ""
        ejemplo_pace = " Pace" if sport_type == "Run" else ""
        
        prompt = f"""
        Transforma el siguiente texto de entrenamiento al formato técnico exacto de Intervals.icu.
        Reglas de formato:
        1. Usa bloques como "Warmup", "Main Set", "Cooldown".
        2. Las líneas de paso deben empezar por "- ".
        3. Para repeticiones usa "4x" (sin guion delante) y CRÍTICO: los pasos debajo de las repeticiones NO DEBEN TENER ESPACIOS AL INICIO. Deben empezar directamente con "- ".
        4. Usa duraciones válidas como 'm' (minutos), 's' (segundos), 'h' (horas), 'km'. IMPORTANTE: 'm' significa MINUTOS. Si el texto original indica una distancia en metros (ej. 100 metros o 100m), OBLIGATORIAMENTE debes convertirla a kilómetros (ej. 0.1km). ¡NUNCA uses 'm' para referirte a metros!
        5. Usa zonas válidas como Z1, Z2, Z3, Z4, Z5, Z6 obligatoriamente en cada paso activo.{pace_rule}
        6. EXCEPCIONES CRÍTICAS:
           - Si es un día de COMPETICIÓN (Ironman, carrera, triatlón, etc.) o Test donde solo hay que competir, NO estructures el entreno. Devuelve simplemente un resumen del texto sin bloques ni pasos técnicos (ejemplo: "MEDIO IRONMAN - Objetivo competir").
           - Si es un día de DESCANSO TOTAL ("Descanso", "Paseo", etc.), NO estructures el entreno. Devuelve simplemente "Descanso Total".
        7. SUMA DE TIEMPOS MUY ESTRICTA: La suma de la duración de TODOS los bloques (Warmup + Main Set + Cooldown) debe cuadrar EXACTAMENTE con el tiempo total de la sesión. NUNCA excedas el tiempo total indicado. Si la sesión es de "30 min trote suave", el total debe sumar 30 minutos (ej. 5m Warmup, 20m Main, 5m Cooldown, o directamente 30m Main Set sin warmup/cooldown).
           
        
        Ejemplo:
        Warmup
        - 15m Z1{ejemplo_pace}
        
        Main Set
        4x
        - 5m Z3{ejemplo_pace}
        - 2m Z1{ejemplo_pace}
          
        Cooldown
        - 10m Z1{ejemplo_pace}
        
        Texto a transformar: {entrenamiento_text} {principal_text}
        
        Devuelve ÚNICAMENTE el texto formateado, sin markdown (```), sin preámbulos, ni despedidas.
        """
        
    # Usar gemini-2.5-flash-lite porque gemini-1.5-flash a veces no está disponible en la versión actual o agota cuotas pronto
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={clean_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        res = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=25)
        if res.status_code == 200:
            output = res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
            # Limpiar posible código markdown alrededor
            if output.startswith("```"):
                output = "\n".join(output.split("\n")[1:-1]).strip()
            return output
        elif res.status_code == 429:
            print(f"ERROR: Rate limit excedido (429). Retries left: {retries}. Esperando 60 segundos...")
            if retries > 0:
                time.sleep(60) # Esperar 60 segundos para asegurar que se resetea la cuota por minuto
                return process_workout_text(api_key, sport_type, entrenamiento_text, principal_text, retries - 1)
            return f"ERROR_AI_FAILED: {res.json().get('error', {}).get('message', 'Rate limit exceeded (429)')}"
        else:
            print(f"Error AI Status {res.status_code}: {res.text}")
            return f"ERROR_AI_FAILED: Status {res.status_code} - {res.json().get('error', {}).get('message', res.text)}"
    except Exception as e:
        print(f"Error AI: {e}")
        return f"ERROR_AI_FAILED: Excepción - {str(e)}"
        
    # FALLBACK: Si falla la IA
    return "ERROR_AI_FAILED"
