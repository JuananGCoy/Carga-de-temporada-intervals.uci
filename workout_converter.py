"""
Conversor LOCAL de texto de entrenamiento al formato estructurado de Intervals.icu.
NO usa ninguna API externa. Parsea directamente el texto del Excel.
"""
import re
import pandas as pd


def convert_to_intervals_format(text, sport_type):
    """
    Convierte texto natural de entrenamiento al formato estructurado de Intervals.icu.
    Cada deporte tiene sus propias reglas.
    """
    if not text or str(text).strip() == '' or str(text).strip().lower() == 'nan':
        return ""
    
    text = str(text).strip()
    text_lower = text.lower()
    
    # --- DESCANSO ---
    if text_lower in ['descanso total', 'descanso', 'descanso completo']:
        return "Descanso Total"
    
    # --- COMPETICIÓN ---
    if 'competición' in text_lower or 'competicion' in text_lower:
        return text  # Se sube como nota, sin estructura
    
    # --- GIMNASIO / FUERZA ---
    if sport_type == 'WeightTraining':
        return _convert_gym(text)
    
    # --- NATACIÓN ---
    if sport_type == 'Swim':
        return _convert_swim(text)
    
    # --- CICLISMO ---
    if sport_type == 'Ride':
        return _convert_ride(text)
    
    # --- CARRERA (por defecto) ---
    if sport_type == 'Run':
        return _convert_run(text)
    
    return text


def _parse_duration_to_minutes(text):
    """Extrae la duración total en minutos de un texto como '60 min', '1h30', '75 min'."""
    # 1h30, 1h 30, 1h45m
    m = re.search(r'(\d+)\s*h\s*(\d+)', text)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.search(r'(\d+)\s*h', text)
    if m:
        return int(m.group(1)) * 60
    m = re.search(r'(\d+)\s*min', text)
    if m:
        return int(m.group(1))
    return None


def _parse_km(text):
    """Extrae la distancia en km de un texto como '14 km', '8km'."""
    m = re.search(r'(\d+(?:[.,]\d+)?)\s*km', text.lower())
    if m:
        return float(m.group(1).replace(',', '.'))
    return None


def _extract_zone(text):
    """Extrae la zona de entrenamiento de un texto. Devuelve 'Z2' por defecto."""
    m = re.search(r'Z(\d)', text)
    if m:
        return f"Z{m.group(1)}"
    if 'regenerat' in text.lower() or 'suave' in text.lower() or 'muy suave' in text.lower():
        return 'Z1'
    if 'aerób' in text.lower() or 'aerob' in text.lower() or 'continuo' in text.lower():
        return 'Z2'
    if 'umbral' in text.lower() or 'tempo' in text.lower():
        return 'Z4'
    if 'fuego' in text.lower() or 'máx' in text.lower() or 'max' in text.lower():
        return 'Z5'
    return 'Z2'


def _convert_run(text):
    """Convierte un entrenamiento de carrera al formato de Intervals.icu."""
    text_lower = text.lower()
    lines = []
    
    # ---- PATRONES ESPECÍFICOS PRIMERO (antes de los genéricos) ----
    
    # --- Patrón: Fartlek ---
    if 'fartlek' in text_lower:
        return _convert_run_fartlek(text)
    
    # --- Patrón: Cuestas ---
    if 'cuesta' in text_lower:
        return _convert_run_cuestas(text)
    
    # --- Patrón: Activación pre-carrera (con rectas) ---
    if 'activaci' in text_lower:
        return _convert_run_activacion(text)
    
    # --- Patrón: Rodaje con rectas ---
    if 'recta' in text_lower:
        return _convert_run_rectas(text)
    
    # --- Patrón: Tirada larga con segmento final ---
    if 'tirada' in text_lower or ('km' in text_lower and ('final' in text_lower or 'integrad' in text_lower)):
        return _convert_run_tirada_larga(text)
    
    # --- Patrón: Series con calentamiento ---
    if _has_calentamiento_series(text):
        return _convert_run_series(text)
    
    # ---- PATRONES GENÉRICOS (fallback) ----
    
    # --- Patrón: Rodaje puro en km ---
    m = re.match(r'(?:carrera[^:]*:\s*)?(\d+)\s*km\s+(.*)', text, re.IGNORECASE)
    if m and not _has_series(text):
        km = int(m.group(1))
        desc = m.group(2)
        zone = _extract_zone(desc)
        
        # Check for progressive ending: "últimos X km en Z3"
        prog_m = re.search(r'(?:últimos|ultimos)\s+(\d+)\s*km\s+.*?(?:en\s+)?(Z\d)', text, re.IGNORECASE)
        if prog_m:
            prog_km = int(prog_m.group(1))
            prog_zone = prog_m.group(2)
            base_km = km - prog_km
            lines.append("Warmup")
            lines.append(f"- {base_km}km {zone} Pace")
            lines.append("")
            lines.append("Main Set")
            lines.append(f"- {prog_km}km {prog_zone} Pace")
        else:
            lines.append(f"- {km}km {zone} Pace")
        return "\n".join(lines)
    
    # --- Patrón: Rodaje puro en minutos ---
    m = re.match(r'(?:carrera[^:]*:\s*)?(\d+)\s*min\s+(.*)', text, re.IGNORECASE)
    if m and not _has_series(text):
        mins = int(m.group(1))
        desc = m.group(2)
        zone = _extract_zone(desc)
        lines.append(f"- {mins}m {zone} Pace")
        return "\n".join(lines)
    
    # --- Fallback: extraer km o minutos ---
    km = _parse_km(text)
    if km:
        zone = _extract_zone(text)
        lines.append(f"- {km}km {zone} Pace")
        return "\n".join(lines)
    
    mins = _parse_duration_to_minutes(text)
    if mins:
        zone = _extract_zone(text)
        lines.append(f"- {mins}m {zone} Pace")
        return "\n".join(lines)
    
    return text


def _has_series(text):
    """Detecta si hay series tipo NxDistancia o NxTiempo."""
    return bool(re.search(r'\d+\s*[xX]\s*[\[\(]?\s*\d', text))


def _has_calentamiento_series(text):
    """Detecta el patrón: cal + series o parte principal + enf."""
    t = text.lower()
    has_cal = 'calentamiento' in t or 'cal ' in t or 'cal+' in t or 'calent' in t
    has_enf = 'enfriamiento' in t or 'enf ' in t or 'enf+' in t or 'enf' in t.split() or 'enfri' in t
    return (has_cal and has_enf) or (has_cal and (re.search(r'\d+\s*[xX]', text) is not None or 'continuo' in t or 'a fuego' in t or 'test' in t))


def _convert_run_fartlek(text):
    """Convierte un fartlek de carrera."""
    lines = []
    
    # Intentar extraer: X min Z1 + Nx[A min ZX / B min ZY] + C min Z1
    # Ej: "35 min (10 min Z1 + 8x [1 min Z3 / 1 min Z1] + 9 min Z1)"
    total = _parse_duration_to_minutes(text)
    
    # Extract warmup minutes
    warmup_m = re.search(r'(\d+)\s*min\s*(Z\d)', text)
    # Extract series: 8x [1 min Z3 / 1 min Z1]
    series_m = re.search(r'(\d+)\s*[xX]\s*[\[\(]?\s*(\d+)\s*min\s*(Z\d)\s*[/,]\s*(\d+)\s*min\s*(Z\d)', text)
    
    if warmup_m and series_m:
        w_mins = int(warmup_m.group(1))
        w_zone = warmup_m.group(2)
        
        reps = int(series_m.group(1))
        on_mins = int(series_m.group(2))
        on_zone = series_m.group(3)
        off_mins = int(series_m.group(4))
        off_zone = series_m.group(5)
        
        series_total = reps * (on_mins + off_mins)
        cooldown_mins = (total or 0) - w_mins - series_total
        if cooldown_mins < 0:
            cooldown_mins = 5
        
        lines.append("Warmup")
        lines.append(f"- {w_mins}m {w_zone} Pace")
        lines.append("")
        lines.append("Main Set")
        lines.append(f"{reps}x")
        lines.append(f"- {on_mins}m {on_zone} Pace")
        lines.append(f"- {off_mins}m {off_zone} Pace")
        
        if cooldown_mins > 0:
            lines.append("")
            lines.append("Cooldown")
            lines.append(f"- {cooldown_mins}m Z1 Pace")
    else:
        # Fallback simple
        if total:
            lines.append(f"- {total}m Z2 Pace")
        else:
            lines.append(text)
    
    return "\n".join(lines)


def _convert_run_cuestas(text):
    """Convierte entrenamiento de cuestas."""
    lines = []
    
    # Ej: "3 km cal + 8 cuestas de 150m fuertes (rec bajando andando) + 2 km enf"
    cal_m = re.search(r'(\d+)\s*km\s*(?:cal|calentamiento)', text, re.IGNORECASE)
    cuestas_m = re.search(r'(\d+)\s*cuestas?\s*(?:de\s*)?(\d+)\s*m', text, re.IGNORECASE)
    enf_m = re.search(r'(\d+)\s*km\s*(?:enf|enfriamiento)', text, re.IGNORECASE)
    
    cal_km = int(cal_m.group(1)) if cal_m else 2
    enf_km = int(enf_m.group(1)) if enf_m else 2
    
    lines.append("Warmup")
    lines.append(f"- {cal_km}km Z1 Pace")
    lines.append("")
    lines.append("Main Set")
    
    if cuestas_m:
        reps = int(cuestas_m.group(1))
        dist_m = int(cuestas_m.group(2))
        dist_km = dist_m / 1000
        lines.append(f"{reps}x")
        lines.append(f"- {dist_km}km Z4 Pace")
        lines.append(f"- {dist_km}km Z1 Pace")
    
    lines.append("")
    lines.append("Cooldown")
    lines.append(f"- {enf_km}km Z1 Pace")
    
    return "\n".join(lines)


def _convert_run_series(text):
    """Convierte series de carrera: cal + NxDist en ZX (rec Y) + enf."""
    text_lower = text.lower()
    lines = []
    
    # Extract calentamiento
    cal_m = re.search(r'(\d+)\s*km\s*(?:cal|calentamiento)', text, re.IGNORECASE)
    cal_km = int(cal_m.group(1)) if cal_m else 3
    
    # Extract enfriamiento 
    enf_m = re.search(r'(\d+)\s*km\s*(?:enf|enfriamiento)', text, re.IGNORECASE)
    enf_km = int(enf_m.group(1)) if enf_m else 2
    
    lines.append("Warmup")
    lines.append(f"- {cal_km}km Z1 Pace")
    lines.append("")
    lines.append("Main Set")
    
    # Pattern: NxDIST en ZX (rec Y)
    # Ej: 3x2.000m en Z4 (rec 2')
    # Ej: 6x1.000m Sub 4:00 (rec 1'30")
    # Ej: 6 km continuos en Z4
    # Ej: 12 km continuos a Ritmo Maratón
    
    # Try repetition pattern first: NxDIST
    rep_m = re.search(r'(\d+)\s*[xX]\s*(\d+(?:[.,]\d+)?)\s*m\s', text)
    if not rep_m:
        rep_m = re.search(r'(\d+)\s*[xX]\s*(\d+(?:[.,]\d+)?)\s*m(?:\s|$)', text)
    
    if rep_m:
        reps = int(rep_m.group(1))
        dist_m = float(rep_m.group(2).replace('.', '').replace(',', '.'))
        # If it's something like 2.000m -> 2000m, or 1.000m -> 1000m
        if dist_m < 10:
            dist_m = dist_m * 1000
        dist_km = dist_m / 1000
        
        # Get zone for the series
        zone = 'Z4'
        zone_m = re.search(r'[xX]\s*\d+.*?(Z\d)', text)
        if zone_m:
            zone = zone_m.group(1)
        elif 'sub' in text.lower() or 'fuego' in text.lower() or 'vivo' in text.lower():
            zone = 'Z5'
        elif 'umbral' in text.lower() or 'tempo' in text.lower():
            zone = 'Z4'
        elif 'marat' in text.lower():
            zone = 'Z3'
        elif 'competici' in text.lower():
            zone = 'Z4'
        
        # Recovery time
        rec_m = re.search(r"rec\s*(\d+)[''′]?\s*(?:(\d+)[\"″])?", text, re.IGNORECASE)
        if not rec_m:
            rec_m = re.search(r"recuperaci[oó]n\s*(?:de\s+)?(\d+)\s*(?:min|'|′)", text, re.IGNORECASE)
        
        rec_str = ""
        if rec_m:
            rec_mins = int(rec_m.group(1))
            rec_secs = int(rec_m.group(2)) if rec_m.lastindex and rec_m.lastindex >= 2 and rec_m.group(2) else 0
            if rec_secs > 0:
                total_secs = rec_mins * 60 + rec_secs
                rec_str = f"- {total_secs}s Z1 Pace"
            else:
                rec_str = f"- {rec_mins}m Z1 Pace"
        else:
            # Default recovery: 2 min
            rec_str = "- 2m Z1 Pace"
        
        lines.append(f"{reps}x")
        lines.append(f"- {dist_km}km {zone} Pace")
        lines.append(rec_str)
    else:
        # Try continuous pattern: X km continuos en ZX
        cont_m = re.search(r'(\d+)\s*km\s*(?:continu|a\s+Ritmo)', text[text.lower().find('calentamiento') + 10:] if 'calentamiento' in text.lower() else text, re.IGNORECASE)
        if cont_m:
            cont_km = int(cont_m.group(1))
            zone = _extract_zone(text[text.lower().find(str(cont_km)):])
            if 'marat' in text.lower():
                zone = 'Z3'
            lines.append(f"- {cont_km}km {zone} Pace")
        else:
            # Recortar el texto para quedarnos con la parte principal (entre el calentamiento y el enfriamiento)
            main_part = text
            idx_cal = text_lower.find('calentamiento')
            if idx_cal == -1:
                idx_cal = text_lower.find('cal ')
            if idx_cal != -1:
                main_part = main_part[idx_cal + 5:]
                
            idx_enf = main_part.lower().find('enfriamiento')
            if idx_enf == -1:
                idx_enf = main_part.lower().find('enf')
            if idx_enf != -1:
                main_part = main_part[:idx_enf]
                
            # Ahora buscar km en la parte principal
            main_km_m = re.search(r'(\d+(?:[.,]\d+)?)\s*km', main_part)
            if main_km_m:
                main_km = float(main_km_m.group(1).replace(',', '.'))
                if main_km.is_integer():
                    main_km = int(main_km)
                zone = _extract_zone(main_part)
                if 'fuego' in main_part.lower() or 'test' in main_part.lower():
                    zone = 'Z5'
                lines.append(f"- {main_km}km {zone} Pace")
            else:
                # Final fallback for series block
                lines.append(f"- 5km Z4 Pace")
    
    lines.append("")
    lines.append("Cooldown")
    lines.append(f"- {enf_km}km Z1 Pace")
    
    return "\n".join(lines)


def _convert_run_tirada_larga(text):
    """Convierte tirada larga con segmento final."""
    lines = []
    
    # Ej: "23 km (17 km en Z2 + 6 km finales a Ritmo Maratón)"
    # Ej: "32 km (16 km en Z2 + 16 km finales a Ritmo Maratón: 4:15)"
    total_m = re.search(r'(\d+)\s*km', text)
    total_km = int(total_m.group(1)) if total_m else 20
    
    # Look for two segments: X km Z2 + Y km Z3/Maratón
    seg_m = re.search(r'(\d+)\s*km\s+(?:en\s+)?(Z\d)\s*.*?\+\s*(\d+)\s*km\s+.*?(?:(?:en\s+)?(Z\d)|[Rr]itmo)', text)
    
    if seg_m:
        base_km = int(seg_m.group(1))
        base_zone = seg_m.group(2)
        final_km = int(seg_m.group(3))
        final_zone = seg_m.group(4) if seg_m.group(4) else 'Z3'
        
        if 'marat' in text.lower():
            final_zone = 'Z3'
        if 'vivo' in text.lower():
            final_zone = 'Z3'
        
        lines.append("Warmup")
        lines.append(f"- {base_km}km {base_zone} Pace")
        lines.append("")
        lines.append("Main Set")
        lines.append(f"- {final_km}km {final_zone} Pace")
    else:
        # Single segment tirada
        zone = _extract_zone(text)
        
        # Check for "últimos X km en Z3"
        prog_m = re.search(r'(?:últimos|ultimos)\s+(\d+)\s*km\s+(?:en\s+)?(Z\d)', text, re.IGNORECASE)
        if prog_m:
            prog_km = int(prog_m.group(1))
            prog_zone = prog_m.group(2)
            base_km = total_km - prog_km
            lines.append("Warmup")
            lines.append(f"- {base_km}km {zone} Pace")
            lines.append("")
            lines.append("Main Set")
            lines.append(f"- {prog_km}km {prog_zone} Pace")
        elif 'progresiva' in text.lower():
            base_km = int(total_km * 0.7)
            prog_km = total_km - base_km
            lines.append("Warmup")
            lines.append(f"- {base_km}km Z2 Pace")
            lines.append("")
            lines.append("Main Set")
            lines.append(f"- {prog_km}km Z3 Pace")
        else:
            lines.append(f"- {total_km}km {zone} Pace")
    
    return "\n".join(lines)


def _convert_run_rectas(text):
    """Convierte rodaje + rectas."""
    lines = []
    
    # Ej: "10 km rodaje suave Z2 + 6 rectas de 100m"
    km_m = re.search(r'(\d+)\s*km', text)
    rectas_m = re.search(r'(\d+)\s*rectas?\s*(?:de\s*)?(\d+)\s*m', text, re.IGNORECASE)
    
    base_km = int(km_m.group(1)) if km_m else 10
    zone = _extract_zone(text)
    
    lines.append("Warmup")
    lines.append(f"- {base_km}km {zone} Pace")
    lines.append("")
    lines.append("Main Set")
    
    if rectas_m:
        reps = int(rectas_m.group(1))
        dist_m = int(rectas_m.group(2))
        dist_km = dist_m / 1000
        lines.append(f"{reps}x")
        lines.append(f"- {dist_km}km Z5 Pace")
        lines.append(f"- {dist_km}km Z1 Pace")
    
    return "\n".join(lines)


def _convert_run_activacion(text):
    """Convierte activación pre-carrera."""
    lines = []
    
    km_m = re.search(r'(\d+)\s*km', text)
    km = int(km_m.group(1)) if km_m else 4
    
    rectas_m = re.search(r'(\d+)\s*rectas?\s*(?:.*?)(\d+)\s*m', text, re.IGNORECASE)
    
    lines.append("Warmup")
    lines.append(f"- {km}km Z1 Pace")
    
    if rectas_m:
        reps = int(rectas_m.group(1))
        dist_m = int(rectas_m.group(2))
        dist_km = dist_m / 1000
        lines.append("")
        lines.append("Main Set")
        lines.append(f"{reps}x")
        lines.append(f"- {dist_km}km Z4 Pace")
        lines.append(f"- {dist_km}km Z1 Pace")
    
    return "\n".join(lines)


def _convert_ride(text):
    """Convierte entrenamiento de ciclismo."""
    lines = []
    
    mins = _parse_duration_to_minutes(text)
    if not mins:
        mins = 60  # default
    
    zone = _extract_zone(text)
    
    # Simple ride: just the duration and zone
    lines.append(f"- {mins}m {zone}")
    
    return "\n".join(lines)


def _convert_swim(text):
    """Convierte entrenamiento de natación a formato legible."""
    # La natación en Intervals.icu no usa el formato estructurado de máquina,
    # se sube como descripción legible. Devolvemos el texto tal cual pero limpio.
    return text


def _convert_gym(text):
    """Convierte entrenamiento de gimnasio a formato legible (sin estructurar)."""
    return text


# =========================================
# TESTING: Convert a few sample workouts
# =========================================
if __name__ == "__main__":
    tests = [
        ("Run", "Carrera: 30 min trote muy suave en Z1."),
        ("Run", "Carrera: 14 km rodaje aeróbico en Z2."),
        ("Run", "Carrera: 11 km rodaje en Z2 con los últimos 2 km progresivos en Z3."),
        ("Run", "Carrera: Fartlek suave 35 min (10 min Z1 + 8x [1 min Z3 / 1 min Z1] + 9 min Z1)."),
        ("Run", "Carrera: 3 km calentamiento + 8 cuestas de 150m fuertes (recuperación bajando al trote muy suave) + 2 km enfriamiento."),
        ("Run", "Carrera: 3 km calentamiento + 3x2.000m en Z4 (Ritmo Umbral: ~4:00-4:05 min/km, con 2 min de recuperación al trote suave) + 2 km enfriamiento."),
        ("Run", "Carrera (Tirada Larga): 23 km (17 km en Z2 constante + 6 km finales integrados a Ritmo Maratón: 4:15 min/km)."),
        ("Run", "Carrera: 10 km rodaje suave Z2 + 6 rectas de 100m en progresión (recuperando la vuelta andando)."),
        ("Run", "Carrera (TEST 5K): 3 km calentamiento + 5 km A FUEGO (Test de ritmo) + 2 km enfriamiento."),
        ("Run", "Carrera (Activación pre-carrera): 3 km trote suave en Z1 + 4 rectas de 100m progresivas."),
        ("Run", "Carrera: 3 km calentamiento + 6x1.000m Sub 4:00 min/km (rec 1'30\" trote) + 2 km enfriamiento."),
        ("Run", "Carrera: 3 km calentamiento + 12 km continuos a Ritmo Maratón (4:15 min/km) + 2 km enfriamiento."),
        ("Run", "Carrera (Tirada Larga): 16 km en Z2 (los últimos 3 km en Z3 cómoda)."),
        ("Ride", "Ciclismo: 60 min en Z1 a cadencia alta (90+ rpm)."),
        ("Ride", "Ciclismo: 75 min rodaje Z1 en llano."),
        ("Ride", "Ciclismo: 90 min en Z2 continua."),
        ("WeightTraining", "Gimnasio: 30 min de movilidad articular y core básico."),
        ("WeightTraining", "Gimnasio: Fuerza Máxima Pesada (Piernas y Core)."),
        ("Swim", "Natación: 1.500m regenerativo (400m suave + 4x200m Z1 con 20s rec + 300m suave)."),
        ("Run", "DESCANSO TOTAL"),
        ("Run", "COMPETICIÓN: MEDIA MARATÓN DE SOFÍA (Objetivo Tipo 2)"),
    ]
    
    for sport, txt in tests:
        print(f"{'='*60}")
        print(f"SPORT: {sport}")
        print(f"INPUT: {txt}")
        print(f"OUTPUT:")
        result = convert_to_intervals_format(txt, sport)
        print(result)
        print()
