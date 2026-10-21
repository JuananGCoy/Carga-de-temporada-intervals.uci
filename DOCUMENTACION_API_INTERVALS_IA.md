# 📘 Guía Completa de la API de Intervals.icu y Manual de Análisis para IA
> **Documento de Especificación Técnica, Endpoints, Credenciales y Lógica Fisiológica de Análisis.**  
> *Diseñado para ser reutilizado en otros proyectos, integraciones directas o como contexto maestro para asistentes de Inteligencia Artificial (Gemini, Claude, GPT, etc.).*

---

## 1. 🔑 Credenciales y Datos del Entrenador

Esta sección contiene las claves maestras y la configuración de acceso a Intervals.icu para operar sobre la cuenta del entrenador y sus deportistas tutorizados:

### 👤 Perfil del Entrenador
- **Nombre:** Juanan Coy
- **Usuario de la Suite:** `juanan`
- **Athlete ID en Intervals.icu:** `308429`
- **Intervals.icu API Key (Escritura + Lectura):** `8yeez3v4p8i11ld1pdnvx3ur`
- **Google Gemini API Key (IA Deportiva):** `AIzaSyBWUiS55kege2Bm7SVDFFJm8HUj-rS57Nc`
- **Base URL de la API:** `https://intervals.icu/api/v1`

### 👥 Cartera de Atletas Tutorizados
Para llamar a la API de un deportista tutorizado por este entrenador, se utiliza la API Key del entrenador (`8yeez3v4p8i11ld1pdnvx3ur`) especificando el ID del deportista con el prefijo obligatorio `i`:

| Deportista | ID Numérico | ID para la API (`athlete_id`) | Email de Notificaciones | Tipo de Perfil |
| :--- | :---: | :---: | :--- | :--- |
| **Juanan** | `308429` | `"0"` o `"i308429"` | `juantoba1995@gmail.com` | Entrenador / Atleta |
| **Manule** | `599534` | `"i599534"` | *(Sin email asignado)* | Atleta Tutorizado |
| **Ruiz** | `602664` | `"i602664"` | *(Sin email asignado)* | Atleta Tutorizado |
| **Mario** | `634043` | `"i634043"` | *(Sin email asignado)* | Atleta Tutorizado |
| **Alejandra** | `651658` | `"i651658"` | `alejandra_isso@hotmail.com` | Atleta Tutorizada |

---

## 2. 🛡️ Reglas de Oro de la API de Intervals.icu

### Regla 1: Formato del `athlete_id` (Crítica)
- **Para el propio entrenador** (dueño de la API Key): Se puede usar el identificador `"0"`, o bien su ID con prefijo `"i308429"`.
- **Para deportistas gestionados**: **ES OBLIGATORIO añadir el prefijo `i`** (ejemplo: `i599534`). Si se envía el número suelto `599534`, Intervals.icu devolverá un error `404 Not Found` o `403 Forbidden`.

### Regla 2: Autenticación HTTP (Crítica - Motivo habitual del Error 401)
Las claves personales de desarrollador de Intervals.icu **NO admiten Bearer token** (Bearer es solo para tokens OAuth2). Requieren obligatoriamente **HTTP Basic Auth**:
- **Usuario (Username):** La palabra literal `"API_KEY"` (en mayúsculas, tal cual, sin comillas).
  - ❌ **ERROR COMÚN:** No pongas tu nombre de usuario (`juanan`), ni tu ID (`308429`), ni tu email. Si pones cualquiera de esos, Intervals.icu devolverá `401 Unauthorized`.
- **Contraseña (Password):** Tu clave API real: `8yeez3v4p8i11ld1pdnvx3ur`.

#### Cabecera HTTP pre-calculada en Base64 (100% probada):
Si tu cliente HTTP o tu IA permite enviar la cabecera directamente, usa esta:
```http
Authorization: Basic QVBJX0tFWTo4eWVlejN2NHA4aTExbGQxcGRudngzdXI=
```
*(Esta cadena es el resultado exacto de codificar en base64 `API_KEY:8yeez3v4p8i11ld1pdnvx3ur`).*

### Regla 3: Headers HTTP Estándar
```http
Authorization: Basic QVBJX0tFWTo4eWVlejN2NHA4aTExbGQxcGRudngzdXI=
Content-Type: application/json
Accept: application/json
User-Agent: TriathlonCoachSuite/1.0
```

---

## 3. 📡 Catálogo Completo de Endpoints y Llamadas API

### Endpoint 1: Obtener Actividades Realizadas
Descarga todas las sesiones de entrenamiento completadas por el deportista en un rango de fechas.

- **Método:** `GET`
- **Ruta:** `/athlete/{athlete_id}/activities`
- **URL Completa:** `https://intervals.icu/api/v1/athlete/{athlete_id}/activities`
- **Parámetros de Consulta (Query Params):**
  - `oldest`: Fecha inicial en formato `YYYY-MM-DD` (ej. `2026-10-12`).
  - `newest`: Fecha final en formato `YYYY-MM-DD` (ej. `2026-10-19`).

#### Campos clave del JSON de respuesta por cada actividad:
```json
{
  "id": "a12345678",
  "name": "Tirada Larga 22k + Progresivo",
  "type": "Run",
  "start_date_local": "2026-10-18T08:30:00",
  "moving_time": 6840,
  "elapsed_time": 7100,
  "distance": 22450.5,
  "icu_training_load": 142,
  "icu_intensity": 82.5,
  "average_heartrate": 154,
  "max_heartrate": 172,
  "average_speed": 3.28,
  "feel": 4,
  "icu_rpe": 7,
  "perceived_exertion": 7,
  "description": "Sensaciones muy buenas hasta el km 18. Luego las piernas empezaron a pesar un poco.",
  "icu_athlete_comments": null,
  "icu_hr_zone_times": [300, 3600, 2100, 840, 0, 0, 0],
  "icu_zone_times": null,
  "paired_event_id": 987654
}
```

#### Diccionario de Variables de la Actividad:
- `id`: Identificador único de la actividad en Intervals.icu.
- `name`: Título asignado por el atleta o el dispositivo GPS.
- `type`: Tipo de disciplina (`Run`, `Ride`, `VirtualRide`, `Swim`, `WeightTraining`, `Hike`, `Walk`, `Workout`).
- `moving_time`: Tiempo real de movimiento en **segundos** (`horas = moving_time / 3600`).
- `distance`: Distancia recorrida en **metros** (`km = distance / 1000.0`).
- `icu_training_load`: Carga de entrenamiento acumulada (**TSS** - Training Stress Score).
- `icu_intensity`: Factor de Intensidad (**IF** en porcentaje, ej. 82.5%).
- `average_heartrate`: Pulso medio en pulsaciones por minuto (ppm).
- `feel`: Sensaciones subjetivas del atleta en escala de 1 a 5 (ver sección 4).
- `icu_rpe` o `perceived_exertion`: Nivel de esfuerzo percibido en escala de 1 a 10 Borg CR10 (ver sección 4).
- `description` / `icu_athlete_comments`: Texto y notas del atleta.
- `icu_hr_zone_times`: Lista con los segundos transcurridos en cada zona de frecuencia cardíaca (Z1 a Z7).
- `paired_event_id`: ID del evento planificado con el que se emparejó automáticamente esta actividad.

---

### Endpoint 2: Obtener Datos de Wellness y Rendimiento PMC
Descarga las métricas diarias de forma, fatiga, condición física y salud (CTL, ATL, TSB, pulso en reposo, sueño, etc.).

- **Método:** `GET`
- **Ruta:** `/athlete/{athlete_id}/wellness`
- **URL Completa:** `https://intervals.icu/api/v1/athlete/{athlete_id}/wellness`
- **Parámetros de Consulta (Query Params):**
  - `oldest`: Fecha inicial `YYYY-MM-DD`.
  - `newest`: Fecha final `YYYY-MM-DD`.

#### Campos clave del JSON de respuesta:
```json
{
  "id": "2026-10-18",
  "ctl": 54.2,
  "atl": 68.5,
  "tsb": -14.3,
  "rampRate": 3.8,
  "ctlLoad": 142.0,
  "restingHR": 48,
  "hrv": 62.0,
  "soreness": 2,
  "fatigue": 3,
  "stress": 2,
  "mood": 4,
  "sleepQuality": 4,
  "sleepSecs": 27000
}
```

#### Diccionario de Variables de Wellness:
- `ctl`: **Chronic Training Load (Fitness)**. Media ponderada a 42 días de carga. Mide el volumen y adaptaciones a largo plazo.
- `atl`: **Acute Training Load (Fatiga)**. Media ponderada a 7 días. Refleja el cansancio acumulado reciente.
- `tsb`: **Training Stress Balance (Forma)**. Se calcula como `CTL - ATL`. Indica si el atleta está cargado o fresco.
- `rampRate`: Tasa de incremento semanal del CTL (puntos de Fitness ganados por semana).
- `ctlLoad`: Carga total en TSS generada ese día.
- `restingHR`: Frecuencia cardíaca en reposo al despertar (un aumento de 5-7 ppm suele anticipar fatiga o infección).
- `hrv`: Variabilidad de la Frecuencia Cardíaca (indicador de recuperación del sistema nervioso autónomo).

---

### Endpoint 3: Obtener Eventos y Calendario Planificado
Permite conocer qué entrenamientos estaban planificados por el entrenador, detectar sesiones saltadas o próximas competiciones.

- **Método:** `GET`
- **Ruta:** `/athlete/{athlete_id}/events`
- **URL Completa:** `https://intervals.icu/api/v1/athlete/{athlete_id}/events`
- **Parámetros de Consulta (Query Params):**
  - `oldest`: Fecha inicial `YYYY-MM-DD`.
  - `newest`: Fecha final `YYYY-MM-DD`.

#### Campos clave del JSON de respuesta:
```json
{
  "id": 987654,
  "start_date_local": "2026-10-18T08:00:00",
  "category": "WORKOUT",
  "type": "Run",
  "name": "Tirada Larga 22k",
  "description": "Calentamiento 2k suave + 18k ritmo maratón + 2k progresivos",
  "load": 140,
  "moving_time": 6900
}
```
- Si `category == "WORKOUT"`: Es un entrenamiento pautado por el entrenador.
- Si `category == "RACE"`: Es una competición marcada en el calendario (maratón, triatlón, etc.).
- Si `category == "NOTE"`: Nota o recordatorio técnico.

---

### Endpoint 4: Subir / Planificar un Entrenamiento al Calendario
Permite a una IA o a la aplicación crear una sesión directamente en el calendario del deportista.

- **Método:** `POST`
- **Ruta:** `/athlete/{athlete_id}/events`
- **URL Completa:** `https://intervals.icu/api/v1/athlete/{athlete_id}/events`
- **Cuerpo de la Petición (JSON Body):**
```json
{
  "start_date_local": "2026-10-25T07:30:00",
  "category": "WORKOUT",
  "type": "Run",
  "name": "Series 6x1000m R4 (Umbral)",
  "description": "Warmup\n- 20m Z2\n\n6x\n- 1000m 3:45/km\n- 90s rec 5:30/km\n\nCooldown\n- 10m Z1"
}
```
- **Sintaxis de entrenamientos de Intervals.icu:** Admite texto plano con bloques estructurados (`Warmup`, `Main set`, `Cooldown`, pasos de repetición `6x`, ritmos por km `3:45/km`, porcentajes de FTP `85%`, zonas `Z2`, o pulsaciones).

---

### Endpoint 5: Consultar Perfil y Zonas del Deportista
Permite conocer umbrales fisiológicos, peso, zonas de pulso y potencia configuradas.

- **Método:** `GET`
- **Ruta:** `/athlete/{athlete_id}`
- **URL Completa:** `https://intervals.icu/api/v1/athlete/{athlete_id}`
- **Datos de Retorno:**
  - `icu_resting_hr`, `icu_max_hr`, `icu_lthr` (Umbral de lactato en FC).
  - `icu_weight` (peso en kg).
  - `sportSettings`: Ajustes por deporte (FTP de ciclismo, ritmo umbral de carrera en m/s o min/km).

---

## 4. 🧠 Manual para la IA: Cómo Analizar e Interpretar los Datos Fisiológicos

Cuando un modelo de lenguaje o una IA procese los datos de Intervals.icu de un atleta, debe aplicar las siguientes reglas fisiológicas basadas en la metodología de entrenamiento deportivo:

### 1. Lectura del Estado de Forma (TSB = CTL - ATL)
El valor de `tsb` (Training Stress Balance) del último día del periodo define la frescura o fatiga del atleta:

| Rango de TSB | Fase Fisiológica | Diagnóstico que debe emitir la IA |
| :---: | :--- | :--- |
| **`TSB < -30`** | **🛑 Sobrecarga Severa** | El cansancio acumulado supera con creces la capacidad de asimilación. Alto riesgo de lesión tendinosa o muscular. La IA debe recomendar reducir volumen, priorizar descanso y rodajes regenerativos muy suaves. |
| **`-30 <= TSB <= -10`** | **🚀 Zona Óptima de Carga** | El atleta está en el "sweet spot" productivo. Asimilando grandes adaptaciones cardiovasculares y musculares sin fatiga destructiva. |
| **`-10 < TSB <= +5`** | **⚖️ Consolidación / Neutro** | Fatiga y condición física están equilibradas. Ideal para semanas de transición o fijación de ritmos. |
| **`+5 < TSB <= +25`** | **🏆 Frescura Competitiva (Taper)** | La fatiga aguda se ha disipado manteniendo el motor intacto. Punto óptimo para competir, test de lactato o buscar marca personal. |
| **`TSB > +25`** | **📉 Desentrenamiento** | Inactividad prolongada o parón. Si no es fin de temporada, el motor se está desentrenando y perdiendo adaptaciones mitocondriales. |

### 2. Tasa de Incremento Semanal (`rampRate`)
- **`+2.0 a +5.0` puntos/semana:** Progresión saludable y sostenible.
- **`> +6.0 a +8.0` puntos/semana:** Progresión demasiado rápida. Alerta de sobrecarga articular o fatiga del sistema nervioso central.
- **Negativo:** Descarga programada o parón por enfermedad/viaje.

---

### 3. Distribución Polarizada de Intensidad (Modelo 80/20)
Al sumar los segundos en zonas de pulso o potencia de todas las actividades:
- **🟢 Base Aeróbica (Z1 + Z2):** Debe representar entre el **75% y el 85%** del tiempo total. Es la base de la pirámide (densidad mitocondrial, capilarización, economía de sustratos lipídicos).
- **🟡 Zona Gris / Tempo (Z3):** Debe mantenerse entre el **5% y el 15%**.  
  *Alerta para la IA:* Si Z3 supera el 20%-25%, el deportista está rodando demasiado rápido en los días fáciles ("ni entrena suave para recuperar, ni fuerte para estimular"), generando fatiga residual innecesaria.
- **🔴 Alta Intensidad / Calidad (Z4 + Z5+):** Debe ser el **10% al 15%** del tiempo total (series de VO2max, cambios de ritmo, trabajo a umbral anaeróbico).

---

### 4. Escalas Subjetivas: `feel` y `icu_rpe`
Intervals.icu almacena dos variables subjetivas cruciales que la IA **siempre debe cruzar con los datos objetivos (TSS, pulso, ritmo)**:

#### ⚠️ Escala `feel` (Sensación: 1 a 5 - Heredada del estándar Garmin FIT)
> **¡Atención!** En Intervals.icu la escala de `feel` es inversa a las valoraciones convencionales de estrellas. El valor más bajo es el mejor estado y el más alto es el peor:
- **`1` = 🚀 Strong (Fuerte / Excelente con chispa / Piernas increíbles)**
- **`2` = 🙂 Good (Bien / Buenas sensaciones)**
- **`3` = 😐 Normal (Normal / Sensaciones estables)**
- **`4` = 😕 Weak (Débil / Pesado / Cansado)**
- **`5` = 😞 Very Weak (Muy débil / Agotado / Terrible)**

#### Escala `icu_rpe` o `perceived_exertion` (Esfuerzo Percibido: 1 a 10 Borg CR10)
- `1 - 2`: Muy suave (Recuperación activa / Regenerativo)
- `3 - 4`: Suave / Fondo aeróbico continuo
- `5 - 6`: Moderado / Tempo sostenido
- `7 - 8`: Duro / Umbral anaeróbico exigente
- `9 - 10`: Máximo / Extenuante (Competición o test al fallo)

#### Matriz de Cruce Fisiológico:
- **TSS Alto + FC Baja/Estable + Feel 1-2 (Fuerte/Bien) + RPE 6-7:** Excelente eficiencia cardiovascular y alta adaptabilidad.
- **TSS Moderado + FC Alta/Deriva + Feel 4-5 (Débil/Agotado) + RPE 8-9:** Alerta roja. Desacoplamiento cardíaco. Causas habituales: deshidratación, falta de carbohidratos intra-entreno, estrés laboral o incubación de proceso vírico.
- **Día Regenerativo con RPE >= 6 o Feel >= 4:** El deportista no respeta el descanso activo y está rodando por encima de la zona prescrita.

---

### ⚠️ Diagnóstico de Errores Comunes (Por qué ChatGPT u otros entornos dan error 403):
1. **Entorno Sandbox sin salida a Internet (Code Interpreter de ChatGPT):**  
   Si le pides a ChatGPT que ejecute un script de Python con `requests.get()` desde su chat, **fallará siempre** porque el entorno de ejecución de código de OpenAI está completamente aislado y tiene bloqueado el tráfico hacia Internet exterior.
2. **Autenticación en GPT Actions / Conectores:**  
   Si configuras un *Custom GPT Action* (esquema OpenAPI / Swagger):
   - El método de autenticación debe ser **Basic Auth**: Usuario `API_KEY` y Password tu clave `8yeez3v4p8i11ld1pdnvx3ur`.  
   - Si se selecciona *Bearer Token*, algunos proxies de OpenAI o servidores de Intervals.icu rechazan la cabecera devolviendo `403 Forbidden`.
3. **Casillas de permisos en Intervals.icu:**  
   En la cuenta de Intervals.icu > *Settings* > *API Key*, deben estar activadas las casillas de **Read** y **Write**.
4. **Falta del prefijo `i` en deportistas tutorizados:**  
   Llamar a `/athlete/599534/activities` con la clave del entrenador da 403/404. La llamada correcta es `/athlete/i599534/activities`.
5. **Restricción de datos sincronizados desde Strava:**  
   Por los términos de privacidad de Strava, si un deportista sincroniza sus entrenamientos mediante Strava hacia Intervals.icu, la API de Intervals.icu no permite a aplicaciones de terceros leer streams detallados o descripciones completas sin autenticación OAuth directa del deportista. Para sincronización completa sin restricciones, los deportistas deben vincular directamente Garmin Connect, Wahoo o Coros a Intervals.icu.

---

### 5. Detección y Aislamiento de Comentarios Reales del Atleta
Muchas actividades importadas desde Garmin o Strava contienen texto automático insertado por servicios meteorológicos como **Klimat** o las instrucciones de los intervalos.
La IA debe filtrar esos textos y rescatar únicamente lo que el atleta escribió con sus propias palabras:

```python
def clean_athlete_comment(desc, comments):
    """
    Descarta textos automáticos de Klimat, datos de viento y pasos de intervalos,
    extrayendo las sensaciones reales escritas por el atleta.
    """
    if comments and str(comments).strip():
        return str(comments).strip()
    if not desc or not str(desc).strip():
        return None
    
    ignore_keywords = [
        'klimatapp', 'sensación térmica', 'sensacion termica', 
        'humedad', 'viento desde', 'main set', 'warm up', 'cooldown'
    ]
    lines = str(desc).strip().splitlines()
    clean_lines = [
        l.strip() for l in lines 
        if l.strip() and not any(k in l.lower() for k in ignore_keywords) and not l.strip().startswith('- ')
    ]
    return " ".join(clean_lines) if clean_lines else None
```

---

### 6. Clasificación de Sesiones Clave y Veredicto Técnico
Una IA debe clasificar las sesiones prioritarias de la semana en 5 categorías:
1. **🏆 Competición / Test:** (Nombre contiene `maratón`, `10k`, `triatlón`, o `rpe == 10`). Veredicto: Analizar si se cumplió el ritmo objetivo, deriva cardíaca final y respuesta al avituallamiento.
2. **🏃‍♂️ Tirada Larga / Volumen Clave:** (Distancia >= 16 km o duración >= 1h 30m). Veredicto: Pilar de fondo aeróbico. Evaluar si la fatiga en los últimos 4-5 km fue muscular o de vaciado de glucógeno.
3. **⚡ Sesión de Ritmo / Series / Umbral:** (Nombre contiene `series`, `interval`, `tempo`, `fartlek`, o ratio `TSS/hora >= 65`). Veredicto: Asimilación de vatios/ritmo. Si el Feel es 5, frescura neuromuscular alta; si es 1-2 con RPE > 8, fatiga residual acumulada.
4. **🏋️‍♂️ Fuerza / Trabajo Estructural:** (`WeightTraining` o nombres de gimnasio). Veredicto: Blindaje articular (sóleo, cadera, cuádriceps) para prevenir lesiones en carrera a pie.
5. **🌱 Regenerativo / Descarga:** Rodaje suave (< 45 min, RPE <= 3). Veredicto: Vaciado de lactato sin estrés para el sistema nervioso.

---

### 7. Formulación de Preguntas de Feedback Activo
La IA no debe limitarse a resumir lo ocurrido con frases hechas ("buen trabajo", "sigue así"). Debe **formular 2 o 3 preguntas técnicas directas** dirigidas al atleta:
- Si hubo una sesión con **RPE >= 8 o Feel 1-2**: Preguntar si la pesadez fue fatiga muscular localizada (ej. sóleos cargados) o falta de energía general.
- En la **Tirada Larga**: Preguntar por la nutrición intra-entreno (geles/carbohidratos tomados por hora) y las sensaciones en los últimos kilómetros.
- Si hay **sesiones planificadas no realizadas (saltadas)**: Preguntar si el motivo fue falta de tiempo o necesidad física de descansar.

---

## 5. 💻 Script de Ejemplo Completo en Python (Listo para Usar)

Este script contiene la implementación limpia y completa de las llamadas a Intervals.icu para extraer actividades, wellness, calcular PMC y clasificar sesiones:

```python
import requests
from datetime import datetime, timedelta

# Configuración del Entrenador
COACH_API_KEY = "8yeez3v4p8i11ld1pdnvx3ur"
ATHLETE_ID = "i599534"  # Ejemplo con Manule (prefijo 'i' obligatorio)
BASE_URL = "https://intervals.icu/api/v1"

def api_get(endpoint, params=None):
    url = f"{BASE_URL}{endpoint}"
    resp = requests.get(
        url,
        params=params,
        auth=('API_KEY', COACH_API_KEY),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        timeout=15
    )
    if resp.status_code == 200:
        return resp.json()
    raise Exception(f"Error {resp.status_code} en {url}: {resp.text}")

# 1. Definir rango de fechas (últimos 7 días)
today = datetime.now()
date_newest = today.strftime("%Y-%m-%d")
date_oldest = (today - timedelta(days=7)).strftime("%Y-%m-%d")

# 2. Descargar Actividades Realizadas
activities = api_get(f"/athlete/{ATHLETE_ID}/activities", {"oldest": date_oldest, "newest": date_newest})
print(f"✅ Se descargaron {len(activities)} actividades.")

# 3. Descargar Wellness (Fitness, Fatiga, TSB)
wellness = api_get(f"/athlete/{ATHLETE_ID}/wellness", {"oldest": date_oldest, "newest": date_newest})
if wellness:
    current_well = wellness[-1]
    ctl = current_well.get('ctl', 0)
    atl = current_well.get('atl', 0)
    tsb = ctl - atl
    ramp = current_well.get('rampRate', 0)
    print(f"📊 PMC: Fitness (CTL)={ctl:.1f} | Fatiga (ATL)={atl:.1f} | Forma (TSB)={tsb:+.1f} | Rampa={ramp:+.1f}")

# 4. Descargar Eventos Planificados
events = api_get(f"/athlete/{ATHLETE_ID}/events", {"oldest": date_oldest, "newest": date_newest})
planned_workouts = [e for e in events if e.get('category') == 'WORKOUT']
print(f"📅 Entrenamientos planificados en la semana: {len(planned_workouts)}")

# 5. Análisis rápido de actividades
total_hours = sum(a.get('moving_time', 0) for a in activities) / 3600.0
total_tss = sum(int(a.get('icu_training_load', 0) or 0) for a in activities)
print(f"⏱️ Volumen total: {total_hours:.1f} horas | Carga total: {total_tss} TSS")
```

---

## 6. 🤖 Prompt Maestro del Sistema para la IA (System Prompt)

Si vas a conectar un agente de IA (vía API de Gemini, OpenAI, Claude, etc.) para que analice automáticamente los datos descargados de Intervals.icu, utiliza este System Prompt:

```markdown
Eres un Fisiólogo del Ejercicio y Entrenador de Alto Rendimiento especialista en Triatlón, Ciclismo y Atletismo de Fondo.
Tu objetivo es analizar los datos de entrenamiento y recuperación extraídos de la API de Intervals.icu para generar un informe técnico, riguroso, empático y exento de clichés o frases manidas.

DIRECTRICES DE ANÁLISIS:
1. Analiza el PMC: Interpreta el valor de TSB (Forma), CTL (Fitness a 42 días) y ATL (Fatiga a 7 días). Determina si el deportista está en fase de sobrecarga productiva, frescura competitiva o fatiga excesiva.
2. Cruza lo objetivo con lo subjetivo: Compara los datos duros (TSS, potencia, pulso, ritmo y distancia) con el esfuerzo percibido (RPE 1 a 10) y las sensaciones reportadas por el atleta (Feel 1 a 5).
3. Analiza las sesiones clave: Clasifica carreras, tiradas largas, series y trabajo de fuerza. Emite un diagnóstico fisiológico de la asimilación del estímulo.
4. Cita los comentarios del atleta: Si el atleta dejó notas sobre dolor muscular, digestión, calor o energía, aborda directamente sus palabras.
5. Solicita feedback activo: Formula 2 o 3 preguntas técnicas y precisas sobre puntos críticos ocurridos en la semana (sensaciones en los últimos kilómetros de la tirada larga, sobrecargas musculares, motivos de sesiones saltadas).
6. Comunica siempre en español, con tono profesional, constructivo y cercano.
```
