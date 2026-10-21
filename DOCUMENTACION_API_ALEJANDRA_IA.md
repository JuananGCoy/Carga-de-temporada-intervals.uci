# 📘 Guía de la API de Intervals.icu y Manual de Análisis para IA: Alejandra (Ale)
> **Especificación Técnica, Endpoints Directos, Credenciales y Lógica Fisiológica de Análisis para Alejandra.**  
> *Diseñado para ser copiado directamente en ChatGPT, Claude, Gemini o cualquier aplicación externa para consultar y analizar todos los entrenamientos y métricas de Ale.*

---

## 1. 🔑 Credenciales y Datos de Acceso de Alejandra

Para consultar o escribir datos en el perfil de Alejandra, se utiliza la API Key de su entrenador (Juanan Coy) especificando su ID de atleta con el prefijo obligatorio `i`:

* **Nombre de la Atleta:** Alejandra (en Intervals.icu: `alepalosamigos`)
* **Localidad / Región:** Hellín, Albacete (España)
* **Email de Notificaciones:** `alejandra_isso@hotmail.com`
* **Athlete ID Numérico:** `651658`
* **Athlete ID para la API (Obligatorio con `i`):** `i651658`
* **Entrenador Tutor:** Juanan Coy (Athlete ID: `308429`)
* **API Key de Acceso (Coach):** `8yeez3v4p8i11ld1pdnvx3ur`
* **Base URL de la API:** `https://intervals.icu/api/v1`

---

## 2. 🛡️ Autenticación y Cabeceras HTTP (100% Probadas)

Intervals.icu exige **HTTP Basic Auth** para claves de desarrollador:
* **Username:** `API_KEY` *(literalmente esas 7 letras en mayúsculas. ❌ No pongas el nombre ni el ID).*
* **Password:** `8yeez3v4p8i11ld1pdnvx3ur`

### ⚡ Cabecera Pre-Calculada en Base64 (Recomendada para la IA)
Envía directamente esta cabecera en todas las peticiones HTTP para evitar errores de autenticación:
```http
Authorization: Basic QVBJX0tFWTo4eWVlejN2NHA4aTExbGQxcGRudngzdXI=
Content-Type: application/json
Accept: application/json
User-Agent: TriathlonCoachSuite/1.0
```

---

## 3. 💬 Mensaje Listo para Copiar y Pegar en ChatGPT

> Copia el siguiente texto y pégalo directamente en ChatGPT para que comience a consultar y analizar a Alejandra de inmediato:

```text
Por favor, analiza el estado de entrenamiento de mi deportista Alejandra en Intervals.icu.

DATOS DE CONEXIÓN:
- Base URL: https://intervals.icu/api/v1
- Athlete ID: i651658
- Cabecera HTTP:
  Authorization: Basic QVBJX0tFWTo4eWVlejN2NHA4aTExbGQxcGRudngzdXI=

ENDPOINTS A CONSULTAR:
1. Perfil y umbrales:
   GET https://intervals.icu/api/v1/athlete/i651658/profile
2. Actividades de los últimos 7 días:
   GET https://intervals.icu/api/v1/athlete/i651658/activities?oldest=2026-10-14&newest=2026-10-21
3. Wellness y rendimiento PMC (CTL, ATL, TSB, rampa):
   GET https://intervals.icu/api/v1/athlete/i651658/wellness?oldest=2026-10-14&newest=2026-10-21
4. Calendario y entrenamientos planificados:
   GET https://intervals.icu/api/v1/athlete/i651658/events?oldest=2026-10-14&newest=2026-10-21

REGLAS DE ANÁLISIS:
- En Intervals.icu la escala 'feel' es inversa (Garmin FIT): 1 es Fuerte/Excelente y 5 es Muy débil/Agotado.
- 'icu_rpe' va de 1 a 10 (Borg CR10).
- Cruza los datos duros (TSS, pulso, ritmo) con las sensaciones reportadas.
- Emite un veredicto técnico y formula 2 o 3 preguntas de feedback activo para Alejandra.
```

---

## 4. 📡 Catálogo de Endpoints Directos para Alejandra

### Endpoint 1: Perfil Fisiológico y Umbrales de Ale
Obtiene el FTP, umbrales de pulso (LTHR), zonas configuradas y datos de peso.
* **Método:** `GET`
* **URL:** `https://intervals.icu/api/v1/athlete/i651658/profile`

---

### Endpoint 2: Actividades Realizadas por Ale
Descarga todas las sesiones de entrenamiento ejecutadas en un rango de fechas.
* **Método:** `GET`
* **URL:** `https://intervals.icu/api/v1/athlete/i651658/activities?oldest=YYYY-MM-DD&newest=YYYY-MM-DD`
* **Campos clave que devuelve:**
  * `name`: Nombre del entrenamiento.
  * `type`: Deporte (`Run`, `Ride`, `VirtualRide`, `Swim`, `WeightTraining`, `Hike`, `Walk`).
  * `start_date_local`: Fecha y hora de inicio (`YYYY-MM-DDTHH:MM:SS`).
  * `moving_time`: Segundos en movimiento (`horas = moving_time / 3600`).
  * `distance`: Metros recorridos (`km = distance / 1000.0`).
  * `icu_training_load`: Carga de entrenamiento (**TSS**).
  * `icu_intensity`: Factor de Intensidad (**IF %**).
  * `average_heartrate`: Frecuencia cardíaca media en ppm.
  * `max_heartrate`: Frecuencia cardíaca máxima.
  * `feel`: Sensación subjetiva del 1 al 5 *(1=Fuerte, 5=Muy débil)*.
  * `icu_rpe` / `perceived_exertion`: Esfuerzo percibido del 1 al 10 *(Borg CR10)*.
  * `description` / `icu_athlete_comments`: Notas y sensaciones escritas por Ale.
  * `icu_hr_zone_times`: Segundos en cada zona de pulso (Z1 a Z7).
  * `paired_event_id`: ID del entrenamiento planificado al que corresponde.

---

### Endpoint 3: Wellness y Métricas PMC de Ale (Forma, Fatiga y Fitness)
Descarga la curva de rendimiento y recuperación diaria.
* **Método:** `GET`
* **URL:** `https://intervals.icu/api/v1/athlete/i651658/wellness?oldest=YYYY-MM-DD&newest=YYYY-MM-DD`
* **Campos clave:**
  * `ctl`: **Fitness acumulado** (media a 42 días de TSS).
  * `atl`: **Fatiga aguda** (media a 7 días de TSS).
  * `tsb`: **Forma / Frescura** (`TSB = CTL - ATL`).
  * `rampRate`: Puntos de Fitness ganados por semana.
  * `ctlLoad`: Carga diaria en TSS.
  * `restingHR`: Pulso en reposo.
  * `hrv`: Variabilidad cardíaca (recuperación del sistema nervioso).
  * `soreness`, `fatigue`, `stress`, `mood`, `sleepQuality`: Cuestionario de bienestar.

---

### Endpoint 4: Calendario y Eventos Planificados de Ale
Permite conocer qué entrenamientos estaban planificados por el entrenador, detectar sesiones completadas vs saltadas y próximas competiciones.
* **Método:** `GET`
* **URL:** `https://intervals.icu/api/v1/athlete/i651658/events?oldest=YYYY-MM-DD&newest=YYYY-MM-DD`
* **Filtros útiles:**
  * `category == "WORKOUT"`: Entrenamientos pautados.
  * `category == "RACE"`: Competiciones u objetivos marcados en el calendario.

---

### Endpoint 5: Crear / Subir un Entrenamiento al Calendario de Ale
Permite a la IA planificar y subir una sesión directamente al calendario de Alejandra.
* **Método:** `POST`
* **URL:** `https://intervals.icu/api/v1/athlete/i651658/events`
* **Cuerpo de la Petición (JSON Body):**
```json
{
  "start_date_local": "2026-10-25T08:00:00",
  "category": "WORKOUT",
  "type": "Run",
  "name": "Tirada Larga 18k + Cambios",
  "description": "Warmup\n- 20m Z2\n\nMain set\n- 12k ritmo cómodo 5:15/km\n- 3x 1000m 4:45/km rec 1m trote\n\nCooldown\n- 10m trote Z1"
}
```

---

## 5. 🧠 Manual para la IA: Cómo Analizar los Datos Fisiológicos de Ale

Cuando la IA procese las actividades y wellness de Alejandra, debe aplicar los siguientes criterios técnicos:

### 1. Estado de Forma (TSB = CTL - ATL)
* **`TSB < -30` (🛑 Sobrecarga):** Fatiga acumulada excesiva. Riesgo de sobreuso o lesión. Recomendar descarga activa y sueño.
* **`-30 <= TSB <= -10` (🚀 Asimilación Productiva):** Zona dulce de construcción de base. Ale está asimilando la carga con éxito.
* **`-10 < TSB <= +5` (⚖️ Consolidación):** Carga y fatiga equilibradas.
* **`+5 < TSB <= +25` (🏆 Frescura Competitiva):** Tapering óptimo para competir o buscar ritmo exigente con piernas frescas.
* **`TSB > +25` (📉 Desentrenamiento):** Fatiga mínima. Si no es periodo de descanso, es momento de reactivar el estímulo.

### 2. Control de la Rampa Semanal (`rampRate`)
* **`+2.0 a +5.0`:** Incremento óptimo y seguro.
* **`> +6.0 a +8.0`:** Subida de carga demasiado brusca para articulaciones y tendones.

### 3. Escala Oficial de Sensaciones (`feel`) y Dificultad (`icu_rpe`)
Intervals.icu utiliza el estándar Garmin FIT:
* **`feel` (1 a 5):**
  * `1`: 🚀 **Strong / Excelente** (Sensaciones sobresalientes, con chispa)
  * `2`: 🙂 **Good / Bien** (Buenas sensaciones, ritmo cómodo)
  * `3`: 😐 **Normal / Estable** (Sesión estándar)
  * `4`: 😕 **Weak / Débil** (Piernas pesadas, falta de chispa)
  * `5`: 😞 **Very Weak / Agotado** (Fatiga alta, malas sensaciones)
* **`icu_rpe` (1 a 10 Borg CR10):**
  * `1-2`: Muy suave (Regenerativo)
  * `3-4`: Suave (Fondo aeróbico Z2)
  * `5-6`: Moderado (Tempo Z3)
  * `7-8`: Duro (Umbral anaeróbico Z4)
  * `9-10`: Máximo (Competición / Test)

### 4. Limpieza de Comentarios de Ale
Alejandra puede tener comentarios automáticos de clima (Klimat) o pasos de Garmin. La IA debe descartar términos como `klimatapp`, `humedad`, `sensación térmica`, `viento`, etc., y quedarse **exclusivamente con las palabras y notas escritas por ella**.

### 5. Preguntas de Feedback Activo para Ale
La IA debe generar **2 o 3 preguntas técnicas y personalizadas** para que Juanan se las envíe:
* Si en una tirada larga o series reportó **Feel 4 o 5** o **RPE >= 8**: Preguntar si la pesadez fue muscular localizada (gemelos, rodilla, isquios) o falta de energía/nutrición.
* Si hubo sesiones planificadas no registradas: Preguntar con empatía si fue por motivos de agenda o cansancio acumulado.

---

## 6. 💻 Script en Python para Extraer los Datos de Ale en 1 Clic

```python
import requests
from datetime import datetime, timedelta

# Configuración de Alejandra
ATHLETE_ID = "i651658"
BASE_URL = "https://intervals.icu/api/v1"
HEADERS = {
    "Authorization": "Basic QVBJX0tFWTo4eWVlejN2NHA4aTExbGQxcGRudngzdXI=",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def get_data(endpoint, params=None):
    r = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params, timeout=15)
    if r.status_code == 200:
        return r.json()
    raise Exception(f"Error {r.status_code}: {r.text}")

today = datetime.now()
d_new = today.strftime("%Y-%m-%d")
d_old = (today - timedelta(days=7)).strftime("%Y-%m-%d")

# 1. Perfil de Ale
profile = get_data(f"/athlete/{ATHLETE_ID}/profile")
print(f"👤 Atleta: {profile['athlete']['name']} ({profile['athlete']['city']})")

# 2. Actividades de los últimos 7 días
acts = get_data(f"/athlete/{ATHLETE_ID}/activities", {"oldest": d_old, "newest": d_new})
print(f"🏃‍♀️ Actividades realizadas en la semana: {len(acts)}")

# 3. Wellness y PMC
well = get_data(f"/athlete/{ATHLETE_ID}/wellness", {"oldest": d_old, "newest": d_new})
if well:
    last = well[-1]
    ctl = last.get('ctl', 0)
    atl = last.get('atl', 0)
    tsb = ctl - atl
    print(f"📊 PMC: Fitness (CTL)={ctl:.1f} | Fatiga (ATL)={atl:.1f} | Forma (TSB)={tsb:+.1f}")

# 4. Calendario / Eventos
events = get_data(f"/athlete/{ATHLETE_ID}/events", {"oldest": d_old, "newest": d_new})
print(f"📅 Entrenamientos en calendario: {len(events)}")
```
