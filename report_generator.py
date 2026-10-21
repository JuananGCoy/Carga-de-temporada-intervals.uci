import pandas as pd
from datetime import datetime, timedelta
import intervals_api
import json
import os

# Mapeo de deportes, iconos y colores corporativos
SPORT_ICONS = {
    'Swim': ('Natación', '🏊‍♂️', '#06b6d4'),
    'Ride': ('Ciclismo', '🚴‍♂️', '#f97316'),
    'VirtualRide': ('Ciclismo', '🚴‍♂️', '#ea580c'),
    'Run': ('Carrera', '🏃‍♂️', '#10b981'),
    'TrailRun': ('Trail Running', '⛰️', '#059669'),
    'WeightTraining': ('Fuerza / Gimnasio', '🏋️‍♂️', '#8b5cf6'),
    'Walk': ('Caminata', '🚶‍♂️', '#64748b'),
    'Workout': ('Entrenamiento', '⚡', '#3b82f6'),
    'Other': ('Otros', '🎯', '#94a3b8')
}

def get_sport_meta(sport_type):
    return SPORT_ICONS.get(sport_type, (sport_type, '🏅', '#64748b'))

def format_sec_to_hours_mins(seconds):
    if not seconds or pd.isna(seconds):
        return "0m"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"

def format_feel(feel_val):
    """
    Formatea las sensaciones registradas en Intervals.icu (escala estándar Garmin FIT 1 a 5):
    1 = Strong (🚀 Fuerte / Con chispa)
    2 = Good (🙂 Bien / Buenas sensaciones)
    3 = Normal (😐 Normal / Estable)
    4 = Weak (😕 Débil / Pesado)
    5 = Very Weak (😞 Muy débil / Agotado)
    """
    if feel_val is None:
        return ("Sin registrar", "⚪", "#94a3b8")
    try:
        val = int(feel_val)
        if val == 1:
            return ("Fuerte / Excelente", "🚀", "#059669")
        elif val == 2:
            return ("Bien / Buenas sensaciones", "🙂", "#10b981")
        elif val == 3:
            return ("Normal / Estable", "😐", "#eab308")
        elif val == 4:
            return ("Débil / Pesado", "😕", "#f97316")
        elif val == 5:
            return ("Muy débil / Agotado", "😞", "#ef4444")
    except Exception:
        pass
    return ("Sin registrar", "⚪", "#94a3b8")

def format_rpe(rpe_val):
    """
    Formatea el Esfuerzo Percibido (RPE de 1 a 10):
    1-2: Muy suave / Regenerativo (Verde claro)
    3-4: Suave / Fondo aeróbico (Verde)
    5-6: Moderado / Tempo (Amarillo)
    7-8: Duro / Umbral (Naranja)
    9-10: Máximo / Extenuante (Rojo)
    """
    if rpe_val is None:
        return ("-", "#94a3b8")
    try:
        val = int(rpe_val)
        if val <= 2:
            return (f"{val}/10 (Muy suave)", "#10b981")
        elif val <= 4:
            return (f"{val}/10 (Suave)", "#22c55e")
        elif val <= 6:
            return (f"{val}/10 (Moderado)", "#eab308")
        elif val <= 8:
            return (f"{val}/10 (Duro)", "#f97316")
        else:
            return (f"{val}/10 (Máximo)", "#ef4444")
    except Exception:
        pass
    return (f"{rpe_val}/10", "#64748b")

def clean_athlete_comment(desc, comments):
    """
    Extrae y limpia comentarios o sensaciones escritas por el atleta,
    descartando textos técnicos automáticos de apps de clima (Klimat) o estructuras de intervalos.
    """
    if comments and str(comments).strip():
        return str(comments).strip()
    if not desc or not str(desc).strip():
        return None
    
    lines = str(desc).strip().splitlines()
    clean_lines = []
    for line in lines:
        line_str = line.strip()
        # Omitir textos de clima o generadores automáticos
        if any(w in line_str.lower() for w in ['klimatapp', 'sensación térmica', 'sensacion termica', 'humedad', 'viento desde', 'main set', 'warm up', 'cooldown']):
            continue
        if line_str.startswith('- ') and 'pace' in line_str.lower():
            continue
        if line_str:
            clean_lines.append(line_str)
            
    if clean_lines:
        res = " ".join(clean_lines)
        if len(res) > 280:
            res = res[:277] + "..."
        return res
    return None

def extract_period_zones(activities):
    """
    Agrega el tiempo en zonas de frecuencia cardíaca y potencia de las actividades del periodo.
    Consolida las métricas en 3 grandes bloques fisiológicos:
    - Base Aeróbica (Z1 - Z2): Desarrollo mitocondrial, quema de grasas y economía.
    - Ritmo Medio / Tempo (Z3): Ritmo sostenido y zona de transición.
    - Alta Intensidad / Calidad (Z4 - Z5+): Umbral anaeróbico, VO2max y potencia neuromuscular.
    """
    zone_secs = [0.0] * 7
    total_sec = 0.0
    has_zones = False

    for act in activities:
        hz = act.get('icu_hr_zone_times')
        if hz and isinstance(hz, list):
            for i, s in enumerate(hz[:7]):
                val = float(s or 0)
                zone_secs[i] += val
                total_sec += val
                if val > 0:
                    has_zones = True
        else:
            pz = act.get('icu_zone_times')
            if pz and isinstance(pz, list):
                for item in pz:
                    if isinstance(item, dict):
                        zid = str(item.get('id', '')).upper()
                        secs = float(item.get('secs', 0) or 0)
                        if secs > 0:
                            has_zones = True
                            total_sec += secs
                            if 'Z1' in zid: zone_secs[0] += secs
                            elif 'Z2' in zid: zone_secs[1] += secs
                            elif 'Z3' in zid: zone_secs[2] += secs
                            elif 'Z4' in zid: zone_secs[3] += secs
                            elif 'Z5' in zid: zone_secs[4] += secs
                            elif 'Z6' in zid: zone_secs[5] += secs
                            elif 'Z7' in zid: zone_secs[6] += secs

    z1 = zone_secs[0]
    z2 = zone_secs[1]
    z3 = zone_secs[2]
    z4 = zone_secs[3]
    z5_plus = zone_secs[4] + zone_secs[5] + zone_secs[6]

    low_sec = z1 + z2
    mid_sec = z3
    high_sec = z4 + z5_plus
    total_consolidated = low_sec + mid_sec + high_sec

    if total_consolidated > 0:
        low_pct = round((low_sec / total_consolidated) * 100.0, 1)
        mid_pct = round((mid_sec / total_consolidated) * 100.0, 1)
        high_pct = round((high_sec / total_consolidated) * 100.0, 1)
    else:
        low_pct = 0.0
        mid_pct = 0.0
        high_pct = 0.0

    return {
        "has_zones": has_zones,
        "total_hours": round(total_consolidated / 3600.0, 1),
        "low_hours": round(low_sec / 3600.0, 1),
        "mid_hours": round(mid_sec / 3600.0, 1),
        "high_hours": round(high_sec / 3600.0, 1),
        "low_pct": low_pct,
        "mid_pct": mid_pct,
        "high_pct": high_pct
    }

def match_workouts_in_period(athlete_id, api_key, start_date, end_date, is_coach=False):
    """
    Compara los entrenamientos programados (WORKOUT) con las actividades reales en el rango de fechas.
    Determina qué se ha completado, qué se ha saltado y qué sesiones fueron adicionales.
    Extrae Feel, RPE y comentarios reales de cada sesión.
    """
    success_ev, events = intervals_api.get_athlete_events(athlete_id, api_key, start_date, end_date, is_coach=is_coach)
    success_act, activities = intervals_api.get_athlete_activities(athlete_id, api_key, start_date, end_date, is_coach=is_coach)

    events_list = events if success_ev and isinstance(events, list) else []
    act_list = activities if success_act and isinstance(activities, list) else []

    planned_workouts = [e for e in events_list if e.get('category') == 'WORKOUT']

    completed = []
    skipped = []
    extra = []
    matched_activity_ids = set()

    def sport_matches(sport1, sport2):
        s1 = str(sport1).lower().strip()
        s2 = str(sport2).lower().strip()
        if s1 == s2:
            return True
        if s1 in ['ride', 'virtualride'] and s2 in ['ride', 'virtualride']:
            return True
        if s1 in ['run', 'trailrun'] and s2 in ['run', 'trailrun']:
            return True
        if s1 in ['weighttraining', 'gym', 'workout'] and s2 in ['weighttraining', 'gym', 'workout']:
            return True
        return False

    for p in planned_workouts:
        p_date = str(p.get('start_date_local', ''))[:10]
        p_type = p.get('type', 'Workout')
        p_id = p.get('id')
        p_name = p.get('name', 'Entrenamiento planificado')

        match = None
        for a in act_list:
            if a.get('paired_event_id') == p_id:
                match = a
                break

        if not match:
            for a in act_list:
                if a.get('id') not in matched_activity_ids:
                    a_date = str(a.get('start_date_local', ''))[:10]
                    a_type = a.get('type', '')
                    if a_date == p_date and sport_matches(a_type, p_type):
                        match = a
                        break

        if match:
            matched_activity_ids.add(match.get('id'))
            completed.append({
                "date": p_date,
                "sport": p_type,
                "planned_name": p_name,
                "actual_name": match.get('name', p_name),
                "duration_str": format_sec_to_hours_mins(match.get('moving_time', 0)),
                "moving_time": match.get('moving_time', 0),
                "distance_km": round((match.get('distance', 0) or 0) / 1000.0, 2),
                "tss": int(match.get('icu_training_load', 0) or 0),
                "avg_hr": int(match.get('average_heartrate', 0) or 0),
                "feel": match.get('feel'),
                "rpe": match.get('icu_rpe') or match.get('perceived_exertion'),
                "comment": clean_athlete_comment(match.get('description'), match.get('icu_athlete_comments')),
                "raw_activity": match
            })
        else:
            skipped.append({
                "date": p_date,
                "sport": p_type,
                "planned_name": p_name,
                "description": p.get('description', '')
            })

    for a in act_list:
        if a.get('id') not in matched_activity_ids:
            extra.append({
                "date": str(a.get('start_date_local', ''))[:10],
                "sport": a.get('type', 'Workout'),
                "actual_name": a.get('name', 'Sesión adicional'),
                "duration_str": format_sec_to_hours_mins(a.get('moving_time', 0)),
                "moving_time": a.get('moving_time', 0),
                "distance_km": round((a.get('distance', 0) or 0) / 1000.0, 2),
                "tss": int(a.get('icu_training_load', 0) or 0),
                "avg_hr": int(a.get('average_heartrate', 0) or 0),
                "feel": a.get('feel'),
                "rpe": a.get('icu_rpe') or a.get('perceived_exertion'),
                "comment": clean_athlete_comment(a.get('description'), a.get('icu_athlete_comments')),
                "raw_activity": a
            })

    total_planned = len(planned_workouts)
    completed_count = len(completed)
    skipped_count = len(skipped)
    extra_count = len(extra)

    compliance_pct = round((completed_count / total_planned * 100.0), 1) if total_planned > 0 else 100.0
    total_duration_sec = sum(a.get('moving_time', 0) or 0 for a in act_list)
    total_tss = sum(int(a.get('icu_training_load', 0) or 0) for a in act_list)
    total_hours = round(total_duration_sec / 3600.0, 1)

    sports_breakdown = {}
    for a in act_list:
        sp = a.get('type', 'Other')
        name, icon, color = get_sport_meta(sp)
        if name not in sports_breakdown:
            sports_breakdown[name] = {"icon": icon, "color": color, "hours": 0.0, "km": 0.0, "tss": 0}
        sports_breakdown[name]["hours"] += (a.get('moving_time', 0) or 0) / 3600.0
        sports_breakdown[name]["km"] += (a.get('distance', 0) or 0) / 1000.0
        sports_breakdown[name]["tss"] += int(a.get('icu_training_load', 0) or 0)

    for k in sports_breakdown:
        sports_breakdown[k]["hours"] = round(sports_breakdown[k]["hours"], 1)
        sports_breakdown[k]["km"] = round(sports_breakdown[k]["km"], 1)
        sports_breakdown[k]["pct"] = round((sports_breakdown[k]["hours"] / total_hours * 100.0), 1) if total_hours > 0 else 0.0

    # Detección de la Sesión Estrella
    star_session = None
    if act_list:
        best_act = max(act_list, key=lambda x: (float(x.get('icu_training_load', 0) or 0), float(x.get('moving_time', 0) or 0)))
        sp_name, sp_icon, sp_col = get_sport_meta(best_act.get('type', 'Workout'))
        star_session = {
            "name": best_act.get('name', 'Entrenamiento clave'),
            "sport": sp_name,
            "icon": sp_icon,
            "color": sp_col,
            "date": str(best_act.get('start_date_local', ''))[:10],
            "duration_str": format_sec_to_hours_mins(best_act.get('moving_time', 0)),
            "distance_km": round((best_act.get('distance', 0) or 0) / 1000.0, 1),
            "tss": int(best_act.get('icu_training_load', 0) or 0),
            "avg_hr": int(best_act.get('average_heartrate', 0) or 0),
            "feel": best_act.get('feel'),
            "rpe": best_act.get('icu_rpe') or best_act.get('perceived_exertion'),
            "comment": clean_athlete_comment(best_act.get('description'), best_act.get('icu_athlete_comments'))
        }

    zones_data = extract_period_zones(act_list)

    return {
        "completed": completed,
        "skipped": skipped,
        "extra": extra,
        "total_planned": total_planned,
        "completed_count": completed_count,
        "skipped_count": skipped_count,
        "extra_count": extra_count,
        "compliance_pct": compliance_pct,
        "total_hours": total_hours,
        "total_tss": total_tss,
        "sports_breakdown": sports_breakdown,
        "star_session": star_session,
        "zones_data": zones_data,
        "raw_activities": act_list
    }

def get_wellness_summary(athlete_id, api_key, start_date, end_date, is_coach=False):
    """
    Obtiene la evolución de CTL, ATL, TSB y Rampa durante el periodo.
    """
    success_well, wellness = intervals_api.get_athlete_wellness(athlete_id, api_key, start_date, end_date, is_coach=is_coach)
    if not success_well or not isinstance(wellness, list) or len(wellness) == 0:
        return {"current_ctl": 0, "current_atl": 0, "current_tsb": 0, "ctl_delta": 0, "ramp_rate": 0}

    df_w = pd.DataFrame(wellness)
    for col in ['ctl', 'atl', 'rampRate']:
        if col in df_w.columns:
            df_w[col] = pd.to_numeric(df_w[col], errors='coerce').fillna(0)

    first_row = df_w.iloc[0]
    last_row = df_w.iloc[-1]

    start_ctl = float(first_row.get('ctl', 0) or 0)
    end_ctl = float(last_row.get('ctl', 0) or 0)
    end_atl = float(last_row.get('atl', 0) or 0)
    end_tsb = end_ctl - end_atl
    ramp = float(last_row.get('rampRate', 0) or 0)

    return {
        "start_ctl": round(start_ctl, 1),
        "end_ctl": round(end_ctl, 1),
        "ctl_delta": round(end_ctl - start_ctl, 1),
        "current_atl": round(end_atl, 1),
        "current_tsb": round(end_tsb, 1),
        "ramp_rate": round(ramp, 1)
    }

def get_upcoming_races(athlete_id, api_key, is_coach=False):
    """
    Obtiene las carreras y competiciones programadas en los próximos 60 días.
    """
    today = datetime.now()
    now_str = today.strftime("%Y-%m-%d")
    future_str = (today + timedelta(days=60)).strftime("%Y-%m-%d")

    success_ev, events = intervals_api.get_athlete_events(athlete_id, api_key, now_str, future_str, is_coach=is_coach)
    if not success_ev or not isinstance(events, list):
        return []

    races = []
    for e in events:
        cat = str(e.get('category', '')).upper()
        if 'RACE' in cat or 'competi' in str(e.get('name', '')).lower():
            d_str = str(e.get('start_date_local', ''))[:10]
            try:
                d_date = datetime.strptime(d_str, "%Y-%m-%d")
                days_left = (d_date.date() - today.date()).days
                if days_left >= 0:
                    races.append({
                        "name": e.get('name', 'Competición'),
                        "date_str": d_date.strftime("%d/%m/%Y"),
                        "category": cat,
                        "days_left": days_left
                    })
            except Exception:
                pass
    return sorted(races, key=lambda x: x['days_left'])

def analyze_key_sessions(activities):
    """
    Clasifica y realiza una revisión técnica y calculada de las sesiones clave del periodo:
    - Competición / Carrera
    - Tirada Larga / Fondo
    - Sesión de Calidad / Series / Umbral
    - Fuerza / Prevención
    - Sesión con Sensaciones Extremas (Feel 5 o Feel 1-2)
    Cruza los datos fisiológicos (ritmo, FC, TSS) con las sensaciones reportadas (Feel y RPE).
    """
    if not activities:
        return []

    scored_acts = []
    for a in activities:
        name = str(a.get('name', ''))
        sport = str(a.get('type', 'Workout'))
        moving_time = float(a.get('moving_time', 0) or 0)
        dist_km = round((float(a.get('distance', 0) or 0)) / 1000.0, 1)
        tss = int(a.get('icu_training_load', 0) or 0)
        avg_hr = int(a.get('average_heartrate', 0) or 0)
        feel = a.get('feel')
        rpe = a.get('icu_rpe') or a.get('perceived_exertion')
        comment = clean_athlete_comment(a.get('description'), a.get('icu_athlete_comments'))
        date_str = str(a.get('start_date_local', ''))[:10]

        # Clasificación de tipo de sesión
        name_lower = name.lower()
        is_race = any(w in name_lower for w in ['maratón', 'maraton', 'media maratón', 'media maraton', '10k', '5k', 'triatlón', 'triatlon', 'competi']) or (rpe is not None and int(rpe) == 10 and dist_km >= 10)
        is_long = dist_km >= 16.0 or moving_time >= 5400 or any(w in name_lower for w in ['tirada', 'largo', 'fondo', '20k', '25k', '30k'])
        is_quality = any(w in name_lower for w in ['series', 'interval', 'rm', 'tempo', 'progresivo', 'umbral', 'fartlek', 'rectas']) or (moving_time > 0 and (tss / (moving_time / 3600.0) >= 65))
        is_gym = sport in ['WeightTraining'] or any(w in name_lower for w in ['fuerza', 'gimnasio', 'gym', 'prehab', 'core', 'pesas'])
        is_recovery = any(w in name_lower for w in ['regenerativo', 'recuperación', 'recuperacion', 'descarga', 'shakeout', 'trote'])

        # Diagnóstico técnico calculado
        verdict = ""
        feel_label, feel_emoji, _ = format_feel(feel)
        rpe_label, _ = format_rpe(rpe)

        if is_race:
            tag = "🏆 Competición / Test"
            verdict = f"Esfuerzo máximo en competición. "
            if rpe:
                verdict += f"Dificultad reportada: {rpe}/10. "
            if avg_hr > 0:
                verdict += f"Frecuencia cardíaca media de {avg_hr} ppm, manteniendo la intensidad en zona de rendimiento. "
            if feel in [1, 2]:
                verdict += "Excelente asimilación del ritmo competitivo."
            elif feel in [4, 5]:
                verdict += "Reportaste fatiga o pesadez durante la prueba; analizaremos si faltó avituallamiento o descarga previa."
        elif is_long:
            tag = "🏃‍♂️ Tirada Larga / Volumen Clave"
            verdict = f"Pilar de resistencia aeróbica del microciclo ({dist_km} km | {format_sec_to_hours_mins(moving_time)}). "
            if rpe and int(rpe) >= 8:
                verdict += f"Percibido como muy exigente ({rpe}/10). "
                if feel in [4, 5]:
                    verdict += "La combinación de RPE alto y malas sensaciones indica fatiga residual acumulada o falta de carbohidratos intra-entreno."
                else:
                    verdict += "Esfuerzo duro pero normal debido a la carga de kilómetros sobre las piernas."
            elif feel in [1, 2]:
                verdict += f"Sensaciones excelentes ({feel_emoji} {feel_label}). Tu capacidad de mantener el pulso ({avg_hr} ppm) sin deriva cardíaca demuestra que el fondo aeróbico está en un gran momento."
            else:
                verdict += f"Rodaje completado con solvencia ({tss} TSS)."
        elif is_quality:
            tag = "⚡ Sesión de Ritmo / Calidad"
            verdict = f"Trabajo de potencia y umbral. "
            if feel == 1:
                verdict += f"¡Sensaciones sobresalientes ({feel_emoji})! Terminar un entrenamiento de calidad con chispa confirma que la frescura y la activación neuromuscular están al 100%."
            elif feel in [4, 5] or (rpe and int(rpe) >= 8):
                verdict += f"Reportaste alta dificultad ({rpe}/10) y pesadez ({feel_label}). Las piernas llegaron cargadas; en estos días es vital no obsesionarse con el cronómetro y priorizar la técnica."
            else:
                verdict += f"Estímulo bien digerido ({tss} TSS, FC media {avg_hr} ppm)."
        elif is_gym:
            tag = "🏋️‍♂️ Fuerza & Resiliencia Muscular"
            verdict = f"Sesión fundamental para proteger rodillas, sóleos y cadera. Clave para transferir fuerza a la zancada y evitar sobrecargas articulares en las tiradas largas."
        elif is_recovery:
            tag = "🌱 Regenerativo / Descarga"
            if rpe and int(rpe) >= 6:
                verdict = f"⚠️ Alerta: Un regenerativo no debería sentirse a {rpe}/10. Si el cuerpo te pide esfuerzo para rodar suave, el sistema nervioso está pidiendo más descanso o menos ritmo."
            else:
                verdict = f"Recuperación activa impecable ({rpe_label}). Permitió el vaciado de fatiga sin añadir estrés muscular."
        else:
            tag = "🎯 Rodaje de Base"
            verdict = f"Consolidación de kilómetros aeróbicos a {avg_hr} ppm."

        scored_acts.append({
            "name": name,
            "sport": sport,
            "date": date_str,
            "moving_time": moving_time,
            "duration_str": format_sec_to_hours_mins(moving_time),
            "distance_km": dist_km,
            "tss": tss,
            "avg_hr": avg_hr,
            "feel": feel,
            "rpe": rpe,
            "comment": comment,
            "tag": tag,
            "verdict": verdict,
            "priority": 5 if is_race else (4 if is_long else (3 if is_quality else (2 if is_gym else 1)))
        })

    # Ordenar por prioridad (carreras > tiradas largas > calidad > fuerza) y luego por fecha más reciente
    sorted_sessions = sorted(scored_acts, key=lambda x: (x['priority'], x['tss']), reverse=True)
    return sorted_sessions[:4]

def generate_coach_feedback_questions(key_sessions, wellness_data, skipped_count, athlete_name="Deportista"):
    """
    Genera 2 o 3 preguntas calculadas, precisas y personalizadas para el deportista,
    abriendo un canal de comunicación real sobre sensaciones, fatiga o dolores.
    """
    questions = []

    # 1. Pregunta sobre sensaciones en sesiones con RPE alto o Feel débil/agotado (4 o 5 en Intervals)
    hard_session = next((s for s in key_sessions if (s.get('rpe') and int(s.get('rpe')) >= 8) or s.get('feel') in [4, 5]), None)
    if hard_session:
        date_fmt = datetime.strptime(hard_session['date'], '%Y-%m-%d').strftime('%d/%m')
        comm_note = f" (comentaste: '_{hard_session['comment']}_')" if hard_session.get('comment') else ""
        questions.append(
            f"En la sesión del **{date_fmt} ({hard_session['name']})** reportaste un esfuerzo elevado ({hard_session['rpe']}/10) y sensaciones de pesadez{comm_note}: "
            f"¿Notaste alguna sobrecarga muscular localizada (gemelos, isquios, rodilla) o fue fatiga puramente energética/cardiovascular?"
        )

    # 2. Pregunta sobre la tirada larga
    long_session = next((s for s in key_sessions if "Tirada Larga" in s.get('tag', '') or s.get('distance_km', 0) >= 18), None)
    if long_session:
        date_fmt = datetime.strptime(long_session['date'], '%Y-%m-%d').strftime('%d/%m')
        questions.append(
            f"Durante los **{long_session['distance_km']} km del {date_fmt}**: "
            f"¿Cómo sentiste la energía en los últimos 4-5 km? ¿Tomaste geles/carbohidratos según lo previsto o sentiste bajón de ritmo al final?"
        )

    # 3. Pregunta sobre sesiones saltadas
    if skipped_count > 0 and len(questions) < 3:
        questions.append(
            f"Esta semana quedaron **{skipped_count} entrenamiento(s) sin registrar**: "
            f"¿Ha sido por falta de tiempo de agenda o porque el cuerpo te pedía parar por cansancio? Cuéntame para ajustar las cargas del próximo bloque."
        )

    # 4. Pregunta general si no hay alertas
    if len(questions) < 2:
        questions.append(
            "¿Cómo sientes las piernas a nivel de tono muscular general y qué tal ha sido tu descanso nocturno estos días?"
        )

    return questions

def analyze_training_insights(match_data, wellness_data, report_type="weekly", athlete_name="Deportista"):
    """
    Motor integral de análisis fisiológico, sensaciones y retroalimentación técnica.
    """
    comp = match_data['compliance_pct']
    total_hours = match_data['total_hours']
    total_tss = match_data['total_tss']
    sports = match_data['sports_breakdown']
    zones = match_data['zones_data']
    tsb = wellness_data['current_tsb']
    ctl = wellness_data['end_ctl']
    delta_ctl = wellness_data['ctl_delta']
    raw_acts = match_data.get('raw_activities', [])

    # Análisis exhaustivo de sesiones clave
    key_sessions = analyze_key_sessions(raw_acts)

    # Balance de sensaciones del periodo
    feels_reported = [int(a.get('feel')) for a in raw_acts if a.get('feel') is not None]
    rpes_reported = [int(a.get('icu_rpe') or a.get('perceived_exertion')) for a in raw_acts if (a.get('icu_rpe') or a.get('perceived_exertion')) is not None]

    strong_count = sum(1 for f in feels_reported if f in [4, 5])
    tired_count = sum(1 for f in feels_reported if f in [1, 2])
    avg_rpe = round(sum(rpes_reported) / len(rpes_reported), 1) if rpes_reported else None

    # Preguntas de feedback específicas
    feedback_questions = generate_coach_feedback_questions(key_sessions, wellness_data, match_data['skipped_count'], athlete_name)

    # Adaptaciones fisiológicas trabajadas
    what_worked = []
    if zones['has_zones'] and zones['low_pct'] >= 65:
        what_worked.append({
            "icon": "🫀",
            "title": "Motor Aeróbico y Densidad Mitocondrial (Zona 1 - 2)",
            "desc": f"Invertiste {zones['low_hours']}h ({zones['low_pct']}% del total) en ritmo submáximo. Esta franja enseña a tu metabolismo a ahorrar glucógeno utilizando ácidos grasos libres, clave para no desfallecer en distancias medias y largas."
        })
    elif total_hours > 0:
        what_worked.append({
            "icon": "🫀",
            "title": "Base Cardiovascular y Eficiencia",
            "desc": f"Sumaste {total_hours} horas en movimiento, manteniendo la permeabilidad capilar y la base aeróbica requerida para tolerar cargas superiores."
        })

    gym_info = sports.get('Fuerza / Gimnasio')
    if gym_info and gym_info['hours'] > 0:
        what_worked.append({
            "icon": "🏋️‍♂️",
            "title": "Fuerza Estructural y Prevención",
            "desc": f"Completaste {gym_info['hours']}h de trabajo de fuerza. Esta disciplina previene la fatiga excéntrica de cuádriceps y gemelos en las bajadas y en la segunda mitad de la tirada larga."
        })

    if zones['has_zones'] and zones['high_pct'] >= 10:
        what_worked.append({
            "icon": "⚡",
            "title": "Capacidad Glucolítica y Ritmo de Competición (Zonas 4 y 5)",
            "desc": f"Dedicaste {zones['high_hours']}h ({zones['high_pct']}%) a intensidades vivas, entrenando la velocidad de reciclaje de lactato cuando se rueda a ritmos exigentes."
        })

    # Puntos fuertes consolidados
    strengths = []
    if comp >= 85:
        strengths.append(f"🎯 **Cumplimiento del {comp}%:** Capacidad de seguir el plan semana tras semana sin altibajos.")
    if strong_count > 0:
        strengths.append(f"🚀 **Sensaciones de chispa:** En {strong_count} sesión(es) reportaste sensaciones de fuerza y soltura en las piernas.")
    if zones['has_zones'] and zones['low_pct'] >= 70:
        strengths.append(f"🟢 **Disciplina en rodajes suaves:** El {zones['low_pct']}% del tiempo se mantuvo en zonas controladas sin caer en sobreintensidad inútil.")
    if report_type == "monthly" and delta_ctl > 0:
        strengths.append(f"📈 **Progresión de condición física:** Incremento de **+{delta_ctl} puntos CTL**, alcanzando un fitness de {ctl}.")

    if not strengths:
        strengths.append("✅ **Regularidad básica mantenida:** Mantienes el hábito deportivo activo para el siguiente ciclo.")

    # Recomendaciones directas del entrenador
    recommendations = []
    if tsb < -25:
        recommendations.append(
            f"🛑 **Priorizar asimilación y descanso (TSB: {tsb}):** La fatiga aguda está en zona roja. Los próximos 2-3 días deben ser de rodaje muy suave o descanso activo. Come bien y duerme al menos 7.5h."
        )
    elif -25 <= tsb <= -5:
        recommendations.append(
            f"🚀 **Ventana productiva ideal (TSB: {tsb}):** Tu cuerpo tolera perfectamente los entrenamientos. Momento propicio para meter el siguiente estímulo planificado con confianza."
        )
    elif 5 <= tsb <= 25:
        recommendations.append(
            f"🏆 **Frescura competitiva (TSB: +{tsb}):** Poca fatiga acumulada. Si tienes competición o test de ritmo próximo, las piernas están listas para rendir."
        )
    else:
        recommendations.append(
            f"⚖️ **Semana de baja fatiga (TSB: +{tsb}):** Es momento de reactivar progresivamente el volumen para que la condición física (CTL) no se estanque."
        )

    if match_data['skipped_count'] > 0:
        recommendations.append(
            f"📋 **No intentes doblar entrenamientos:** Por los {match_data['skipped_count']} entrenamiento(s) que quedaron pendientes, no fuerces sesiones dobles. Habla conmigo y reajustamos el plan."
        )

    return {
        "key_sessions": key_sessions,
        "feels_reported": feels_reported,
        "strong_count": strong_count,
        "tired_count": tired_count,
        "avg_rpe": avg_rpe,
        "feedback_questions": feedback_questions,
        "what_worked": what_worked,
        "strengths": strengths,
        "recommendations": recommendations
    }

def build_report_html(athlete_name, report_type, start_date, end_date, match_data, wellness_data, upcoming_races, recommendations=None, coach_name="Juanan Coy - Entrenador"):
    """
    Construye el documento HTML del correo electrónico con diseño profesional,
    revisión exhaustiva sesión a sesión, análisis de Feel/RPE y bloque de llamada a feedback.
    """
    title_label = "INFORME SEMANAL DE RENDIMIENTO" if report_type == "weekly" else "BALANCE MENSUAL DE ENTRENAMIENTO"
    period_label = f"{datetime.strptime(start_date, '%Y-%m-%d').strftime('%d %b')} al {datetime.strptime(end_date, '%Y-%m-%d').strftime('%d %b %Y')}"

    insights = analyze_training_insights(match_data, wellness_data, report_type, athlete_name)
    if not recommendations:
        recommendations = insights['recommendations']

    comp = match_data['compliance_pct']
    comp_color = "#10b981" if comp >= 80 else ("#f59e0b" if comp >= 65 else "#ef4444")
    comp_badge = "¡Excelente disciplina!" if comp >= 85 else ("Buen cumplimiento" if comp >= 70 else "Atención al plan")

    tsb = wellness_data['current_tsb']
    tsb_color = "#10b981" if -25 <= tsb <= 10 else ("#ef4444" if tsb < -25 else "#3b82f6")
    tsb_badge = "Asimilando óptimo" if -25 <= tsb <= -5 else ("Fresco / Competitivo" if tsb > 0 else "Fatiga acumulada")

    # 1. RESUMEN DE PERCEPCIÓN DE ESFUERZO (RPE Y FEEL)
    rpe_summary_html = ""
    if insights['avg_rpe'] is not None or insights['strong_count'] > 0:
        rpe_txt = f"<strong>{insights['avg_rpe']} / 10</strong>" if insights['avg_rpe'] else "-"
        rpe_summary_html = f"""
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; margin-top: 10px; font-size: 12.5px; color: #334155;">
            📊 <strong>Sensaciones del Periodo:</strong> Esfuerzo medio percibido: {rpe_txt} &nbsp;|&nbsp; 
            🚀 <strong>{insights['strong_count']}</strong> sesión(es) con sensaciones de fuerza &nbsp;|&nbsp; 
            ⚠️ <strong>{insights['tired_count']}</strong> sesión(es) con pesadez/fatiga
        </div>
        """

    # 2. TARJETAS DE SESIONES CLAVE (ANÁLISIS CALCULADO Y EXHAUSTIVO)
    key_sessions_html = ""
    for s in insights['key_sessions']:
        _, s_icon, s_color = get_sport_meta(s['sport'])
        feel_label, feel_emoji, feel_color = format_feel(s.get('feel'))
        rpe_label, rpe_color = format_rpe(s.get('rpe'))
        date_fmt = datetime.strptime(s['date'], '%Y-%m-%d').strftime('%d/%m')

        dist_txt = f" • 📏 <strong>{s['distance_km']} km</strong>" if s['distance_km'] > 0 else ""
        hr_txt = f" • ❤️ <strong>{s['avg_hr']} ppm</strong>" if s['avg_hr'] > 0 else ""
        comm_box = f"""
        <div style="background-color: #f1f5f9; border-left: 3px solid #64748b; padding: 6px 10px; margin: 8px 0; font-size: 12px; color: #334155; font-style: italic;">
            🗣️ <strong>Tu comentario:</strong> "{s['comment']}"
        </div>
        """ if s.get('comment') else ""

        key_sessions_html += f"""
        <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="font-size: 11px; text-transform: uppercase; font-weight: 800; color: #0284c7; letter-spacing: 0.5px;">
                    {s['tag']} • {date_fmt}
                </span>
                <span style="font-size: 12px; font-weight: 700; color: #2563eb; background-color: #eff6ff; padding: 2px 8px; border-radius: 4px;">
                    {s['tss']} TSS
                </span>
            </div>
            <div style="font-size: 15px; font-weight: 800; color: #0f172a; margin-bottom: 4px;">
                {s_icon} {s['name']}
            </div>
            <div style="font-size: 12.5px; color: #475569; margin-bottom: 6px;">
                ⏱️ <strong>{s['duration_str']}</strong>{dist_txt}{hr_txt}
            </div>
            
            <!-- BADGES DE SENSACIONES Y ESFUERZO -->
            <div style="margin: 6px 0 8px 0;">
                <span style="display: inline-block; background-color: #f8fafc; border: 1px solid {feel_color}; color: #0f172a; font-size: 11.5px; font-weight: 600; padding: 3px 8px; border-radius: 6px; margin-right: 6px;">
                    Sensación: {feel_emoji} {feel_label}
                </span>
                <span style="display: inline-block; background-color: #f8fafc; border: 1px solid {rpe_color}; color: #0f172a; font-size: 11.5px; font-weight: 600; padding: 3px 8px; border-radius: 6px;">
                    Esfuerzo (RPE): <strong style="color: {rpe_color};">{rpe_label}</strong>
                </span>
            </div>
            
            {comm_box}
            
            <div style="font-size: 12.5px; color: #334155; line-height: 1.45; border-top: 1px dashed #e2e8f0; padding-top: 6px; margin-top: 6px;">
                🔍 <strong>Análisis del entrenador:</strong> {s['verdict']}
            </div>
        </div>
        """

    # 3. PREGUNTAS CLAVE DEL ENTRENADOR (PETICIÓN ACTIVA DE FEEDBACK)
    questions_html = ""
    for q in insights['feedback_questions']:
        questions_html += f"<li style='margin-bottom: 8px; font-size: 13px; line-height: 1.45; color: #1e293b;'>{q}</li>"

    # 4. BARRAS DE DISTRIBUCIÓN POR DEPORTE
    sports_bars_html = ""
    for sp_name, sp_info in match_data['sports_breakdown'].items():
        km_text = f" • {sp_info['km']} km" if sp_info['km'] > 0 else ""
        sports_bars_html += f"""
        <div style="margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; font-size: 12.5px; margin-bottom: 4px; color: #334155;">
                <span><strong>{sp_info['icon']} {sp_name}</strong>{km_text}</span>
                <span style="font-weight: 700; color: #0f172a;">{sp_info['hours']}h ({sp_info.get('pct', 0)}%)</span>
            </div>
            <div style="background-color: #e2e8f0; border-radius: 6px; height: 10px; overflow: hidden;">
                <div style="background-color: {sp_info['color']}; height: 100%; width: {min(100, max(4, sp_info.get('pct', 0)))}%; border-radius: 6px;"></div>
            </div>
        </div>
        """

    # 5. BARRA DE ZONAS DE INTENSIDAD (POLARIZADA)
    zones = match_data['zones_data']
    zones_visual_html = ""
    if zones['has_zones']:
        zones_visual_html = f"""
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; margin-top: 15px;">
            <div style="font-size: 13px; font-weight: 700; color: #0f172a; margin-bottom: 6px;">
                ⚡ Distribución de Intensidad (Modelo Polarizado):
            </div>
            <div style="display: flex; height: 16px; border-radius: 8px; overflow: hidden; background-color: #e2e8f0; margin-bottom: 8px;">
                <div style="background-color: #10b981; width: {zones['low_pct']}%;" title="Base Z1-Z2: {zones['low_pct']}%"></div>
                <div style="background-color: #f59e0b; width: {zones['mid_pct']}%;" title="Tempo Z3: {zones['mid_pct']}%"></div>
                <div style="background-color: #ef4444; width: {zones['high_pct']}%;" title="Alta Intensidad Z4-Z5: {zones['high_pct']}%"></div>
            </div>
            <table width="100%" border="0" cellpadding="0" cellspacing="0" style="font-size: 11.5px; color: #475569;">
                <tr>
                    <td width="33%"><span style="color: #10b981; font-weight: bold;">● Base (Z1-Z2):</span> {zones['low_pct']}% ({zones['low_hours']}h)</td>
                    <td width="33%" style="text-align: center;"><span style="color: #f59e0b; font-weight: bold;">● Tempo (Z3):</span> {zones['mid_pct']}% ({zones['mid_hours']}h)</td>
                    <td width="33%" style="text-align: right;"><span style="color: #ef4444; font-weight: bold;">● Alta (Z4-Z5):</span> {zones['high_pct']}% ({zones['high_hours']}h)</td>
                </tr>
            </table>
        </div>
        """

    # 6. QUÉ HAS TRABAJADO (BLOQUES FISIOLÓGICOS)
    what_worked_html = ""
    for item in insights['what_worked']:
        what_worked_html += f"""
        <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px; margin-bottom: 8px;">
            <div style="font-size: 13.5px; font-weight: 700; color: #1e3a8a; margin-bottom: 4px;">
                {item['icon']} {item['title']}
            </div>
            <div style="font-size: 12.5px; color: #475569; line-height: 1.45;">
                {item['desc']}
            </div>
        </div>
        """

    # 7. TABLA DE ENTRENAMIENTOS REALIZADOS
    completed_rows = ""
    for c in match_data['completed']:
        _, icon, _ = get_sport_meta(c['sport'])
        dist_str = f"{c['distance_km']} km" if c['distance_km'] > 0 else "-"
        hr_str = f"{c['avg_hr']} ppm" if c['avg_hr'] > 0 else "-"
        feel_l, feel_e, _ = format_feel(c.get('feel'))
        rpe_l, _ = format_rpe(c.get('rpe'))
        rpe_short = f"{c.get('rpe')}/10" if c.get('rpe') else "-"
        completed_rows += f"""
        <tr style="border-bottom: 1px solid #f1f5f9;">
            <td style="padding: 8px 10px; font-weight: 600; color: #334155; font-size: 12px;">{datetime.strptime(c['date'], '%Y-%m-%d').strftime('%d/%m')}</td>
            <td style="padding: 8px 10px; font-size: 12px;">{icon} {c['sport']}</td>
            <td style="padding: 8px 10px; font-size: 12px; color: #0f172a; font-weight: 500;">{c['actual_name']}</td>
            <td style="padding: 8px 10px; font-size: 12px; color: #475569;">{c['duration_str']}</td>
            <td style="padding: 8px 10px; font-size: 12px; color: #475569;">{dist_str}</td>
            <td style="padding: 8px 10px; font-size: 12px; font-weight: 700; color: #2563eb;">{c['tss']}</td>
            <td style="padding: 8px 10px; font-size: 11.5px; text-align: center;">{feel_e} {rpe_short}</td>
        </tr>
        """

    for e in match_data['extra']:
        _, icon, _ = get_sport_meta(e['sport'])
        dist_str = f"{e['distance_km']} km" if e['distance_km'] > 0 else "-"
        feel_l, feel_e, _ = format_feel(e.get('feel'))
        rpe_short = f"{e.get('rpe')}/10" if e.get('rpe') else "-"
        completed_rows += f"""
        <tr style="border-bottom: 1px solid #f1f5f9; background-color: #fafafa;">
            <td style="padding: 8px 10px; font-weight: 600; color: #64748b; font-size: 12px;">{datetime.strptime(e['date'], '%Y-%m-%d').strftime('%d/%m')}</td>
            <td style="padding: 8px 10px; font-size: 12px;">{icon} {e['sport']}</td>
            <td style="padding: 8px 10px; font-size: 12px; color: #334155;">{e['actual_name']}</td>
            <td style="padding: 8px 10px; font-size: 12px; color: #475569;">{e['duration_str']}</td>
            <td style="padding: 8px 10px; font-size: 12px; color: #475569;">{dist_str}</td>
            <td style="padding: 8px 10px; font-size: 12px; font-weight: 700; color: #2563eb;">{e['tss']}</td>
            <td style="padding: 8px 10px; font-size: 11.5px; text-align: center;">{feel_e} {rpe_short}</td>
        </tr>
        """

    if not completed_rows:
        completed_rows = "<tr><td colspan='7' style='padding: 14px; text-align: center; color: #94a3b8;'>No se registraron sesiones completadas en este periodo.</td></tr>"

    # 8. TABLA DE ENTRENAMIENTOS SALTADOS
    skipped_rows = ""
    for s in match_data['skipped']:
        _, icon, _ = get_sport_meta(s['sport'])
        skipped_rows += f"""
        <tr style="border-bottom: 1px solid #fee2e2; background-color: #fff5f5;">
            <td style="padding: 8px 10px; font-weight: 600; color: #dc2626; font-size: 12.5px;">{datetime.strptime(s['date'], '%Y-%m-%d').strftime('%d/%m')}</td>
            <td style="padding: 8px 10px; font-size: 12.5px;">{icon} {s['sport']}</td>
            <td style="padding: 8px 10px; font-size: 12.5px; color: #991b1b; font-weight: 500;">{s['planned_name']}</td>
            <td colspan="3" style="padding: 8px 10px; font-size: 11.5px; color: #b91c1c; font-style: italic;">No realizada</td>
            <td style="padding: 8px 10px; font-size: 12px; text-align: center;"><span style="color: #ef4444; font-weight: bold; background-color: #fef2f2; padding: 2px 8px; border-radius: 4px;">❌ Saltado</span></td>
        </tr>
        """

    # 9. RECOMENDACIONES DEL ENTRENADOR
    recs_html = ""
    for r in recommendations:
        recs_html += f"<li style='margin-bottom: 8px; font-size: 13px; line-height: 1.5; color: #1e293b;'>{r}</li>"

    # 10. PRÓXIMAS CARRERAS
    races_html = ""
    if upcoming_races:
        for rc in upcoming_races[:2]:
            races_html += f"""
            <div style="background-color: #fef2f2; border: 1px solid #fecaca; border-left: 4px solid #ef4444; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; font-size: 13px;">
                <strong>🏆 {rc['name']}</strong> — 📅 {rc['date_str']} (<strong>⏱️ ¡Faltan {rc['days_left']} días!</strong>)
            </div>
            """
    else:
        races_html = "<div style='font-size: 12.5px; color: #64748b; font-style: italic;'>No hay competiciones registradas en las próximas semanas.</div>"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title_label}</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 20px; color: #1e293b;">
        <table align="center" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 680px; background-color: #ffffff; border-radius: 14px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.06);">
            
            <!-- HEADER -->
            <tr>
                <td style="background: linear-gradient(135deg, #0f172a, #1e3a8a, #0284c7); padding: 32px 28px; text-align: left; color: #ffffff;">
                    <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 2px; font-weight: 800; color: #7dd3fc; margin-bottom: 6px;">COACHING SUITE PROFESIONAL</div>
                    <h1 style="margin: 0; font-size: 23px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px;">{title_label}</h1>
                    <div style="margin-top: 8px; font-size: 14px; color: #e0f2fe;">
                        Deportista: <strong style="color: #ffffff;">{athlete_name}</strong> &nbsp;|&nbsp; Periodo: <strong>{period_label}</strong>
                    </div>
                </td>
            </tr>

            <!-- BARRA DE CUMPLIMIENTO VISUAL -->
            <tr>
                <td style="padding: 20px 28px 10px 28px;">
                    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="font-size: 13px; font-weight: 700; color: #334155;">Cumplimiento del Plan:</span>
                            <span style="font-size: 12px; font-weight: 700; color: {comp_color}; background-color: #ffffff; border: 1px solid {comp_color}; border-radius: 12px; padding: 2px 10px;">
                                {comp_badge} ({comp}%)
                            </span>
                        </div>
                        <div style="background-color: #e2e8f0; border-radius: 8px; height: 12px; overflow: hidden;">
                            <div style="background: linear-gradient(90deg, {comp_color}, #0284c7); height: 100%; width: {min(100, max(5, comp))}%; border-radius: 8px;"></div>
                        </div>
                        <div style="font-size: 11.5px; color: #64748b; margin-top: 6px; text-align: right;">
                            {match_data['completed_count']} sesiones completadas de {match_data['total_planned']} planificadas
                        </div>
                        {rpe_summary_html}
                    </div>
                </td>
            </tr>

            <!-- TARJETAS DE MÉTRICAS CLAVE -->
            <tr>
                <td style="padding: 5px 28px 10px 28px;">
                    <table width="100%" border="0" cellpadding="0" cellspacing="0">
                        <tr>
                            <td width="23%" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 8px; text-align: center;">
                                <div style="font-size: 10.5px; text-transform: uppercase; color: #64748b; font-weight: 700;">Volumen Total</div>
                                <div style="font-size: 21px; font-weight: 800; color: #0f172a; margin-top: 3px;">{match_data['total_hours']}h</div>
                                <div style="font-size: 10.5px; color: #64748b; margin-top: 2px;">{match_data['completed_count'] + match_data['extra_count']} sesiones</div>
                            </td>
                            <td width="2%"></td>
                            <td width="23%" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 8px; text-align: center;">
                                <div style="font-size: 10.5px; text-transform: uppercase; color: #64748b; font-weight: 700;">Carga (TSS)</div>
                                <div style="font-size: 21px; font-weight: 800; color: #2563eb; margin-top: 3px;">{match_data['total_tss']}</div>
                                <div style="font-size: 10.5px; color: #64748b; margin-top: 2px;">Esfuerzo real</div>
                            </td>
                            <td width="2%"></td>
                            <td width="23%" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 8px; text-align: center;">
                                <div style="font-size: 10.5px; text-transform: uppercase; color: #64748b; font-weight: 700;">Forma (TSB)</div>
                                <div style="font-size: 21px; font-weight: 800; color: {tsb_color}; margin-top: 3px;">{wellness_data['current_tsb']}</div>
                                <div style="font-size: 10.5px; color: #64748b; margin-top: 2px;">{tsb_badge}</div>
                            </td>
                            <td width="2%"></td>
                            <td width="23%" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 8px; text-align: center;">
                                <div style="font-size: 10.5px; text-transform: uppercase; color: #64748b; font-weight: 700;">Fitness (CTL)</div>
                                <div style="font-size: 21px; font-weight: 800; color: #0284c7; margin-top: 3px;">{wellness_data['end_ctl']}</div>
                                <div style="font-size: 10.5px; color: #64748b; margin-top: 2px;">Δ {wellness_data['ctl_delta']:+.1f} pts</div>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>

            <!-- SECCIÓN ESTELAR: REVISIÓN EXHAUSTIVA DE SESIONES CLAVE Y SENSACIONES -->
            <tr>
                <td style="padding: 10px 28px;">
                    <div style="font-size: 14.5px; font-weight: 800; color: #0f172a; margin-bottom: 10px; border-bottom: 2px solid #0284c7; padding-bottom: 6px;">
                        🧠 Revisión Exhaustiva de Sesiones Clave y Sensaciones
                    </div>
                    {key_sessions_html}
                </td>
            </tr>

            <!-- SECCIÓN: PETICIÓN ACTIVA DE FEEDBACK (LLAMADA AL DEPORTISTA) -->
            <tr>
                <td style="padding: 10px 28px;">
                    <div style="background-color: #fefce8; border: 1.5px solid #fef08a; border-left: 5px solid #eab308; border-radius: 10px; padding: 16px 18px;">
                        <div style="font-size: 14px; font-weight: 800; color: #854d0e; margin-bottom: 8px;">
                            💬 Preguntas Clave del Entrenador (¡Dime cómo te has sentido!)
                        </div>
                        <ul style="margin: 0; padding-left: 18px;">
                            {questions_html}
                        </ul>
                        <div style="margin-top: 12px; text-align: center;">
                            <span style="font-size: 12px; color: #713f12; font-weight: 600;">
                                👉 Responde a este correo o escríbeme por WhatsApp para ajustar el plan al milímetro.
                            </span>
                        </div>
                    </div>
                </td>
            </tr>

            <!-- GRÁFICO VISUAL POR DISCIPLINAS Y ZONAS -->
            <tr>
                <td style="padding: 10px 28px;">
                    <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px;">
                        <div style="font-size: 13px; font-weight: 700; color: #0f172a; margin-bottom: 12px; text-transform: uppercase;">
                            📊 Distribución del Tiempo por Deporte:
                        </div>
                        {sports_bars_html}
                        {zones_visual_html}
                    </div>
                </td>
            </tr>

            <!-- QUÉ HAS TRABAJADO -->
            <tr>
                <td style="padding: 10px 28px;">
                    <div style="font-size: 14px; font-weight: 800; color: #0f172a; margin-bottom: 8px;">
                        🔬 Adaptaciones Fisiológicas Desarrolladas
                    </div>
                    {what_worked_html}
                </td>
            </tr>

            <!-- TABLA DE ENTRENAMIENTOS REALIZADOS -->
            <tr>
                <td style="padding: 15px 28px 5px 28px;">
                    <div style="font-size: 14px; font-weight: 800; color: #0f172a; margin-bottom: 8px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px;">
                        📋 Registro Completo de Actividades ({match_data['completed_count']})
                    </div>
                    <table width="100%" border="0" cellpadding="0" cellspacing="0" style="border-collapse: collapse;">
                        <thead>
                            <tr style="background-color: #f8fafc; text-align: left; font-size: 11px; text-transform: uppercase; color: #64748b; border-bottom: 1px solid #e2e8f0;">
                                <th style="padding: 8px 10px;">Día</th>
                                <th style="padding: 8px 10px;">Deporte</th>
                                <th style="padding: 8px 10px;">Sesión</th>
                                <th style="padding: 8px 10px;">Tiempo</th>
                                <th style="padding: 8px 10px;">Dist.</th>
                                <th style="padding: 8px 10px;">TSS</th>
                                <th style="padding: 8px 10px; text-align: center;">Feel / RPE</th>
                            </tr>
                        </thead>
                        <tbody>
                            {completed_rows}
                        </tbody>
                    </table>
                </td>
            </tr>

            <!-- TABLA DE ENTRENAMIENTOS SALTADOS -->
            {f'''
            <tr>
                <td style="padding: 15px 28px 5px 28px;">
                    <div style="font-size: 14px; font-weight: 800; color: #dc2626; margin-bottom: 8px; border-bottom: 2px solid #fee2e2; padding-bottom: 6px;">
                        ❌ Entrenamientos Saltados ({match_data['skipped_count']})
                    </div>
                    <table width="100%" border="0" cellpadding="0" cellspacing="0" style="border-collapse: collapse;">
                        <thead>
                            <tr style="background-color: #fef2f2; text-align: left; font-size: 11px; text-transform: uppercase; color: #991b1b; border-bottom: 1px solid #fecaca;">
                                <th style="padding: 8px 10px;">Día</th>
                                <th style="padding: 8px 10px;">Deporte</th>
                                <th style="padding: 8px 10px;">Sesión Planificada</th>
                                <th colspan="3" style="padding: 8px 10px;">Detalle</th>
                                <th style="padding: 8px 10px; text-align: center;">Estado</th>
                            </tr>
                        </thead>
                        <tbody>
                            {skipped_rows}
                        </tbody>
                    </table>
                </td>
            </tr>
            ''' if match_data['skipped_count'] > 0 else ''}

            <!-- RECOMENDACIONES DEL ENTRENADOR -->
            <tr>
                <td style="padding: 15px 28px;">
                    <div style="background-color: #eff6ff; border: 1px solid #bfdbfe; border-left: 4px solid #2563eb; border-radius: 10px; padding: 16px;">
                        <div style="font-size: 13.5px; font-weight: 800; color: #1e40af; margin-bottom: 8px; text-transform: uppercase;">
                            💡 Recomendaciones de tu Entrenador para el Próximo Microciclo:
                        </div>
                        <ul style="margin: 0; padding-left: 18px;">
                            {recs_html}
                        </ul>
                    </div>
                </td>
            </tr>

            <!-- PRÓXIMAS COMPETICIONES -->
            <tr>
                <td style="padding: 0 28px 20px 28px;">
                    <div style="font-size: 14px; font-weight: 800; color: #0f172a; margin-bottom: 8px;">
                        🎯 Próximos Retos y Competiciones:
                    </div>
                    {races_html}
                </td>
            </tr>

            <!-- FOOTER -->
            <tr>
                <td style="background-color: #0f172a; padding: 24px 28px; text-align: center; color: #94a3b8; font-size: 12px;">
                    <div style="font-weight: 700; color: #f8fafc; font-size: 14px; margin-bottom: 4px;">{coach_name}</div>
                    <div style="color: #cbd5e1;">Informe personalizado generado a través de la API oficial de Intervals.icu</div>
                    <div style="margin-top: 8px; font-size: 11px; color: #64748b;">Triathlon Coaching Suite • Rendimiento & Salud</div>
                </td>
            </tr>

        </table>
    </body>
    </html>
    """
    return html

def generate_report_recommendations(match_data, wellness_data, report_type="weekly", gemini_key=None, athlete_name="Deportista"):
    insights = analyze_training_insights(match_data, wellness_data, report_type, athlete_name)
    return insights['recommendations']
