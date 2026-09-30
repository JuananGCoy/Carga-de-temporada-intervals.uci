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
        # Prioridad 1: Frecuencia Cardíaca
        hz = act.get('icu_hr_zone_times')
        if hz and isinstance(hz, list):
            for i, s in enumerate(hz[:7]):
                val = float(s or 0)
                zone_secs[i] += val
                total_sec += val
                if val > 0:
                    has_zones = True
        else:
            # Prioridad 2: Potencia (ciclismo) si no hay FC
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
    Determina con exactitud qué se ha completado, qué se ha saltado y qué sesiones fueron adicionales.
    Calcula además la sesión estrella y la distribución de zonas.
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

    # Normalización de deportes para matching
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

        # Intento 1: Emparejamiento por paired_event_id
        match = None
        for a in act_list:
            if a.get('paired_event_id') == p_id:
                match = a
                break

        # Intento 2: Misma fecha y mismo deporte
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
                "avg_hr": int(match.get('average_heartrate', 0) or 0)
            })
        else:
            skipped.append({
                "date": p_date,
                "sport": p_type,
                "planned_name": p_name,
                "description": p.get('description', '')
            })

    # Actividades que no estaban planificadas (sesiones libres o extras)
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
                "avg_hr": int(a.get('average_heartrate', 0) or 0)
            })

    # Cálculos globales
    total_planned = len(planned_workouts)
    completed_count = len(completed)
    skipped_count = len(skipped)
    extra_count = len(extra)

    compliance_pct = round((completed_count / total_planned * 100.0), 1) if total_planned > 0 else 100.0
    total_duration_sec = sum(a.get('moving_time', 0) or 0 for a in act_list)
    total_tss = sum(int(a.get('icu_training_load', 0) or 0) for a in act_list)
    total_hours = round(total_duration_sec / 3600.0, 1)

    # Desglose por disciplina con cálculo de porcentaje
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

    # Detección de la Sesión Estrella (mayor TSS o más larga)
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
            "avg_hr": int(best_act.get('average_heartrate', 0) or 0)
        }

    # Distribución de zonas en el periodo
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

def analyze_training_insights(match_data, wellness_data, report_type="weekly", athlete_name="Deportista"):
    """
    Motor de análisis fisiológico y pedagógico de entrenamiento.
    Extrae con precisión:
    1. Qué adaptaciones fisiológicas ha trabajado el deportista en este ciclo.
    2. Puntos fuertes consolidados y progresos tangibles.
    3. Análisis de la sesión estrella.
    4. Recomendaciones accionables para el próximo periodo.
    """
    comp = match_data['compliance_pct']
    total_hours = match_data['total_hours']
    total_tss = match_data['total_tss']
    sports = match_data['sports_breakdown']
    zones = match_data['zones_data']
    tsb = wellness_data['current_tsb']
    ctl = wellness_data['end_ctl']
    delta_ctl = wellness_data['ctl_delta']
    star = match_data.get('star_session')

    period_word = "esta semana" if report_type == "weekly" else "este mes"

    # --- 1. ¿Qué has trabajado? (Sistemas fisiológicos estimulados) ---
    what_worked = []

    # A) Base Aeróbica
    if zones['has_zones'] and zones['low_pct'] >= 65:
        what_worked.append({
            "icon": "🫀",
            "title": "Motor Aeróbico y Eficiencia Metabólica (Zona 1 - 2)",
            "desc": f"Has invertido {zones['low_hours']}h ({zones['low_pct']}% de tu tiempo) en intensidades controladas. "
                    "Esto estimula la multiplicación de mitocondrias y capilares en tus fibras musculares, enseñando a tu organismo a usar las grasas como combustible principal y preservando glucógeno."
        })
    elif total_hours > 0:
        what_worked.append({
            "icon": "🫀",
            "title": "Fondo y Capacidad Cardiovascular General",
            "desc": f"Has sumado {total_hours} horas de movimiento activo en el periodo, construyendo la base de resistencia que te permitirá tolerar mayores intensidades más adelante."
        })

    # B) Fuerza y Estabilidad Muscular
    gym_info = sports.get('Fuerza / Gimnasio')
    if gym_info and gym_info['hours'] > 0:
        what_worked.append({
            "icon": "🏋️‍♂️",
            "title": "Fuerza Estructural y Prevención de Lesiones",
            "desc": f"Completaste {gym_info['hours']}h de trabajo de fuerza. Fortalecer tendones, glúteos y core no solo te hace más potente en cada brazada o zancada, sino que reduce drásticamente el riesgo de sobrecargas articulares."
        })
    elif 'Fuerza / Gimnasio' in [s['sport'] for s in match_data['skipped']]:
        what_worked.append({
            "icon": "⚠️",
            "title": "Fuerza Pendiente de Reforzar",
            "desc": "Se han quedado sesiones de gimnasio sin realizar. Recuerda que la fuerza es el pilar que sostiene todo el volumen de nado, bici y carrera."
        })

    # C) Ritmo y Umbral / Calidad
    if zones['has_zones'] and zones['high_pct'] >= 10:
        what_worked.append({
            "icon": "⚡",
            "title": "Ritmo Específico y Tolerancia al Lactato (Zonas 4 y 5)",
            "desc": f"Dedicaste {zones['high_hours']}h ({zones['high_pct']}%) a intensidades altas. Este trabajo desplaza tu umbral de lactato hacia la derecha, permitiéndote rodar y correr más rápido con menor sensación de agonía."
        })
    elif zones['has_zones'] and zones['mid_pct'] >= 25:
        what_worked.append({
            "icon": "🎯",
            "title": "Ritmo de Crucero / Tempo (Zona 3)",
            "desc": f"Registraste {zones['mid_hours']}h ({zones['mid_pct']}%) en zona media. Buen trabajo de ritmo de crucero, aunque en las próximas semanas conviene polarizar más: rodar más suave en días fáciles para tener chispa en las series duras."
        })

    # D) Disciplina líder
    if sports:
        top_sport = max(sports.items(), key=lambda x: x[1]['hours'])
        if top_sport[0] in ['Ciclismo', 'Carrera', 'Natación']:
            km_txt = f" ({top_sport[1]['km']} km)" if top_sport[1]['km'] > 0 else ""
            what_worked.append({
                "icon": top_sport[1]['icon'],
                "title": f"Foco Principal: {top_sport[0]}",
                "desc": f"Ha sido la disciplina con mayor volumen ({top_sport[1]['hours']}h{km_txt}), consolidando sensaciones técnicas y resistencia específica sobre este deporte."
            })

    # --- 2. Puntos Fuertes Mejorados ---
    strengths = []

    if comp >= 85:
        strengths.append(f"🎯 **Constancia sobresaliente ({comp}% completado):** La regularidad es la variable #1 que predice el éxito deportivo. Has cumplido con gran disciplina el plan marcado.")
    elif comp >= 70:
        strengths.append(f"👍 **Buena capacidad de cumplimiento ({comp}%):** A pesar de los imprevistos de la rutina diaria, has salvado el núcleo duro de los entrenamientos.")

    if zones['has_zones'] and zones['low_pct'] >= 70:
        strengths.append(f"🟢 **Excelente control de intensidad:** Has respetado las zonas suaves ({zones['low_pct']}% en Z1-Z2), evitando la trampa de 'rodar siempre en fatiga media'.")

    if total_tss >= 400:
        strengths.append(f"🔥 **Capacidad de carga sólida:** Has digerido {total_tss} puntos TSS en el periodo sin saturar en exceso el organismo, lo que demuestra que tu motor está creciendo.")

    if gym_info and gym_info['hours'] > 0:
        strengths.append("💪 **Compromiso con el trabajo muscular:** Gran disciplina al no saltarte las sesiones de fuerza, un factor diferencial frente a la mayoría de populares.")

    if report_type == "monthly" and delta_ctl > 0:
        strengths.append(f"📈 **Fitness al alza (+{delta_ctl} puntos CTL):** Tu condición física de base se ha incrementado notablemente a lo largo del mes, situándote en {ctl} CTL.")

    if not strengths:
        strengths.append("✅ **Actividad constante:** Mantienes activo el hábito deportivo y la base física general.")

    # --- 3. Comentario de la Sesión Estrella ---
    star_comment = ""
    if star:
        star_comment = (
            f"Tu sesión de mayor impacto fue el **{datetime.strptime(star['date'], '%Y-%m-%d').strftime('%d/%m')}**: "
            f"**{star['name']}** ({star['sport']} - {star['duration_str']}"
            + (f", {star['distance_km']} km" if star['distance_km'] > 0 else "")
            + f", {star['tss']} TSS). Este entrenamiento supuso el estímulo clave del periodo para desafiar tu resistencia."
        )

    # --- 4. Recomendaciones del Entrenador ---
    recommendations = []

    # Estado de fatiga (TSB)
    if tsb < -25:
        recommendations.append(
            f"🛑 **Priorizar descanso activo (TSB: {tsb}):** Tu cuerpo acumula fatiga aguda. "
            "Es normal tras días duros, pero para asimilar este trabajo necesitas dormir 7-8 horas, hidratarte bien y no forzar en los días fáciles."
        )
    elif -25 <= tsb <= -5:
        recommendations.append(
            f"🚀 **Punto dulce de adaptación (TSB: {tsb}):** Tu fatiga y tu forma están perfectamente equilibradas. "
            "Estás en la ventana ideal donde el entrenamiento produce mejoras directas sin riesgo de sobrecarga."
        )
    elif 5 <= tsb <= 25:
        recommendations.append(
            f"🏆 **Frescura competitiva alta (TSB: +{tsb}):** Tu cuerpo ha disipado la fatiga. "
            "Estás en condiciones óptimas para rendir al 100% en competiciones o tests de ritmo."
        )
    else:
        recommendations.append(
            f"⚖️ **Periodo de descanso / transición (TSB: +{tsb}):** La fatiga ha caído bastante. "
            "Es momento de volver a introducir estímulos progresivos de volumen para seguir construyendo."
        )

    # Alerta de sesiones saltadas
    if match_data['skipped_count'] > 0:
        recommendations.append(
            f"📋 **Gestión de sesiones no realizadas ({match_data['skipped_count']} saltadas):** "
            "No te preocupes por recuperarlas de golpe metiendo sesiones dobles. Lo ideal es hablar conmigo para reajustar los próximos días sin acumular fatiga innecesaria."
        )

    recommendations.append(
        "📝 **Feedback en Intervals:** No olvides registrar tus sensaciones (RPE del 1 al 10) tras cada entrenamiento. Me ayuda enormemente a calibrar tus cargas."
    )

    return {
        "what_worked": what_worked,
        "strengths": strengths,
        "star_comment": star_comment,
        "recommendations": recommendations
    }

def build_report_html(athlete_name, report_type, start_date, end_date, match_data, wellness_data, upcoming_races, recommendations=None, coach_name="Juanan Coy - Entrenador"):
    """
    Construye el documento HTML del correo electrónico con diseño limpio, responsivo y profesional.
    Incorpora gráficos visuales en puro HTML/CSS (barras de distribución, zonas de intensidad y progreso).
    """
    title_label = "INFORME SEMANAL DE RENDIMIENTO" if report_type == "weekly" else "BALANCE MENSUAL DE ENTRENAMIENTO"
    period_label = f"{datetime.strptime(start_date, '%Y-%m-%d').strftime('%d %b')} al {datetime.strptime(end_date, '%Y-%m-%d').strftime('%d %b %Y')}"

    # Análisis avanzado
    insights = analyze_training_insights(match_data, wellness_data, report_type, athlete_name)
    if not recommendations:
        recommendations = insights['recommendations']

    # Métricas clave
    comp = match_data['compliance_pct']
    comp_color = "#10b981" if comp >= 80 else ("#f59e0b" if comp >= 65 else "#ef4444")
    comp_badge = "¡Excelente disciplina!" if comp >= 85 else ("Buen cumplimiento" if comp >= 70 else "Atención al plan")

    tsb = wellness_data['current_tsb']
    tsb_color = "#10b981" if -25 <= tsb <= 10 else ("#ef4444" if tsb < -25 else "#3b82f6")
    tsb_badge = "Asimilando óptimo" if -25 <= tsb <= -5 else ("Fresco / Competitivo" if tsb > 0 else "Fatiga acumulada")

    # 1. BARRA VISUAL DE DISTRIBUCIÓN POR DEPORTE
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

    # 2. BARRA VISUAL DE ZONAS DE INTENSIDAD (POLARIZADA)
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
            <div style="font-size: 11px; color: #64748b; margin-top: 6px; font-style: italic;">
                💡 <strong>Objetivo salud y fondo:</strong> ~80% en Zona Verde (Base) y ~20% en Tempo y Calidad.
            </div>
        </div>
        """

    # 3. SESIÓN ESTRELLA HIGHLIGHT CARD
    star = match_data.get('star_session')
    star_html = ""
    if star and (star['tss'] > 0 or star['duration_str'] != "0m"):
        dist_part = f" • 📏 <strong>{star['distance_km']} km</strong>" if star['distance_km'] > 0 else ""
        hr_part = f" • ❤️ <strong>{star['avg_hr']} ppm</strong>" if star['avg_hr'] > 0 else ""
        star_html = f"""
        <div style="background: linear-gradient(135deg, #eff6ff, #f8fafc); border: 1.5px solid #bfdbfe; border-left: 5px solid #2563eb; border-radius: 10px; padding: 14px 16px; margin-bottom: 20px;">
            <div style="font-size: 11.5px; text-transform: uppercase; letter-spacing: 1px; color: #2563eb; font-weight: 800; margin-bottom: 4px;">
                🌟 Sesión Estrella del Periodo
            </div>
            <div style="font-size: 16px; font-weight: 800; color: #0f172a; margin-bottom: 4px;">
                {star['icon']} {star['name']}
            </div>
            <div style="font-size: 13px; color: #334155; margin-bottom: 6px;">
                📅 <strong>{datetime.strptime(star['date'], '%Y-%m-%d').strftime('%d/%m/%Y')}</strong> • ⏱️ <strong>{star['duration_str']}</strong>{dist_part} • ⚡ <strong>{star['tss']} TSS</strong>{hr_part}
            </div>
            <div style="font-size: 12px; color: #475569; line-height: 1.4;">
                {insights['star_comment']}
            </div>
        </div>
        """

    # 4. QUÉ HAS TRABAJADO (BLOQUES FISIOLÓGICOS)
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

    # 5. PUNTOS FUERTES MEJORADOS
    strengths_html = ""
    for s in insights['strengths']:
        strengths_html += f"""
        <li style="margin-bottom: 6px; font-size: 13px; line-height: 1.45; color: #166534;">{s}</li>
        """

    # 6. TABLA DE ENTRENAMIENTOS REALIZADOS
    completed_rows = ""
    for c in match_data['completed']:
        _, icon, _ = get_sport_meta(c['sport'])
        dist_str = f"{c['distance_km']} km" if c['distance_km'] > 0 else "-"
        hr_str = f"{c['avg_hr']} ppm" if c['avg_hr'] > 0 else "-"
        completed_rows += f"""
        <tr style="border-bottom: 1px solid #f1f5f9;">
            <td style="padding: 8px 10px; font-weight: 600; color: #334155; font-size: 12.5px;">{datetime.strptime(c['date'], '%Y-%m-%d').strftime('%d/%m')}</td>
            <td style="padding: 8px 10px; font-size: 12.5px;">{icon} {c['sport']}</td>
            <td style="padding: 8px 10px; font-size: 12.5px; color: #0f172a; font-weight: 500;">{c['actual_name']}</td>
            <td style="padding: 8px 10px; font-size: 12.5px; color: #475569;">{c['duration_str']}</td>
            <td style="padding: 8px 10px; font-size: 12.5px; color: #475569;">{dist_str}</td>
            <td style="padding: 8px 10px; font-size: 12.5px; font-weight: 700; color: #2563eb;">{c['tss']}</td>
            <td style="padding: 8px 10px; font-size: 12px; text-align: center;"><span style="color: #10b981; font-weight: bold; background-color: #ecfdf5; padding: 2px 8px; border-radius: 4px;">✅ Hecho</span></td>
        </tr>
        """

    for e in match_data['extra']:
        _, icon, _ = get_sport_meta(e['sport'])
        dist_str = f"{e['distance_km']} km" if e['distance_km'] > 0 else "-"
        completed_rows += f"""
        <tr style="border-bottom: 1px solid #f1f5f9; background-color: #fafafa;">
            <td style="padding: 8px 10px; font-weight: 600; color: #64748b; font-size: 12.5px;">{datetime.strptime(e['date'], '%Y-%m-%d').strftime('%d/%m')}</td>
            <td style="padding: 8px 10px; font-size: 12.5px;">{icon} {e['sport']}</td>
            <td style="padding: 8px 10px; font-size: 12.5px; color: #334155;">{e['actual_name']}</td>
            <td style="padding: 8px 10px; font-size: 12.5px; color: #475569;">{e['duration_str']}</td>
            <td style="padding: 8px 10px; font-size: 12.5px; color: #475569;">{dist_str}</td>
            <td style="padding: 8px 10px; font-size: 12.5px; font-weight: 700; color: #2563eb;">{e['tss']}</td>
            <td style="padding: 8px 10px; font-size: 12px; text-align: center;"><span style="color: #6366f1; font-weight: bold; background-color: #eef2ff; padding: 2px 8px; border-radius: 4px;">➕ Extra</span></td>
        </tr>
        """

    if not completed_rows:
        completed_rows = "<tr><td colspan='7' style='padding: 14px; text-align: center; color: #94a3b8;'>No se registraron sesiones completadas en este periodo.</td></tr>"

    # 7. TABLA DE ENTRENAMIENTOS SALTADOS
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

    # 8. RECOMENDACIONES DEL ENTRENADOR
    recs_html = ""
    for r in recommendations:
        recs_html += f"<li style='margin-bottom: 8px; font-size: 13px; line-height: 1.5; color: #1e293b;'>{r}</li>"

    # 9. PRÓXIMAS CARRERAS
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
                            <span style="font-size: 13px; font-weight: 700; color: #334155;">Nivel de Cumplimiento del Plan:</span>
                            <span style="font-size: 12px; font-weight: 700; color: {comp_color}; background-color: #ffffff; border: 1px solid {comp_color}; border-radius: 12px; padding: 2px 10px;">
                                {comp_badge} ({comp}%)
                            </span>
                        </div>
                        <div style="background-color: #e2e8f0; border-radius: 8px; height: 12px; overflow: hidden;">
                            <div style="background: linear-gradient(90deg, {comp_color}, #0284c7); height: 100%; width: {min(100, max(5, comp))}%; border-radius: 8px;"></div>
                        </div>
                        <div style="font-size: 11.5px; color: #64748b; margin-top: 6px; text-align: right;">
                            {match_data['completed_count']} sesiones completadas de {match_data['total_planned']} programadas
                        </div>
                    </div>
                </td>
            </tr>

            <!-- TARJETAS DE MÉTRICAS CLAVE -->
            <tr>
                <td style="padding: 10px 28px;">
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
                                <div style="font-size: 10.5px; color: #64748b; margin-top: 2px;">Δ {wellness_data['ctl_delta']:+.1f} puntos</div>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>

            <!-- SESIÓN ESTRELLA -->
            <tr>
                <td style="padding: 10px 28px 0 28px;">
                    {star_html}
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

            <!-- QUÉ HAS TRABAJADO (ANÁLISIS FISIOLÓGICO CLARO) -->
            <tr>
                <td style="padding: 10px 28px;">
                    <div style="font-size: 14px; font-weight: 800; color: #0f172a; margin-bottom: 8px;">
                        🔬 ¿Qué has trabajado en este periodo? (Adaptaciones Conseguidas)
                    </div>
                    {what_worked_html}
                </td>
            </tr>

            <!-- PUNTOS FUERTES MEJORADOS -->
            <tr>
                <td style="padding: 10px 28px;">
                    <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-left: 4px solid #16a34a; border-radius: 10px; padding: 14px 16px;">
                        <div style="font-size: 13.5px; font-weight: 800; color: #15803d; margin-bottom: 8px; text-transform: uppercase;">
                            🏆 Tus Puntos Fuertes Mejorados:
                        </div>
                        <ul style="margin: 0; padding-left: 18px;">
                            {strengths_html}
                        </ul>
                    </div>
                </td>
            </tr>

            <!-- TABLA DE ENTRENAMIENTOS REALIZADOS -->
            <tr>
                <td style="padding: 15px 28px 5px 28px;">
                    <div style="font-size: 14px; font-weight: 800; color: #0f172a; margin-bottom: 8px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px;">
                        ✅ Entrenamientos Completados ({match_data['completed_count']})
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
                                <th style="padding: 8px 10px; text-align: center;">Estado</th>
                            </tr>
                        </thead>
                        <tbody>
                            {completed_rows}
                        </tbody>
                    </table>
                </td>
            </tr>

            <!-- TABLA DE ENTRENAMIENTOS SALTADOS SI LOS HAY -->
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
                            💡 Recomendaciones de tu Entrenador para el Próximo Ciclo:
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

            <!-- MINI GLOSARIO PEDAGÓGICO -->
            <tr>
                <td style="padding: 0 28px 20px 28px;">
                    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; font-size: 11px; color: #64748b; line-height: 1.4;">
                        📖 <strong>¿Qué significan mis métricas?</strong> 
                        <strong>TSS:</strong> Carga de entrenamiento que combina volumen e intensidad. 
                        <strong>CTL (Fitness):</strong> Tu condición física construida en los últimos 42 días. 
                        <strong>TSB (Forma):</strong> El balance entre fatiga y frescura (entre -25 y -10 construyes; positivo estás descansado).
                    </div>
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
    """
    Función de compatibilidad: redirige al nuevo motor analyze_training_insights.
    """
    insights = analyze_training_insights(match_data, wellness_data, report_type, athlete_name)
    return insights['recommendations']
