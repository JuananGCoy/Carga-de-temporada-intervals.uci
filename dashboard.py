import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import calendar
import intervals_api
import report_generator
import requests
import json
import os

# Mapeo de nombres e iconos de deportes
SPORT_MAP = {
    'Swim': ('Natación', '🏊‍♂️', '#06b6d4'),
    'Ride': ('Ciclismo', '🚴‍♂️', '#f97316'),
    'VirtualRide': ('Ciclismo Virtual', '🚴‍♂️', '#ea580c'),
    'Run': ('Carrera', '🏃‍♂️', '#10b981'),
    'TrailRun': ('Trail Running', '⛰️', '#059669'),
    'WeightTraining': ('Gimnasio/Fuerza', '🏋️‍♂️', '#8b5cf6'),
    'Walk': ('Caminata', '🚶‍♂️', '#64748b'),
    'Hike': ('Senderismo', '🥾', '#475569'),
    'Workout': ('Entrenamiento', '⚡', '#3b82f6'),
    'Other': ('Otros', '🎯', '#94a3b8')
}

def get_sport_info(sport_type):
    return SPORT_MAP.get(sport_type, (sport_type, '🏅', '#64748b'))

@st.cache_data(ttl=300, show_spinner=False)
def fetch_athlete_data(athlete_id, api_key, oldest, newest, is_coach=False):
    """
    Descarga y cachea las actividades, wellness y eventos de Intervals.icu.
    """
    success_act, activities = intervals_api.get_athlete_activities(athlete_id, api_key, oldest, newest, is_coach=is_coach)
    success_well, wellness = intervals_api.get_athlete_wellness(athlete_id, api_key, oldest, newest, is_coach=is_coach)
    success_prof, profile = intervals_api.get_athlete_profile(athlete_id, api_key, is_coach=is_coach)
    
    # Obtener eventos desde el inicio del mes en curso hasta 120 días en el futuro
    today = datetime.now()
    first_of_month = today.replace(day=1).strftime("%Y-%m-%d")
    future_date = (today + timedelta(days=120)).strftime("%Y-%m-%d")
    success_events, events = intervals_api.get_athlete_events(athlete_id, api_key, first_of_month, future_date, is_coach=is_coach)
    
    return {
        "activities": activities if success_act and isinstance(activities, list) else [],
        "wellness": wellness if success_well and isinstance(wellness, list) else [],
        "profile": profile if success_prof and isinstance(profile, dict) else {},
        "events": events if success_events and isinstance(events, list) else [],
        "fetched_at": datetime.now().strftime("%H:%M:%S"),
        "error_act": activities if not success_act else None,
        "error_well": wellness if not success_well else None
    }

def format_duration(seconds):
    if not seconds or pd.isna(seconds):
        return "0h 0m"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes:02d}m"

def extract_zones_data(activities):
    """
    Agrega el tiempo en zonas de frecuencia cardíaca y potencia de las actividades del periodo.
    Consolida las métricas según el modelo de polarización deportiva (Seiler 80/20).
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
            # Prioridad 2: Zonas de potencia (ciclismo) si no hay FC
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

    # 5 Zonas consolidadas:
    # Z1: Recuperación
    # Z2: Base Aeróbica
    # Z3: Tempo
    # Z4: Umbral Lactato
    # Z5+: VO2max y Anaeróbico (Z5 + Z6 + Z7)
    z1 = zone_secs[0]
    z2 = zone_secs[1]
    z3 = zone_secs[2]
    z4 = zone_secs[3]
    z5_plus = zone_secs[4] + zone_secs[5] + zone_secs[6]

    zones_5 = [z1, z2, z3, z4, z5_plus]
    total_5 = sum(zones_5)

    pcts = [(z / total_5 * 100.0) if total_5 > 0 else 0.0 for z in zones_5]
    hours = [z / 3600.0 for z in zones_5]

    low_pct = pcts[0] + pcts[1]
    mid_pct = pcts[2]
    high_pct = pcts[3] + pcts[4]

    return {
        "has_zones": has_zones,
        "hours": hours,
        "pcts": pcts,
        "total_hours": total_5 / 3600.0,
        "low_pct": low_pct,
        "mid_pct": mid_pct,
        "high_pct": high_pct
    }

def render_zone_distribution_chart(zone_data):
    """
    Gráfico de barras apiladas horizontal que muestra la distribución de tiempo en zonas de intensidad.
    """
    fig = go.Figure()
    
    if not zone_data["has_zones"] or zone_data["total_hours"] == 0:
        fig.add_annotation(
            text="💡 No se registraron datos de zonas de pulso o potencia en las actividades del periodo.<br>Asegúrate de que tus deportistas lleven pulsómetro o potenciómetro.",
            showarrow=False,
            font=dict(size=13, color="#64748b")
        )
        fig.update_layout(height=180, plot_bgcolor="white", paper_bgcolor="white")
        return fig

    zone_labels = [
        "Z1: Recuperación",
        "Z2: Base Aeróbica",
        "Z3: Tempo (Zona Gris)",
        "Z4: Umbral",
        "Z5+: VO2max / Anaeróbico"
    ]
    colors = ["#94a3b8", "#0284c7", "#f59e0b", "#ea580c", "#dc2626"]
    pcts = zone_data["pcts"]
    hours = zone_data["hours"]

    for i in range(len(zone_labels)):
        fig.add_trace(go.Bar(
            y=["Intensidad"],
            x=[pcts[i]],
            name=zone_labels[i],
            orientation='h',
            marker=dict(color=colors[i]),
            hovertemplate=f"<b>{zone_labels[i]}</b><br>{pcts[i]:.1f}% ({hours[i]:.1f} horas)<extra></extra>"
        ))

    fig.update_layout(
        barmode='stack',
        title=dict(
            text="<b>Distribución por Zonas de Intensidad (%)</b><br><span style='font-size:12px; font-weight:normal; color:#64748b;'>🟢 Base Z1-Z2 (~80% objetivo) | 🟡 Tempo Z3 (ritmo medio) | 🔴 Alta Z4-Z5+ (umbral y series)</span>",
            y=0.97, x=0.01, xanchor='left', yanchor='top', font=dict(size=14)
        ),
        xaxis=dict(title="Porcentaje del Tiempo Total (%)", range=[0, 100], showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(showticklabels=False),
        legend=dict(orientation="h", yanchor="top", y=-0.28, xanchor="center", x=0.5),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=190,
        margin=dict(l=20, r=20, t=55, b=65)
    )
    return fig

def generate_zone_recommendations(zone_data):
    """
    Genera recomendaciones fisiológicas basadas en la distribución de zonas y polarización 80/20.
    """
    recs = []
    if not zone_data["has_zones"] or zone_data["total_hours"] == 0:
        return recs

    low = zone_data["low_pct"]
    mid = zone_data["mid_pct"]
    high = zone_data["high_pct"]

    # 1. Base aeróbica Z1-Z2
    if low >= 75:
        recs.append((
            "success",
            "✅ Base Aeróbica Excelente (Z1 - Z2)",
            f"El deportista acumula un **{low:.1f}%** de su tiempo en Z1-Z2 (objetivo recomendado: 75% - 85%). "
            "Esto asegura una óptima adaptación mitocondrial, capilarización y uso eficiente de grasas como combustible sin acumular fatiga innecesaria."
        ))
    elif low < 65:
        recs.append((
            "warning",
            "⚠️ Déficit de Rodajes en Base Aeróbica (Z1 - Z2 bajo)",
            f"Solo el **{low:.1f}%** del tiempo está en Z1-Z2 (se recomienda al menos un 70-80%). "
            "El deportista tiende a rodar demasiado rápido en las sesiones supuestamente suaves. "
            "**Recomendación:** Forzar rodajes más cómodos en Z2 baja para permitir una recuperación adecuada y construir base aeróbica real."
        ))

    # 2. Zona Gris (Z3 - Tempo)
    if mid > 25:
        recs.append((
            "error" if mid > 35 else "warning",
            "⚠️ Exceso de Tiempo en 'Zona Gris' (Z3 / Tempo)",
            f"El **{mid:.1f}%** del tiempo de entrenamiento se realiza en Z3 (lo recomendado es < 15%). "
            "La Z3 es la llamada 'tierra de nadie': es un ritmo demasiado exigente para recuperar bien y demasiado suave para generar adaptaciones máximas de umbral o VO2max. "
            "**Recomendación:** Polarizar el entrenamiento: haz que los días fáciles sean verdaderamente fáciles (Z1/Z2) para llegar frescos y rendir al máximo en las series intensas (Z4/Z5)."
        ))
    elif mid <= 15 and low >= 70:
        recs.append((
            "success",
            "🎯 Control Óptimo de la Zona Media (Z3)",
            f"El tiempo en Z3 está controlado en un **{mid:.1f}%**, lo que demuestra una excelente disciplina en intensidades y un entrenamiento bien polarizado."
        ))

    # 3. Alta Intensidad (Z4 - Z5+)
    if high < 5 and zone_data["total_hours"] > 8:
        recs.append((
            "info",
            "⚡ Falta de Estímulo de Calidad / Umbral (Z4 - Z5+)",
            f"Solo se ha dedicado un **{high:.1f}%** del tiempo a intensidades superiores (Z4/Z5+). "
            "Si no se está en periodo exclusivo de volumen de pretemporada, conviene introducir bloques de series fraccionadas a ritmo umbral o VO2max para elevar la velocidad y potencia sostenible."
        ))
    elif high > 22:
        recs.append((
            "warning",
            "🔥 Alta Concentración de Intensidad Máxima",
            f"El **{high:.1f}%** del tiempo transcurre en Z4 o superior. Supervisa de cerca la fatiga del sistema nervioso y la calidad del sueño para evitar sobrecargas."
        ))

    return recs

def generate_month_calendar_html(year, month, events_by_date):
    """
    Genera el HTML de una cuadrícula de calendario mensual limpio con eventos y carreras.
    """
    cal = calendar.monthcalendar(year, month)
    month_names = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    month_name = month_names[month - 1]
    
    html = f"""
    <div style="background-color: #ffffff; border-radius: 10px; border: 1px solid #e2e8f0; padding: 12px; margin-top: 10px;">
        <div style="font-size: 1.1rem; font-weight: 700; margin-bottom: 10px; color: #1e293b;">📅 {month_name} {year}</div>
        <table style="width: 100%; border-collapse: separate; border-spacing: 5px; table-layout: fixed;">
            <thead>
                <tr style="text-align: center; font-size: 0.8rem; color: #64748b; font-weight: 600;">
                    <th style="padding: 2px;">Lun</th>
                    <th style="padding: 2px;">Mar</th>
                    <th style="padding: 2px;">Mié</th>
                    <th style="padding: 2px;">Jue</th>
                    <th style="padding: 2px;">Vie</th>
                    <th style="padding: 2px; color: #2563eb;">Sáb</th>
                    <th style="padding: 2px; color: #ef4444;">Dom</th>
                </tr>
            </thead>
            <tbody>
    """
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    for week in cal:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += '<td style="background-color: #f8fafc; border-radius: 6px; height: 65px; vertical-align: top; opacity: 0.25;"></td>'
            else:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                day_events = events_by_date.get(date_str, [])
                is_today = (date_str == today_str)
                
                border_style = "2px solid #2563eb" if is_today else "1px solid #e2e8f0"
                bg_style = "#eff6ff" if is_today else "#ffffff"
                
                content = f'<div style="font-size: 0.75rem; font-weight: 700; margin-bottom: 2px; color: {"#2563eb" if is_today else "#334155"};">{day}</div>'
                
                # Competiciones
                races = [e for e in day_events if 'race' in str(e.get('category', '')).lower()]
                workouts = [e for e in day_events if e.get('category') == 'WORKOUT']
                
                if races:
                    for r in races:
                        cat = str(r.get('category', '')).upper()
                        badge_color = "#dc2626" if 'A' in cat else ("#f59e0b" if 'B' in cat else "#2563eb")
                        r_name = str(r.get('name', 'Competición'))[:18]
                        content += f'<div style="background-color: {badge_color}; color: white; border-radius: 4px; font-size: 0.68rem; font-weight: bold; padding: 2px 4px; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{r.get("name")}">🏆 {r_name}</div>'
                
                if workouts:
                    for w in workouts[:2]:
                        w_type = w.get('type', 'Workout')
                        icon = '🏊' if w_type == 'Swim' else ('🚴' if w_type in ['Ride', 'VirtualRide'] else ('🏃' if w_type in ['Run', 'TrailRun'] else ('🏋️' if w_type == 'WeightTraining' else '⚡')))
                        w_name = str(w.get('name', ''))[:14]
                        content += f'<div style="background-color: #f1f5f9; color: #1e293b; border-left: 3px solid #3b82f6; border-radius: 2px; font-size: 0.65rem; padding: 1px 3px; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{w.get("name")}">{icon} {w_name}</div>'
                    if len(workouts) > 2:
                        content += f'<div style="font-size: 0.62rem; color: #64748b;">+{len(workouts)-2} más</div>'
                elif not races:
                    content += '<div style="font-size: 0.62rem; color: #cbd5e1; font-style: italic;">Descanso</div>'
                
                html += f'<td style="background-color: {bg_style}; border: {border_style}; border-radius: 6px; height: 65px; vertical-align: top; padding: 3px; max-width: 14%;">{content}</td>'
        html += "</tr>"
        
    html += """
            </tbody>
        </table>
    </div>
    """
    return html

def render_upcoming_objectives(events):
    """
    Renderiza las tarjetas de cuenta atrás para las carreras clave y el calendario mensual.
    """
    st.markdown("### 🎯 Próximos Objetivos y Calendario Competitivo")

    today = datetime.now()
    races = []
    
    for e in events:
        cat = str(e.get('category', '')).upper()
        if 'RACE' in cat or 'TARGET' in cat or 'competi' in str(e.get('name', '')).lower():
            d_str = str(e.get('start_date_local', ''))[:10]
            try:
                d_date = datetime.strptime(d_str, "%Y-%m-%d")
                days_left = (d_date.date() - today.date()).days
                if days_left >= 0:
                    races.append({
                        "name": e.get('name', 'Competición'),
                        "date": d_date,
                        "date_str": d_str,
                        "category": cat,
                        "type": e.get('type', 'Race'),
                        "days_left": days_left
                    })
            except Exception:
                pass

    races = sorted(races, key=lambda x: x['days_left'])

    if races:
        cols = st.columns(min(len(races), 3))
        for idx, race in enumerate(races[:3]):
            with cols[idx]:
                cat = race['category']
                is_race_a = 'A' in cat
                is_race_b = 'B' in cat
                badge = "🏆 OBJETIVO PRINCIPAL (RACE A)" if is_race_a else ("🥈 OBJETIVO SECUNDARIO (RACE B)" if is_race_b else "🥉 TEST (RACE C)")
                badge_bg = "#dc2626" if is_race_a else ("#f59e0b" if is_race_b else "#2563eb")
                
                days = race['days_left']
                days_label = "¡HOY!" if days == 0 else (f"Falta 1 día" if days == 1 else f"Faltan {days} días")
                
                # Contexto de fase
                if days <= 7:
                    phase = "⚡ Semana de carrera: Activación y descanso máximo"
                elif days <= 21 and is_race_a:
                    phase = "📉 Fase de Tapering: Reducir volumen 25-35%, mantener ritmo"
                elif days <= 45:
                    phase = "🚀 Bloque Específico: Ritmos de competición y tiradas clave"
                else:
                    phase = "🏗️ Fase de Carga General / Base"

                st.markdown(f"""
                <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-top: 4px solid {badge_bg}; border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                    <div style="font-size: 0.72rem; font-weight: 700; color: {badge_bg}; text-transform: uppercase;">{badge}</div>
                    <div style="font-size: 1.05rem; font-weight: 700; color: #0f172a; margin: 4px 0;">{race['name']}</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 0.85rem; color: #64748b;">📅 {race['date'].strftime('%d/%m/%Y')}</span>
                        <span style="background-color: #e2e8f0; color: #1e293b; padding: 2px 8px; border-radius: 12px; font-weight: 700; font-size: 0.8rem;">⏱️ {days_label}</span>
                    </div>
                    <div style="font-size: 0.78rem; color: #334155; border-top: 1px dashed #cbd5e1; padding-top: 6px;">{phase}</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("ℹ️ No hay competiciones marcadas como RACE A/B/C en Intervals.icu en los próximos meses. Puedes asignarlas en el calendario de Intervals.icu para ver la cuenta atrás automática.")

    # Calendario Mensual Interactivo
    with st.expander("📅 Ver Calendario Mensual de Entrenamientos y Objetivos", expanded=False):
        months_available = []
        cur_date = today.replace(day=1)
        for i in range(4): # Mes actual + 3 meses siguientes
            # Añadir semanas para saltar al siguiente mes
            m_date = (cur_date + timedelta(days=i*32)).replace(day=1)
            if m_date not in months_available:
                months_available.append(m_date)
            
        month_labels = [m.strftime("%B %Y").capitalize() for m in months_available]
        
        es_months = {
            "January": "Enero", "February": "Febrero", "March": "Marzo", "April": "Abril",
            "May": "Mayo", "June": "Junio", "July": "Julio", "August": "Agosto",
            "September": "Septiembre", "October": "Octubre", "November": "Noviembre", "December": "Diciembre"
        }
        for eng, esp in es_months.items():
            month_labels = [l.replace(eng, esp) for l in month_labels]
            
        selected_m_idx = st.radio("Mes a visualizar:", range(len(month_labels)), format_func=lambda i: month_labels[i], horizontal=True)
        selected_date = months_available[selected_m_idx]
        
        # Agrupar eventos por fecha
        events_by_date = {}
        for ev in events:
            d_str = str(ev.get('start_date_local', ''))[:10]
            if d_str:
                if d_str not in events_by_date:
                    events_by_date[d_str] = []
                events_by_date[d_str].append(ev)
                
        cal_html = generate_month_calendar_html(selected_date.year, selected_date.month, events_by_date)
        st.markdown(cal_html, unsafe_allow_html=True)


def render_fitness_freshness_chart(df_well, df_act=None):
    """
    Genera el gráfico de Rendimiento PMC (Fitness & Freshness).
    - Curva CTL (Fitness - Azul)
    - Curva ATL (Fatiga - Rosa/Rojo)
    - Curva TSB (Forma - Verde/Naranja con áreas sombreadas)
    - Barras de Training Load diario (TSS)
    """
    fig = go.Figure()

    if df_well.empty:
        fig.add_annotation(text="No hay datos de fitness/wellness en este periodo", showarrow=False, font=dict(size=14))
        fig.update_layout(height=400)
        return fig

    # Bandas de referencia para TSB (Forma)
    fig.add_hrect(
        y0=-50, y1=-30,
        fillcolor="rgba(239, 68, 68, 0.12)", line_width=0,
        annotation_text="⚠️ Riesgo Sobrecarga (TSB < -30)",
        annotation_position="bottom right",
        annotation_font_size=11,
        annotation_font_color="#ef4444"
    )
    fig.add_hrect(
        y0=-30, y1=-10,
        fillcolor="rgba(16, 185, 129, 0.12)", line_width=0,
        annotation_text="🚀 Zona Óptima de Carga (TSB -30 a -10)",
        annotation_position="top right",
        annotation_font_size=11,
        annotation_font_color="#10b981"
    )
    fig.add_hrect(
        y0=5, y1=25,
        fillcolor="rgba(59, 130, 246, 0.12)", line_width=0,
        annotation_text="🏆 Zona Fresca / Competición (TSB +5 a +25)",
        annotation_position="top right",
        annotation_font_size=11,
        annotation_font_color="#3b82f6"
    )

    # Barras de Carga Diaria (TSS)
    if 'ctlLoad' in df_well.columns and df_well['ctlLoad'].sum() > 0:
        fig.add_trace(go.Bar(
            x=df_well['date'],
            y=df_well['ctlLoad'],
            name='Carga Diaria (TSS)',
            marker_color='rgba(148, 163, 184, 0.4)',
            hoverinfo='x+y',
            hovertemplate='<b>%{x|%d %b %Y}</b><br>TSS: %{y:.0f}<extra></extra>'
        ))

    # Curva de Forma (TSB)
    if 'tsb' in df_well.columns:
        fig.add_trace(go.Scatter(
            x=df_well['date'],
            y=df_well['tsb'],
            mode='lines',
            name='Forma (TSB)',
            line=dict(color='#10b981', width=2),
            hovertemplate='<b>%{x|%d %b %Y}</b><br>TSB (Forma): %{y:.1f}<extra></extra>'
        ))

    # Curva de Fatiga (ATL)
    if 'atl' in df_well.columns:
        fig.add_trace(go.Scatter(
            x=df_well['date'],
            y=df_well['atl'],
            mode='lines',
            name='Fatiga (ATL - 7d)',
            line=dict(color='#f43f5e', width=2.5, dash='dash'),
            hovertemplate='<b>%{x|%d %b %Y}</b><br>ATL (Fatiga): %{y:.1f}<extra></extra>'
        ))

    # Curva de Fitness (CTL)
    if 'ctl' in df_well.columns:
        fig.add_trace(go.Scatter(
            x=df_well['date'],
            y=df_well['ctl'],
            mode='lines',
            name='Fitness (CTL - 42d)',
            line=dict(color='#2563eb', width=3),
            hovertemplate='<b>%{x|%d %b %Y}</b><br>CTL (Fitness): %{y:.1f}<extra></extra>'
        ))

    fig.add_hline(y=0, line_dash="dot", line_color="gray", line_width=1)

    fig.update_layout(
        title=dict(
            text="<b>Evolución del Rendimiento: Fitness (CTL), Fatiga (ATL) y Forma (TSB)</b><br><span style='font-size:12px; font-weight:normal; color:#64748b;'>🔵 Fitness (42d) | 🔴 Fatiga reciente (7d) | 🟢 Forma actual (Zona Verde = Asimilación óptima | Zona Azul = Frescura competitiva)</span>",
            y=0.97, x=0.01, xanchor='left', yanchor='top', font=dict(size=15)
        ),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(showgrid=True, gridcolor="#f1f5f9", title="Carga / Puntos"),
        margin=dict(l=40, r=40, t=75, b=70),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=460
    )

    return fig

def render_weekly_load_chart(df_act):
    """
    Gráfico de Carga Semanal por Disciplina (Stacked Bar Chart).
    """
    fig = go.Figure()
    if df_act.empty:
        fig.add_annotation(text="No hay actividades en este periodo", showarrow=False)
        fig.update_layout(height=350)
        return fig

    df_plot = df_act.copy()
    df_plot['date'] = pd.to_datetime(df_plot['start_date_local'])
    df_plot['week_start'] = df_plot['date'].dt.to_period('W-SUN').apply(lambda r: r.start_time)
    
    # Normalizar deporte
    df_plot['sport_group'] = df_plot['type'].apply(lambda x: get_sport_info(x)[0])
    
    if 'icu_training_load' not in df_plot.columns:
        df_plot['icu_training_load'] = 0
    df_plot['icu_training_load'] = df_plot['icu_training_load'].fillna(0)

    weekly = df_plot.groupby(['week_start', 'sport_group', 'type'])['icu_training_load'].sum().reset_index()
    sports_present = weekly['type'].unique()
    
    for s_type in sports_present:
        s_data = weekly[weekly['type'] == s_type]
        name, icon, color = get_sport_info(s_type)
        fig.add_trace(go.Bar(
            x=s_data['week_start'].dt.strftime('%d %b'),
            y=s_data['icu_training_load'],
            name=f"{icon} {name}",
            marker_color=color,
            hovertemplate=f"<b>Semana: %{{x}}</b><br>{name}: %{{y:.0f}} TSS<extra></extra>"
        ))

    fig.update_layout(
        barmode='stack',
        title=dict(
            text="<b>Carga de Entrenamiento Semanal por Deporte (TSS)</b><br><span style='font-size:12px; font-weight:normal; color:#64748b;'>Volumen de esfuerzo digerido cada semana (100 TSS ≈ 1h a máxima intensidad sostenida)</span>",
            y=0.97, x=0.01, xanchor='left', yanchor='top', font=dict(size=14)
        ),
        xaxis=dict(title="Semana", showgrid=False),
        yaxis=dict(title="Training Load (TSS)", showgrid=True, gridcolor="#f1f5f9"),
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=420,
        margin=dict(l=40, r=40, t=75, b=80)
    )

    return fig

def render_sport_distribution_chart(df_act):
    """
    Gráfico de donut con el porcentaje de tiempo o TSS dedicado a cada disciplina.
    """
    if df_act.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sin datos", showarrow=False)
        fig.update_layout(height=350)
        return fig

    df_plot = df_act.copy()
    df_plot['sport_name'] = df_plot['type'].apply(lambda x: f"{get_sport_info(x)[1]} {get_sport_info(x)[0]}")
    df_plot['hours'] = df_plot['moving_time'] / 3600.0

    summary = df_plot.groupby('sport_name')['hours'].sum().reset_index()
    summary = summary[summary['hours'] > 0]

    color_map = {}
    for st_name in summary['sport_name']:
        for key, (label, icon, color) in SPORT_MAP.items():
            if label in st_name:
                color_map[st_name] = color
                break

    fig = px.pie(
        summary,
        values='hours',
        names='sport_name',
        hole=0.45,
        title="<b>Distribución de Tiempo por Disciplina</b>",
        color='sport_name',
        color_discrete_map=color_map
    )
    
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        insidetextorientation='horizontal',
        hovertemplate='<b>%{label}</b><br>Horas: %{value:.1f}h<br>Porcentaje: %{percent}<extra></extra>'
    )
    
    fig.update_layout(
        title=dict(
            text="<b>Distribución de Tiempo por Disciplina</b><br><span style='font-size:12px; font-weight:normal; color:#64748b;'>Reparto porcentual del volumen total en movimiento</span>",
            y=0.97, x=0.01, xanchor='left', yanchor='top', font=dict(size=14)
        ),
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=420,
        margin=dict(l=20, r=20, t=75, b=20)
    )

    return fig

def render_recovery_chart(df_well):
    """
    Gráfico de tendencia de Frecuencia Cardíaca en Reposo (RHR) y HRV.
    """
    fig = go.Figure()
    
    has_rhr = 'restingHR' in df_well.columns and df_well['restingHR'].dropna().shape[0] > 0
    has_hrv = 'hrv' in df_well.columns and df_well['hrv'].dropna().shape[0] > 0

    if not has_rhr and not has_hrv:
        fig.add_annotation(
            text="💡 El deportista aún no tiene registrados datos de Frecuencia Cardíaca en Reposo o HRV.<br>Se sincronizan automáticamente conectando Garmin, Oura, Whoop o Apple Watch con Intervals.icu.",
            showarrow=False,
            font=dict(size=13, color="#64748b")
        )
        fig.update_layout(height=300, plot_bgcolor="white", paper_bgcolor="white")
        return fig

    if has_hrv:
        fig.add_trace(go.Scatter(
            x=df_well['date'],
            y=df_well['hrv'],
            name='HRV (ms)',
            mode='lines+markers',
            line=dict(color='#8b5cf6', width=2),
            yaxis='y1',
            hovertemplate='<b>%{x|%d %b}</b><br>HRV: %{y:.1f} ms<extra></extra>'
        ))

    if has_rhr:
        fig.add_trace(go.Scatter(
            x=df_well['date'],
            y=df_well['restingHR'],
            name='Pulso en Reposo (bpm)',
            mode='lines+markers',
            line=dict(color='#ef4444', width=2, dash='dot'),
            yaxis='y2',
            hovertemplate='<b>%{x|%d %b}</b><br>RHR: %{y:.0f} ppm<extra></extra>'
        ))

    fig.update_layout(
        title=dict(
            text="<b>Tendencias de Recuperación: HRV y Frecuencia Cardíaca en Reposo</b><br><span style='font-size:12px; font-weight:normal; color:#64748b;'>Marcadores de fatiga nerviosa matutina: subidas continuadas de +4-5 ppm en reposo alertan de sobrecansancio</span>",
            y=0.97, x=0.01, xanchor='left', yanchor='top', font=dict(size=14)
        ),
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(title="HRV (ms)", title_font=dict(color="#8b5cf6"), showgrid=True, gridcolor="#f1f5f9"),
        yaxis2=dict(title="Pulso Reposo (ppm)", title_font=dict(color="#ef4444"), overlaying='y', side='right', showgrid=False),
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=350,
        margin=dict(l=40, r=40, t=75, b=60)
    )

    return fig


def generate_coach_recommendations(df_well, df_act, athlete_name):
    """
    Genera recomendaciones fisiológicas automáticas basadas en la ciencia del entrenamiento (Coggan, Friel).
    """
    recommendations = []
    
    if df_well.empty:
        return [("info", "Datos insuficientes", "No se dispone de suficientes registros para generar recomendaciones automáticas.")]

    latest_well = df_well.iloc[-1]
    ctl = latest_well.get('ctl', 0) or 0
    atl = latest_well.get('atl', 0) or 0
    tsb = latest_well.get('tsb', 0) or (ctl - atl)
    ramp_rate = latest_well.get('rampRate', 0) or 0

    # 1. Diagnóstico de TSB (Forma / Balance de Estrés de Entrenamiento)
    if tsb < -30:
        recommendations.append((
            "error",
            "🚨 Fatiga Extrema / Sobrecarga Crítica (TSB < -30)",
            f"El balance actual de forma es de **{tsb:.1f}** con una fatiga aguda (ATL: {atl:.1f}) muy superior al fitness base (CTL: {ctl:.1f}). "
            "El deportista se encuentra en una zona de alto riesgo de sobreentrenamiento y lesión. "
            "**Recomendación del entrenador:** Programa de inmediato 2 a 4 días de descarga activa (Z1 regenerativo o descanso total) y evita a toda costa sesiones de alta intensidad hasta que el TSB vuelva a subir por encima de -20."
        ))
    elif -30 <= tsb <= -10:
        recommendations.append((
            "success",
            "🚀 Estado de Carga Óptimo / Productivo (TSB entre -30 y -10)",
            f"El TSB actual es de **{tsb:.1f}** (Fitness: {ctl:.1f} | Fatiga: {atl:.1f}). "
            "Esta es la franja de mayor estimulación y adaptación fisiológica del ciclo de entrenamiento. "
            "**Recomendación del entrenador:** Excelente progresión. El atleta está asimilando la carga con éxito. Mantén la estructura de microciclo planificada asegurando una buena nutrición e hidratación post-entreno."
        ))
    elif -10 < tsb <= 5:
        recommendations.append((
            "info",
            "⚖️ Zona Neutra / Transición Equilibrada (TSB entre -10 y +5)",
            f"El TSB actual es de **{tsb:.1f}**. El equilibrio entre fatiga y condición física es estable. "
            "**Recomendación del entrenador:** Ideal para semanas de consolidación o descarga planificada. Si se busca un nuevo pico de condición, es momento de introducir un nuevo bloque de volumen o intensidad."
        ))
    elif 5 < tsb <= 25:
        recommendations.append((
            "success",
            "🏆 Pico de Forma / Óptimo para Competición (TSB entre +5 y +25)",
            f"El TSB se encuentra en **+{tsb:.1f}**, lo que indica que el deportista ha disipado la mayor parte de la fatiga aguda manteniendo una buena base de fitness (CTL: {ctl:.1f}). "
            "**Recomendación del entrenador:** Ventana idónea para competiciones clave (Race A/B) o realización de tests de umbral (FTP, ritmos de carrera). Mantén toques de chispa cortos para no perder activación neuromuscular."
        ))
    else: # tsb > 25
        recommendations.append((
            "warning",
            "📉 Transición Prolongada / Riesgo de Desentrenamiento (TSB > +25)",
            f"El TSB actual es de **+{tsb:.1f}** con una fatiga muy reducida (ATL: {atl:.1f}). "
            "Si no está planificado por descanso de final de temporada o lesión, el deportista está perdiendo adaptaciones aeróbicas y capacidad cardiovascular. "
            "**Recomendación del entrenador:** Reactivar progresivamente el volumen semanal para restablecer el CTL."
        ))

    # 2. Diagnóstico de Ramp Rate (Tasa de subida de carga semanal)
    if ramp_rate > 6.0:
        recommendations.append((
            "warning",
            "⚠️ Rampa de Carga Excesiva (Ramp Rate > 6.0)",
            f"La tasa de progresión semanal de CTL es de **+{ramp_rate:.1f} TSS/semana**. "
            "Los incrementos superiores a 5-6 puntos semanales se asocian fuertemente a lesiones por sobreuso muscular y tendinoso. "
            "**Recomendación del entrenador:** Estabiliza el volumen la próxima semana en lugar de seguir aumentándolo."
        ))
    elif ramp_rate < -5.0:
        recommendations.append((
            "info",
            "📉 Caída Marcada de Carga Semanal",
            f"El CTL está decayendo a un ritmo de **{ramp_rate:.1f} puntos/semana**. Verifica si se debe a una semana de recuperación prevista o a falta de adherencia al plan."
        ))

    # 3. Diagnóstico de Distribución de Disciplinas (Triatlón)
    if not df_act.empty and 'type' in df_act.columns:
        last_3w = pd.to_datetime(datetime.now() - timedelta(days=21))
        recent_acts = df_act[pd.to_datetime(df_act['start_date_local']) >= last_3w]
        if not recent_acts.empty:
            total_sec = recent_acts['moving_time'].sum()
            if total_sec > 0:
                swim_pct = (recent_acts[recent_acts['type'] == 'Swim']['moving_time'].sum() / total_sec) * 100
                bike_pct = (recent_acts[recent_acts['type'].isin(['Ride', 'VirtualRide'])]['moving_time'].sum() / total_sec) * 100
                run_pct = (recent_acts[recent_acts['type'].isin(['Run', 'TrailRun'])]['moving_time'].sum() / total_sec) * 100
                
                # Alertas de desequilibrio
                if swim_pct < 10 and (bike_pct > 20 or run_pct > 20):
                    recommendations.append((
                        "info",
                        "🏊‍♂️ Volumen de Natación Bajo en las Últimas 3 Semanas",
                        f"La natación representa solo el **{swim_pct:.1f}%** del tiempo de entrenamiento reciente. Para objetivos de triatlón, se sugiere aumentar a al menos 15-20% del volumen total para no perder sensaciones hidrodinámicas."
                    ))
                if run_pct > 55:
                    recommendations.append((
                        "warning",
                        "🏃‍♂️ Alto Porcentaje de Impacto (Carrera a pie)",
                        f"La carrera a pie concentra el **{run_pct:.1f}%** de las horas totales recientes. El impacto mecánico repetitivo puede elevar el riesgo de sobrecarga tibial o fascitis. Considera compensar con más volumen en rodillo/bici."
                    ))

    # 4. Diagnóstico de Marcadores de Salud (RHR y HRV)
    if 'restingHR' in df_well.columns:
        valid_rhr = df_well['restingHR'].dropna()
        if len(valid_rhr) >= 10:
            avg_rhr = valid_rhr.iloc[:-3].mean()
            recent_rhr = valid_rhr.iloc[-3:].mean()
            if recent_rhr - avg_rhr >= 4.0:
                recommendations.append((
                    "warning",
                    "💓 Elevación del Pulso en Reposo Basal",
                    f"La frecuencia cardíaca en reposo media de los últimos 3 días ({recent_rhr:.0f} ppm) está **+{recent_rhr - avg_rhr:.1f} ppm** por encima del promedio del mes ({avg_rhr:.0f} ppm). "
                    "Puede indicar fatiga acumulada del sistema nervioso simpático, falta de hidratación o inicio de un proceso vírico/enfermedad."
                ))

    return recommendations

def request_ai_deep_analysis(gemini_api_key, athlete_name, ctl, atl, tsb, ramp_rate, weekly_hours, sports_summary, recent_acts_text, zone_summary=""):
    """
    Genera un informe técnico cualitativo y personalizado utilizando la API de Google Gemini.
    """
    clean_key = str(gemini_api_key).strip()
    if not clean_key:
        return "⚠️ Debes configurar tu Google Gemini API Key para generar informes avanzados con Inteligencia Artificial."

    prompt = f"""
    Eres un entrenador y fisiólogo deportivo de élite especializado en triatlón, ciclismo y carrera de fondo.
    Estás analizando los datos reales de entrenamiento de tu deportista '{athlete_name}' en Intervals.icu.

    Datos Fisiológicos Actuales:
    - Fitness (CTL - Carga Crónica a 42 días): {ctl:.1f}
    - Fatiga (ATL - Carga Aguda a 7 días): {atl:.1f}
    - Forma / Balance (TSB = CTL - ATL): {tsb:.1f}
    - Tasa de Rampa Semanal (Ramp Rate): {ramp_rate:.1f} TSS/semana
    - Horas de entrenamiento semanales promedio: {weekly_hours:.1f}h
    - Desglose de carga por deporte: {sports_summary}
    - Distribución por Zonas de Intensidad: {zone_summary}

    Muestra de entrenamientos recientes:
    {recent_acts_text}

    Por favor, genera un informe técnico estructurado y directo para el entrenador con los siguientes puntos:
    1. 🔍 **Diagnóstico del Estado Actual**: ¿En qué fase de forma se encuentra y cómo está asimilando el volumen?
    2. ⚡ **Análisis de Zonas de Intensidad**: ¿Está respetando la base aeróbica Z1-Z2 o cayendo en la zona gris Z3?
    3. 💪 **Puntos Fuertes Detectados**: Qué aspectos de regularidad, consistencia o intensidades destacan positivamente.
    4. ⚠️ **Riesgos y Áreas de Mejora**: Fatiga excesiva, disciplinas descompensadas o progresión muy abrupta.
    5. 📋 **Prescripción para el Próximo Microciclo**: Recomendaciones concretas para las próximas 1-2 semanas (volumen Z2, toques de ritmo específico, descanso o descarga).

    Redacta en español, tono profesional y riguroso pero motivador y aplicable al día a día. Sé conciso y utiliza formato Markdown.
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={clean_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        res = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=30)
        if res.status_code == 200:
            return res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        else:
            return f"Error al generar informe con Gemini: Código {res.status_code} - {res.text}"
    except Exception as e:
        return f"Excepción de conexión con la IA: {str(e)}"

def render_dashboard(active_athlete, coach_api_key, coach_athlete_id, athletes_list, gemini_api_key=""):
    """
    Función principal que renderiza el Dashboard de Rendimiento en Streamlit.
    """
    st.markdown("## 📊 Dashboard de Rendimiento y Análisis de Cargas")
    
    if not coach_api_key:
        st.warning("⚠️ Introduce tu API Key de Entrenador en la barra lateral para ver los datos de Intervals.icu.")
        return

    # Controles superiores: Rango temporal y botón de refresco
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 1, 1])
    
    with col_ctrl1:
        period_option = st.selectbox(
            "📅 Periodo de análisis:",
            options=["Últimos 30 días", "Últimos 60 días", "Últimos 90 días", "Últimos 6 meses", "Año actual"],
            index=1
        )
    
    today = datetime.now()
    if period_option == "Últimos 30 días":
        oldest_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    elif period_option == "Últimos 60 días":
        oldest_date = (today - timedelta(days=60)).strftime("%Y-%m-%d")
    elif period_option == "Últimos 90 días":
        oldest_date = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    elif period_option == "Últimos 6 meses":
        oldest_date = (today - timedelta(days=180)).strftime("%Y-%m-%d")
    else: # Año actual
        oldest_date = f"{today.year}-01-01"
        
    newest_date = today.strftime("%Y-%m-%d")

    with col_ctrl2:
        st.write("")
        st.write("")
        if st.button("🔄 Actualizar Datos", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    with col_ctrl3:
        athlete_id_raw = str(active_athlete.get("athlete_id", "")).strip()
        coach_id_raw = str(coach_athlete_id).strip()
        is_coach = (athlete_id_raw == coach_id_raw or athlete_id_raw == "0")
        
        st.write("")
        st.write("")
        if is_coach:
            st.caption("👑 Viendo tu cuenta propia")
        else:
            st.caption(f"👤 Atleta ID: {athlete_id_raw}")

    # Descarga de datos
    with st.spinner(f"Cargando métricas de {active_athlete.get('name', 'deportista')} desde Intervals.icu..."):
        data = fetch_athlete_data(athlete_id_raw, coach_api_key, oldest_date, newest_date, is_coach=is_coach)

    activities = data.get("activities", [])
    wellness = data.get("wellness", [])
    events = data.get("events", [])
    fetched_at = data.get("fetched_at", "")

    # Nota de sincronización automática
    st.caption(f"⚡ Datos sincronizados con Intervals.icu (última consulta: {fetched_at} | Caché activa de 5 min). Pulsa **'🔄 Actualizar Datos'** si has subido un nuevo entrenamiento y quieres verlo al instante.")

    # SECCIÓN 1: PRÓXIMOS OBJETIVOS Y CALENDARIO MENSUAL
    render_upcoming_objectives(events)

    # Procesar Wellness DataFrame
    if wellness:
        df_well = pd.DataFrame(wellness)
        df_well['date'] = pd.to_datetime(df_well['id'])
        for col in ['ctl', 'atl', 'rampRate', 'ctlLoad', 'atlLoad', 'restingHR', 'hrv']:
            if col in df_well.columns:
                df_well[col] = pd.to_numeric(df_well[col], errors='coerce')
        df_well = df_well.sort_values('date').reset_index(drop=True)
        if 'ctl' in df_well.columns and 'atl' in df_well.columns:
            df_well['tsb'] = df_well['ctl'].fillna(0) - df_well['atl'].fillna(0)
    else:
        df_well = pd.DataFrame()

    # Procesar Activities DataFrame
    if activities:
        df_act = pd.DataFrame(activities)
        df_act['date'] = pd.to_datetime(df_act['start_date_local'])
        if 'type' not in df_act.columns:
            df_act['type'] = 'Other'
        else:
            df_act['type'] = df_act['type'].fillna('Other').astype(str)
        if 'name' not in df_act.columns:
            df_act['name'] = 'Entrenamiento'
        else:
            df_act['name'] = df_act['name'].fillna('Entrenamiento').astype(str)
        if 'moving_time' not in df_act.columns:
            df_act['moving_time'] = 0.0
        else:
            df_act['moving_time'] = pd.to_numeric(df_act['moving_time'], errors='coerce').fillna(0.0)
        if 'distance' not in df_act.columns:
            df_act['distance'] = 0.0
        else:
            df_act['distance'] = pd.to_numeric(df_act['distance'], errors='coerce').fillna(0.0)
        if 'icu_training_load' not in df_act.columns:
            df_act['icu_training_load'] = 0.0
        else:
            df_act['icu_training_load'] = pd.to_numeric(df_act['icu_training_load'], errors='coerce').fillna(0.0)
        if 'icu_intensity' not in df_act.columns:
            df_act['icu_intensity'] = 0.0
        else:
            df_act['icu_intensity'] = pd.to_numeric(df_act['icu_intensity'], errors='coerce').fillna(0.0)
        if 'average_heartrate' not in df_act.columns:
            df_act['average_heartrate'] = 0.0
        else:
            df_act['average_heartrate'] = pd.to_numeric(df_act['average_heartrate'], errors='coerce').fillna(0.0)

        df_act = df_act.sort_values('date', ascending=False).reset_index(drop=True)
    else:
        df_act = pd.DataFrame()

    # Métricas Principales (KPI Cards)
    st.markdown("---")
    
    current_ctl = 0.0
    current_atl = 0.0
    current_tsb = 0.0
    current_ramp = 0.0
    delta_ctl = 0.0

    if not df_well.empty:
        last_row = df_well.iloc[-1]
        current_ctl = float(last_row.get('ctl', 0) or 0)
        current_atl = float(last_row.get('atl', 0) or 0)
        current_tsb = float(last_row.get('tsb', 0) or (current_ctl - current_atl))
        current_ramp = float(last_row.get('rampRate', 0) or 0)
        
        if len(df_well) >= 7:
            week_ago_ctl = float(df_well.iloc[-7].get('ctl', 0) or 0)
            delta_ctl = current_ctl - week_ago_ctl

    total_hours = (df_act['moving_time'].sum() / 3600.0) if not df_act.empty and 'moving_time' in df_act.columns else 0.0
    total_tss = df_act['icu_training_load'].sum() if not df_act.empty and 'icu_training_load' in df_act.columns else 0.0
    total_acts = len(df_act)

    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    
    with kpi1:
        st.metric(
            label="🏋️ Fitness (CTL)",
            value=f"{current_ctl:.1f}",
            delta=f"{delta_ctl:+.1f} (últimos 7d)",
            help="Chronic Training Load (Carga Crónica a 42 días). Refleja tu capacidad de rendimiento acumulada."
        )
    with kpi2:
        st.metric(
            label="⚡ Fatiga (ATL)",
            value=f"{current_atl:.1f}",
            delta=f"{current_atl - current_ctl:+.1f} vs Fitness",
            delta_color="inverse",
            help="Acute Training Load (Fatiga Aguda a 7 días). Refleja el cansancio reciente."
        )
    with kpi3:
        tsb_status = "Productivo" if -30 <= current_tsb <= -10 else ("Fresco" if current_tsb > 0 else "Sobrecarga")
        st.metric(
            label=f"🎯 Forma (TSB: {tsb_status})",
            value=f"{current_tsb:+.1f}",
            help="Training Stress Balance (Forma = CTL - ATL). -30 a -10 indica carga productiva; +5 a +25 indica frescura óptima para competir."
        )
    with kpi4:
        st.metric(
            label="📈 Rampa Semanal",
            value=f"{current_ramp:+.1f}",
            help="Tasa de subida de carga por semana. Lo ideal es mantenerse entre +2 y +5. Si supera +6-8 hay riesgo de sobreuso."
        )
    with kpi5:
        st.metric(
            label="⏱️ Volumen Total",
            value=f"{total_hours:.1f} h",
            delta=f"{int(total_tss)} TSS ({total_acts} sesiones)",
            help="Total de horas y TSS completados en el periodo seleccionado."
        )

    # Veredicto Pedagógico del Estado Actual en 1 vistazo
    col_stat1, col_stat2 = st.columns([2, 1])
    with col_stat1:
        if -30 <= current_tsb <= -10:
            st.success(f"🚀 **Fase Actual: Asimilación Productiva de Carga** (TSB: {current_tsb:.1f} | Fitness: {current_ctl:.1f})\n\nTu organismo está asimilando el entrenamiento en la zona dulce de desarrollo cardiovascular. Buen equilibrio entre fatiga y adaptación.")
        elif -10 < current_tsb <= 5:
            st.info(f"⚖️ **Fase Actual: Equilibrio y Consolidación** (TSB: {current_tsb:.1f} | Fitness: {current_ctl:.1f})\n\nLa fatiga aguda y tu condición física están niveladas. Momento ideal para asentar sensaciones o preparar el siguiente bloque de carga.")
        elif 5 < current_tsb <= 25:
            st.success(f"🏆 **Fase Actual: Frescura Competitiva** (TSB: +{current_tsb:.1f} | Fitness: {current_ctl:.1f})\n\nHas disipado la fatiga acumulada manteniendo el motor en marcha. Estás en el punto óptimo para rendir al máximo en competiciones o tests.")
        elif current_tsb < -30:
            st.error(f"🛑 **Fase Actual: Fatiga Elevada / Riesgo de Sobrecarga** (TSB: {current_tsb:.1f})\n\nEl cansancio acumulado en los últimos 7 días supera el ritmo de recuperación. Conviene priorizar descanso, hidratación y rodajes muy suaves.")
        else:
            st.warning(f"📉 **Fase Actual: Descanso Prolongado** (TSB: +{current_tsb:.1f})\n\nLa fatiga ha bajado al mínimo. Si no estás en parón de fin de temporada, es momento de reactivar progresivamente el volumen.")
    with col_stat2:
        st.info("💡 **Cómo leer las curvas abajo:**\n\n• **Línea Azul (CTL):** Tu motor construido (42 días).\n• **Línea Rosa (ATL):** Cansancio reciente (7 días).\n• **Línea Verde (TSB):** Frescura diaria (Azul menos Rosa).")

    # GRÁFICA PRINCIPAL: Fitness & Freshness (PMC)
    st.plotly_chart(render_fitness_freshness_chart(df_well, df_act), use_container_width=True)

    # GRÁFICAS SECUNDARIAS: Carga Semanal por Deporte + Donut de Horas
    col_g1, col_g2 = st.columns([3, 2])
    with col_g1:
        st.plotly_chart(render_weekly_load_chart(df_act), use_container_width=True)
    with col_g2:
        st.plotly_chart(render_sport_distribution_chart(df_act), use_container_width=True)

    # SECCIÓN NUEVA: ANÁLISIS DE TIEMPO POR ZONAS (80/20)
    st.markdown("---")
    st.markdown("### ⚡ Distribución y Control de Zonas de Intensidad")
    
    zone_data = extract_zones_data(activities)
    
    if zone_data["has_zones"]:
        # Métricas de polarización en 3 columnas
        col_z1, col_z2, col_z3 = st.columns(3)
        with col_z1:
            st.metric(
                label="🟢 Baja Intensidad (Z1 - Z2)",
                value=f"{zone_data['low_pct']:.1f}%",
                delta=f"{zone_data['hours'][0] + zone_data['hours'][1]:.1f} horas (Obj: 75-85%)",
                help="Base aeróbica pura. Debe ser la base de la pirámide (75% - 85% del tiempo total)."
            )
        with col_z2:
            st.metric(
                label="🟡 Media Intensidad / Tempo (Z3)",
                value=f"{zone_data['mid_pct']:.1f}%",
                delta=f"{zone_data['hours'][2]:.1f} horas (Obj: 5-15%)",
                delta_color="off" if zone_data['mid_pct'] <= 15 else "inverse",
                help="Zona gris / Tempo. Si supera el 20-25% indica que se está rodando demasiado fuerte en días fáciles."
            )
        with col_z3:
            st.metric(
                label="🔴 Alta Intensidad / Calidad (Z4 - Z5+)",
                value=f"{zone_data['high_pct']:.1f}%",
                delta=f"{zone_data['hours'][3] + zone_data['hours'][4]:.1f} horas (Obj: 10-15%)",
                help="Umbral y VO2max. Estimula la potencia y el ritmo de competición (10% - 15% del tiempo)."
            )
            
        st.plotly_chart(render_zone_distribution_chart(zone_data), use_container_width=True)
        
        # Recomendaciones específicas de zonas
        z_recs = generate_zone_recommendations(zone_data)
        for z_lvl, z_tit, z_desc in z_recs:
            if z_lvl == "error":
                st.error(f"**{z_tit}**\n\n{z_desc}")
            elif z_lvl == "warning":
                st.warning(f"**{z_tit}**\n\n{z_desc}")
            elif z_lvl == "success":
                st.success(f"**{z_tit}**\n\n{z_desc}")
            else:
                st.info(f"**{z_tit}**\n\n{z_desc}")
    else:
        st.info("💡 No se detectaron zonas registradas en este periodo. Se registrarán automáticamente cuando los deportistas sincronicen actividades con pulsómetro.")

    # GRÁFICA DE RECUPERACIÓN & WELLNESS
    st.plotly_chart(render_recovery_chart(df_well), use_container_width=True)

    # SECCIÓN: RECOMENDACIONES DEL ENTRENADOR
    st.markdown("---")
    st.markdown("### 💡 Diagnóstico General y Recomendaciones del Entrenador")
    
    recs = generate_coach_recommendations(df_well, df_act, active_athlete.get('name', 'Deportista'))
    
    for level, title, desc in recs:
        if level == "error":
            st.error(f"**{title}**\n\n{desc}")
        elif level == "warning":
            st.warning(f"**{title}**\n\n{desc}")
        elif level == "success":
            st.success(f"**{title}**\n\n{desc}")
        else:
            st.info(f"**{title}**\n\n{desc}")

    # SECCIÓN: REVISIÓN EXHAUSTIVA DE SESIONES Y SENSACIONES (FEEDBACK CLAVE)
    st.markdown("---")
    st.markdown("### 🧠 Revisión Exhaustiva de Entrenamientos y Sensaciones")
    st.caption("Revisión profunda cruzando datos fisiológicos objetivos (TSS, FC, ritmo, distancia) con el esfuerzo percibido (RPE 1-10) y las sensaciones reales reportadas por el deportista.")
    
    key_sessions = report_generator.analyze_key_sessions(activities)
    
    # Calcular métricas globales de sensaciones del periodo
    rpes = []
    feels = []
    for a in activities:
        r_val = a.get('icu_rpe') if a.get('icu_rpe') is not None else a.get('perceived_exertion')
        if r_val is not None:
            try:
                rpes.append(float(r_val))
            except (ValueError, TypeError):
                pass
        f_val = a.get('feel')
        if f_val is not None:
            try:
                feels.append(int(f_val))
            except (ValueError, TypeError):
                pass

    athlete_comments_count = sum(1 for a in activities if report_generator.clean_athlete_comment(a.get('description'), a.get('icu_athlete_comments')))
    
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        avg_rpe = (sum(rpes) / len(rpes)) if rpes else None
        rpe_lbl, rpe_col = report_generator.format_rpe(round(avg_rpe)) if avg_rpe is not None else ("Sin registros", "#94a3b8")
        st.metric(
            label="📊 Dificultad Media (RPE)",
            value=f"{avg_rpe:.1f} / 10" if avg_rpe is not None else "N/D",
            delta=rpe_lbl if avg_rpe is not None else None,
            help="Media de esfuerzo percibido en la escala Borg CR10 reportado en las actividades."
        )
    with col_f2:
        avg_feel = (sum(feels) / len(feels)) if feels else None
        f_lbl, f_emo, f_col = report_generator.format_feel(round(avg_feel)) if avg_feel is not None else ("Sin registros", "⚪", "#94a3b8")
        st.metric(
            label="🔋 Sensación Promedio",
            value=f"{f_emo} {avg_feel:.1f} / 5" if avg_feel is not None else "N/D",
            delta=f_lbl if avg_feel is not None else None,
            help="Media de sensaciones (1=Terrible a 5=Fuerte/Excelente)."
        )
    with col_f3:
        st.metric(
            label="💬 Sesiones con Feedback",
            value=f"{athlete_comments_count} sesiones",
            help="Número de entrenamientos donde el deportista dejó notas, sensaciones o comentarios escritos."
        )
    with col_f4:
        st.metric(
            label="🎯 Sesiones Clave Detectadas",
            value=f"{len(key_sessions)} sesiones",
            help="Competiciones, tiradas largas, series de ritmo o trabajo de fuerza analizados a fondo."
        )

    if key_sessions:
        st.markdown("#### 🔍 Desglose y Veredicto Técnico de Sesiones Clave:")
        for idx, s in enumerate(key_sessions):
            f_lbl, f_emo, f_col = report_generator.format_feel(s.get('feel'))
            rpe_lbl, rpe_col = report_generator.format_rpe(s.get('rpe'))
            d_str = s.get('date', '')
            try:
                date_formatted = datetime.strptime(d_str, '%Y-%m-%d').strftime('%d/%m/%Y')
            except Exception:
                date_formatted = d_str
            
            with st.container():
                st.markdown(f"""
                <div style="background: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid #0284c7; border-radius: 8px; padding: 14px 18px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; flex-wrap: wrap; gap: 8px;">
                        <div>
                            <span style="background: #f1f5f9; color: #1e293b; font-weight: 600; font-size: 0.8rem; padding: 3px 8px; border-radius: 4px; margin-right: 8px;">{s.get('tag', 'Sesión')}</span>
                            <span style="font-weight: 700; font-size: 1.05rem; color: #0f172a;">{s.get('name', 'Entrenamiento')}</span>
                            <span style="color: #64748b; font-size: 0.85rem; margin-left: 8px;">📅 {date_formatted}</span>
                        </div>
                        <div>
                            <span style="background: {f_col}22; color: {f_col}; font-weight: 600; font-size: 0.8rem; padding: 3px 8px; border-radius: 4px; margin-right: 6px;">Sensación: {f_emo} {f_lbl}</span>
                            <span style="background: {rpe_col}22; color: {rpe_col}; font-weight: 600; font-size: 0.8rem; padding: 3px 8px; border-radius: 4px;">RPE: {rpe_lbl}</span>
                        </div>
                    </div>
                    <div style="color: #475569; font-size: 0.9rem; margin-bottom: 8px;">
                        ⏱️ <b>Tiempo:</b> {s.get('duration_str', '-')} &nbsp;|&nbsp; 
                        📏 <b>Distancia:</b> {s.get('distance_km', 0)} km &nbsp;|&nbsp; 
                        ⚡ <b>Carga:</b> {s.get('tss', 0)} TSS &nbsp;|&nbsp; 
                        ❤️ <b>FC Media:</b> {s.get('avg_hr', 0)} ppm
                    </div>
                    <div style="background: #f8fafc; border-radius: 6px; padding: 10px 12px; font-size: 0.9rem; color: #1e293b; line-height: 1.45; border-left: 3px solid #0284c7;">
                        <b>Diagnóstico Fisiológico:</b> {s.get('verdict', '')}
                    </div>
                    {f'''<div style="margin-top: 8px; padding: 8px 12px; background: #eff6ff; border-radius: 6px; font-size: 0.88rem; color: #1e40af;">
                        🗣️ <b>Comentario del deportista:</b> "<em>{s.get('comment')}</em>"
                    </div>''' if s.get('comment') else ''}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("💡 No se detectaron sesiones clave de alta exigencia o tiradas largas en este periodo.")

    # Generación de preguntas activas de feedback
    st.markdown("#### 🗣️ Preguntas Clave para Solicitar Feedback al Deportista:")
    st.caption("Copia y envía estas preguntas directas a tu atleta por WhatsApp o chat para profundizar en su recuperación y sensaciones:")
    
    feedback_questions = report_generator.generate_coach_feedback_questions(
        key_sessions=key_sessions,
        wellness_data={},
        skipped_count=0,
        athlete_name=active_athlete.get('name', 'Deportista')
    )
    for q_idx, q in enumerate(feedback_questions, 1):
        st.info(f"**Pregunta {q_idx}:** {q}")

    # SECCIÓN: ANÁLISIS PROFUNDO CON IA (GEMINI)
    with st.expander("🤖 Asistente de Análisis con Inteligencia Artificial (Gemini)", expanded=False):
        st.markdown(
            "Haz clic abajo para que la Inteligencia Artificial deportiva analice en profundidad todas las métricas fisiológicas de este deportista "
            "y te genere un informe técnico con recomendaciones para los próximos microciclos."
        )
        
        gemini_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        
        col_ai_btn, col_ai_key = st.columns([1, 2])
        with col_ai_key:
            input_ai_key = st.text_input("Gemini API Key (Opcional si ya está en .env):", value=gemini_key, type="password")
            
        with col_ai_btn:
            st.write("")
            st.write("")
            generate_ai_btn = st.button("🚀 Generar Informe IA", use_container_width=True)

        if generate_ai_btn:
            key_to_use = input_ai_key or gemini_key
            if not key_to_use:
                st.error("Por favor, introduce tu clave de Google Gemini API para usar el asistente.")
            else:
                with st.spinner("🧠 Generando informe técnico con Inteligencia Artificial..."):
                    if not df_act.empty:
                        sports_sum = df_act.groupby('type')['moving_time'].sum()
                        sports_summary_str = ", ".join([f"{k}: {v/3600.0:.1f}h" for k, v in sports_sum.items()])
                        sample_acts = "\n".join([
                            f"- {str(row.get('start_date_local', ''))[:10]} | {row.get('type', '')} | {row.get('name', '')} | TSS: {row.get('icu_training_load', 0)} | {format_duration(row.get('moving_time', 0))}"
                            for _, row in df_act.head(8).iterrows()
                        ])
                    else:
                        sports_summary_str = "Sin actividades registradas"
                        sample_acts = "Ninguna"

                    weekly_avg_hours = total_hours / max(1, (len(df_well) / 7.0))
                    
                    z_sum_str = f"Z1-Z2 (Base): {zone_data['low_pct']:.1f}% | Z3 (Tempo): {zone_data['mid_pct']:.1f}% | Z4-Z5+ (Alta): {zone_data['high_pct']:.1f}%" if zone_data['has_zones'] else "Sin datos de zonas"

                    report = request_ai_deep_analysis(
                        gemini_api_key=key_to_use,
                        athlete_name=active_athlete.get('name', 'Deportista'),
                        ctl=current_ctl,
                        atl=current_atl,
                        tsb=current_tsb,
                        ramp_rate=current_ramp,
                        weekly_hours=weekly_avg_hours,
                        sports_summary=sports_summary_str,
                        recent_acts_text=sample_acts,
                        zone_summary=z_sum_str
                    )
                    
                    st.markdown("#### 📋 Informe Técnico del Deportista:")
                    st.markdown(report)

    # SECCIÓN: HISTORIAL DE ACTIVIDADES DETALLADO
    st.markdown("---")
    st.markdown("### 📋 Historial Reciente de Entrenamientos")
    
    if not df_act.empty:
        raw_sports = [str(s) for s in df_act['type'].dropna().unique().tolist() if str(s).strip() != ""]
        all_sports = sorted(list(set(raw_sports)))
        selected_sports = st.multiselect(
            "Filtrar por deporte:",
            options=all_sports,
            default=all_sports,
            format_func=lambda x: f"{get_sport_info(x)[1]} {get_sport_info(x)[0]}"
        )
        
        filtered_act = df_act[df_act['type'].isin(selected_sports)].copy()
        
        table_df = pd.DataFrame()
        table_df['Fecha'] = filtered_act['date'].dt.strftime('%d/%m/%Y %H:%M')
        table_df['Deporte'] = filtered_act['type'].apply(lambda x: f"{get_sport_info(x)[1]} {get_sport_info(x)[0]}")
        table_df['Nombre'] = filtered_act['name']
        table_df['Tiempo'] = filtered_act['moving_time'].apply(format_duration)
        table_df['Distancia (km)'] = (filtered_act['distance'] / 1000.0).round(2).fillna(0)
        table_df['TSS'] = filtered_act['icu_training_load'].fillna(0).astype(int)
        table_df['IF (%)'] = filtered_act['icu_intensity'].fillna(0).round(1)
        table_df['FC Media'] = filtered_act['average_heartrate'].fillna(0).astype(int)
        
        if 'feel' in filtered_act.columns:
            table_df['Sensación'] = filtered_act['feel'].apply(lambda f: f"{report_generator.format_feel(f)[1]} {report_generator.format_feel(f)[0]}" if pd.notna(f) else "-")
        else:
            table_df['Sensación'] = "-"

        rpe_col_src = 'icu_rpe' if 'icu_rpe' in filtered_act.columns else ('perceived_exertion' if 'perceived_exertion' in filtered_act.columns else None)
        if rpe_col_src:
            table_df['RPE (1-10)'] = filtered_act[rpe_col_src].apply(lambda r: f"{int(r)}/10" if pd.notna(r) and str(r).strip() != "" else "-")
        else:
            table_df['RPE (1-10)'] = "-"
        
        st.dataframe(
            table_df,
            use_container_width=True,
            column_config={
                "Fecha": st.column_config.TextColumn(width="medium"),
                "Deporte": st.column_config.TextColumn(width="small"),
                "Nombre": st.column_config.TextColumn(width="large"),
                "Distancia (km)": st.column_config.NumberColumn(format="%.2f km"),
                "TSS": st.column_config.NumberColumn(format="%d"),
                "IF (%)": st.column_config.NumberColumn(format="%.1f%%"),
                "FC Media": st.column_config.NumberColumn(format="%d ppm"),
                "Sensación": st.column_config.TextColumn(width="medium"),
                "RPE (1-10)": st.column_config.TextColumn(width="small")
            },
            hide_index=True
        )
    else:
        st.info("No se encontraron entrenamientos realizados en el periodo seleccionado.")
