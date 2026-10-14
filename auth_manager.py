import json
import os
import hashlib
import secrets
from datetime import datetime

USERS_FILE = "users.json"
LEGACY_ATHLETES_FILE = "athletes.json"

def _hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Genera hash SHA-256 con salt para máxima seguridad."""
    if not salt:
        salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((salt + password).encode('utf-8'))
    return hash_obj.hexdigest(), salt

def _verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verifica si la contraseña coincide con el hash almacenado."""
    hash_obj = hashlib.sha256((salt + password).encode('utf-8'))
    return hash_obj.hexdigest() == password_hash

def load_users() -> dict:
    """Carga la base de datos de usuarios desde users.json."""
    if not os.path.exists(USERS_FILE):
        return init_users_db()
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
    except Exception as e:
        print(f"Error cargando {USERS_FILE}: {e}")
        return init_users_db()

def save_users(users: dict) -> bool:
    """Guarda la base de datos de usuarios en users.json."""
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error guardando {USERS_FILE}: {e}")
        return False

def init_users_db() -> dict:
    """
    Inicializa users.json migrando automáticamente los datos de Juanan desde athletes.json.
    Esto garantiza que no se pierda ningún avance ni configuración previa.
    """
    users = {}
    
    # Cargar datos existentes de athletes.json si existen
    legacy_data = {}
    if os.path.exists(LEGACY_ATHLETES_FILE):
        try:
            with open(LEGACY_ATHLETES_FILE, 'r', encoding='utf-8') as f:
                legacy_data = json.load(f)
        except Exception as e:
            print(f"Aviso al leer {LEGACY_ATHLETES_FILE}: {e}")

    # Claves predeterminadas de Juanan
    coach_api_key = legacy_data.get("coach_api_key", "") or os.environ.get("INTERVALS_API_KEY", "8yeez3v4p8i11ld1pdnvx3ur")
    coach_athlete_id = legacy_data.get("coach_athlete_id", "") or os.environ.get("INTERVALS_ATHLETE_ID", "308429")
    athletes = legacy_data.get("athletes", [])
    smtp_config = legacy_data.get("smtp_config", {
        "server": "smtp.gmail.com",
        "port": 587,
        "user": "juantoba1995@gmail.com",
        "password": "",
        "coach_name": "Juanan Coy - Entrenador",
        "bcc_coach": True
    })

    # Si athletes estaba vacío, cargar los deportistas conocidos
    if not athletes:
        athletes = [
            {"name": "Juanan", "athlete_id": "308429", "email": "juantoba1995@gmail.com"},
            {"name": "Manule", "athlete_id": "599534", "email": ""},
            {"name": "Ruiz", "athlete_id": "602664", "email": ""},
            {"name": "Mario", "athlete_id": "634043", "email": ""},
            {"name": "Alejandra", "athlete_id": "651658", "email": "alejandra_isso@hotmail.com"}
        ]

    # Contraseña inicial para Juanan: 'juanan123' (configurable desde la app)
    pwd_hash, salt = _hash_password("juanan123")

    users["juanan"] = {
        "username": "juanan",
        "display_name": "Juanan Coy",
        "email": "juantoba1995@gmail.com",
        "password_hash": pwd_hash,
        "salt": salt,
        "role": "coach",
        "coach_api_key": coach_api_key,
        "coach_athlete_id": str(coach_athlete_id).strip(),
        "athletes": athletes,
        "smtp_config": smtp_config,
        "created_at": datetime.now().isoformat()
    }

    save_users(users)
    return users

def authenticate(username: str, password: str) -> dict | None:
    """Valida credenciales y devuelve el usuario si son correctas."""
    username = str(username).strip().lower()
    users = load_users()
    user = users.get(username)
    if not user:
        return None
    
    if _verify_password(password, user.get("password_hash", ""), user.get("salt", "")):
        return user
    return None

def register_user(username: str, password: str, display_name: str, email: str = "", coach_api_key: str = "", coach_athlete_id: str = "") -> tuple[bool, str]:
    """Registra un nuevo entrenador con su propio espacio aislado."""
    username = str(username).strip().lower()
    if not username:
        return False, "El nombre de usuario es obligatorio."
    if len(username) < 3:
        return False, "El nombre de usuario debe tener al menos 3 caracteres."
    if len(password) < 4:
        return False, "La contraseña debe tener al menos 4 caracteres."
    
    users = load_users()
    if username in users:
        return False, f"El usuario '{username}' ya existe. Elige otro nombre de usuario."
    
    pwd_hash, salt = _hash_password(password)
    users[username] = {
        "username": username,
        "display_name": display_name or username.capitalize(),
        "email": email.strip(),
        "password_hash": pwd_hash,
        "salt": salt,
        "role": "coach",
        "coach_api_key": coach_api_key.strip(),
        "coach_athlete_id": str(coach_athlete_id).strip(),
        "athletes": [],
        "smtp_config": {
            "server": "smtp.gmail.com",
            "port": 587,
            "user": email.strip(),
            "password": "",
            "coach_name": display_name or username.capitalize(),
            "bcc_coach": True
        },
        "created_at": datetime.now().isoformat()
    }

    if save_users(users):
        return True, "¡Cuenta de entrenador creada con éxito!"
    return False, "Error al guardar los datos del nuevo usuario."

def get_user(username: str) -> dict | None:
    """Devuelve los datos de un usuario concreto."""
    users = load_users()
    return users.get(str(username).strip().lower())

def save_user_config(username: str, user_data: dict) -> bool:
    """Actualiza la configuración y deportistas de un entrenador específico."""
    username = str(username).strip().lower()
    users = load_users()
    if username not in users:
        return False
    
    users[username].update(user_data)
    success = save_users(users)
    
    # Si es Juanan, sincronizar también athletes.json para compatibilidad local
    if success and username == "juanan":
        try:
            compat_data = {
                "coach_api_key": users[username].get("coach_api_key", ""),
                "coach_athlete_id": users[username].get("coach_athlete_id", ""),
                "athletes": users[username].get("athletes", []),
                "smtp_config": users[username].get("smtp_config", {})
            }
            with open(LEGACY_ATHLETES_FILE, 'w', encoding='utf-8') as f:
                json.dump(compat_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
            
    return success

def change_password(username: str, old_password: str, new_password: str) -> tuple[bool, str]:
    """Permite al usuario cambiar su contraseña."""
    user = authenticate(username, old_password)
    if not user:
        return False, "La contraseña actual es incorrecta."
    if len(new_password) < 4:
        return False, "La nueva contraseña debe tener al menos 4 caracteres."
    
    pwd_hash, salt = _hash_password(new_password)
    users = load_users()
    users[username]["password_hash"] = pwd_hash
    users[username]["salt"] = salt
    if save_users(users):
        return True, "Contraseña actualizada con éxito."
    return False, "Error al guardar la nueva contraseña."
