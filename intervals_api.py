import requests
import json

def format_athlete_id(athlete_id, is_coach=False):
    """
    Formatea el ID de atleta para Intervals.icu.
    - Si es el propio entrenador/dueño de la clave API, se puede usar "0".
    - Para deportistas tutorizados, Intervals.icu exige el prefijo 'i' (ej. i599534).
    """
    clean_id = "0" if is_coach else str(athlete_id).strip()
    if not clean_id or clean_id == "":
        clean_id = "0"
    if clean_id != "0" and not clean_id.lower().startswith("i"):
        clean_id = f"i{clean_id}"
    return clean_id

def _request_intervals(method, endpoint, api_key, params=None, json_data=None, timeout=15):
    """
    Realiza una petición HTTP a la API de Intervals.icu manejando Basic Auth y fallback a Bearer Token.
    """
    clean_key = str(api_key).strip()
    url = f"https://intervals.icu/api/v1{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "TriathlonCoachDashboard/1.0"
    }

    try:
        # MÉTODO 1: Basic Auth
        response = requests.request(
            method=method,
            url=url,
            params=params,
            json=json_data,
            auth=('API_KEY', clean_key),
            headers=headers,
            timeout=timeout
        )
        # MÉTODO 2: Bearer Token si falla con 403
        if response.status_code == 403:
            bearer_headers = headers.copy()
            bearer_headers["Authorization"] = f"Bearer {clean_key}"
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=bearer_headers,
                timeout=timeout
            )
        return response
    except Exception as e:
        raise e

def upload_to_intervals(athlete_id, api_key, payload, use_athlete_key=True):
    """
    Sube el entrenamiento a Intervals.icu usando la API oficial.
    """
    clean_id = format_athlete_id(athlete_id, is_coach=use_athlete_key)
    endpoint = f"/athlete/{clean_id}/events"
    
    data = {
        "start_date_local": payload.get("start_date_local"),
        "type": payload.get("type", "Swim"),
        "name": payload.get("name", "Entrenamiento"),
        "description": payload.get("workout_text", ""), 
        "category": payload.get("category", "WORKOUT")
    }

    try:
        response = _request_intervals("POST", endpoint, api_key, json_data=data)
        if response.status_code in [200, 201]:
            return True, "¡Éxito!"
        if response.status_code == 403:
            return False, (
                "Error 403 (No autorizado). Por favor, comprueba lo siguiente:\n"
                "1. Ve a Intervals.icu > Settings > API Key.\n"
                "2. Asegúrate de que las casillas de 'Write' (Escritura) estén marcadas.\n"
                "3. Verifica que tu Athlete ID sea correcto."
            )
        return False, f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return False, f"Fallo de conexión: {str(e)}"

def get_athlete_activities(athlete_id, api_key, oldest, newest, is_coach=False):
    """
    Obtiene las actividades realizadas de un deportista entre las fechas oldest y newest (YYYY-MM-DD).
    """
    clean_id = format_athlete_id(athlete_id, is_coach=is_coach)
    endpoint = f"/athlete/{clean_id}/activities"
    params = {"oldest": oldest, "newest": newest}
    
    try:
        response = _request_intervals("GET", endpoint, api_key, params=params)
        if response.status_code == 200:
            return True, response.json()
        return False, f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return False, f"Fallo de conexión: {str(e)}"

def get_athlete_wellness(athlete_id, api_key, oldest, newest, is_coach=False):
    """
    Obtiene el registro de wellness, fatiga (ATL), forma (TSB), fitness (CTL) y recuperación.
    """
    clean_id = format_athlete_id(athlete_id, is_coach=is_coach)
    endpoint = f"/athlete/{clean_id}/wellness"
    params = {"oldest": oldest, "newest": newest}
    
    try:
        response = _request_intervals("GET", endpoint, api_key, params=params)
        if response.status_code == 200:
            return True, response.json()
        return False, f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return False, f"Fallo de conexión: {str(e)}"

def get_athlete_profile(athlete_id, api_key, is_coach=False):
    """
    Obtiene los datos de perfil del atleta (FTP, peso, ritmo cardíaco basal, etc.).
    """
    clean_id = format_athlete_id(athlete_id, is_coach=is_coach)
    endpoint = f"/athlete/{clean_id}"
    
    try:
        response = _request_intervals("GET", endpoint, api_key)
        if response.status_code == 200:
            return True, response.json()
        return False, f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return False, f"Fallo de conexión: {str(e)}"

def get_athlete_events(athlete_id, api_key, oldest, newest, is_coach=False):
    """
    Obtiene los eventos (entrenamientos planificados, notas, competiciones) del calendario.
    """
    clean_id = format_athlete_id(athlete_id, is_coach=is_coach)
    endpoint = f"/athlete/{clean_id}/events"
    params = {"oldest": oldest, "newest": newest}
    
    try:
        response = _request_intervals("GET", endpoint, api_key, params=params)
        if response.status_code == 200:
            return True, response.json()
        return False, f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return False, f"Fallo de conexión: {str(e)}"
