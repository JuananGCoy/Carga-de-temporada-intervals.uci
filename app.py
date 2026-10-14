import streamlit as st
import pandas as pd
import os
import json
import time
from dotenv import load_dotenv
from processing import process_excel, sanitize_workout_text
from intervals_api import upload_to_intervals
import dashboard

load_dotenv()

# Configuración de la página
st.set_page_config(page_title="Intervals.icu Suite Profesional", page_icon="🏋️", layout="wide")

# Estilos Premium personalizados con CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    /* Configuración de tipografía global */
    html, body, [class*="css"], .stMarkdown, .stText {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Encabezados y títulos con gradiente */
    .main-title {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #1e3a8a, #0284c7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1.5rem;
        text-shadow: 0px 4px 10px rgba(0, 0, 0, 0.05);
    }
    
    /* Botones primarios premium */
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #1e40af, #0369a1);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    div.stButton > button:first-child:hover {
        background: linear-gradient(135deg, #1d4ed8, #0284c7);
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    
    /* Tarjetas y contenedores con diseño limpio */
    .stExpander {
        border-radius: 10px !important;
        border: 1px solid #e2e8f0 !important;
        background-color: #f8fafc !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
    }
</style>
""", unsafe_allow_html=True)

import auth_manager

# --- GESTIÓN DE SESIÓN Y AUTENTICACIÓN MULTI-ENTRENADOR ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None

def render_login_page():
    st.markdown('<h1 class="main-title" style="text-align: center;">Triathlon Intervals.icu Suite 🏊‍♂️🚴‍♂️🏃‍♂️</h1>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b; font-size: 1.15rem; margin-bottom: 2rem;'>Plataforma profesional para entrenadores y deportistas de triatlón, ciclismo y carrera</p>", unsafe_allow_html=True)

    col_empty1, col_center, col_empty2 = st.columns([1, 2, 1])
    with col_center:
        tab_login, tab_register = st.tabs(["🔑 Iniciar Sesión", "📝 Registrar Nuevo Entrenador"])

        with tab_login:
            st.markdown("#### Acceso a tu Panel de Entrenador")
            with st.form("login_form"):
                login_user = st.text_input("Usuario", placeholder="ej. juanan").strip().lower()
                login_pass = st.text_input("Contraseña", type="password", placeholder="••••••••")
                submit_login = st.form_submit_button("🚀 Acceder a mi Panel", use_container_width=True)

                if submit_login:
                    if not login_user or not login_pass:
                        st.error("Por favor, introduce tu usuario y contraseña.")
                    else:
                        user = auth_manager.authenticate(login_user, login_pass)
                        if user:
                            st.session_state["authenticated"] = True
                            st.session_state["username"] = user["username"]
                            st.session_state["current_user"] = user
                            st.success(f"¡Bienvenido de nuevo, {user.get('display_name', login_user)}!")
                            time.sleep(0.4)
                            st.rerun()
                        else:
                            st.error("Usuario o contraseña incorrectos.")

            st.info("💡 **Tu cuenta:** Ya está preconfigurada con tus deportistas actuales. Usuario: **`juanan`** | Contraseña: **`juanan123`** (puedes cambiarla una vez dentro).")

        with tab_register:
            st.markdown("#### Alta de Nuevo Entrenador")
            st.caption("Crea tu espacio de trabajo privado. Tus deportistas y datos estarán 100% aislados de otros entrenadores.")
            with st.form("register_form"):
                reg_name = st.text_input("Nombre completo / Alias", placeholder="Ej. Carlos Gómez").strip()
                reg_user = st.text_input("Nombre de usuario (minúsculas, sin espacios)", placeholder="Ej. carlos_coach").strip().lower()
                reg_email = st.text_input("Email de contacto", placeholder="carlos@email.com").strip()
                col_p1, col_p2 = st.columns(2)
                reg_pass = col_p1.text_input("Contraseña", type="password")
                reg_pass2 = col_p2.text_input("Confirmar contraseña", type="password")
                
                st.markdown("##### ⚡ Vinculación con Intervals.icu (Opcional ahora)")
                reg_api_key = st.text_input("Tu Intervals.icu API Key (Entrenador)", type="password", placeholder="Opcional, puedes configurarlo dentro")
                reg_ath_id = st.text_input("Tu Intervals.icu Athlete ID", placeholder="Ej. 123456 (Opcional)")

                submit_reg = st.form_submit_button("✨ Crear Mi Cuenta de Entrenador", use_container_width=True)

                if submit_reg:
                    if not reg_user or not reg_pass:
                        st.error("El usuario y la contraseña son obligatorios.")
                    elif reg_pass != reg_pass2:
                        st.error("Las contraseñas no coinciden.")
                    else:
                        ok, msg = auth_manager.register_user(
                            username=reg_user,
                            password=reg_pass,
                            display_name=reg_name or reg_user.capitalize(),
                            email=reg_email,
                            coach_api_key=reg_api_key,
                            coach_athlete_id=reg_ath_id
                        )
                        if ok:
                            st.success("¡Cuenta creada correctamente! Pasa a la pestaña 'Iniciar Sesión' para acceder.")
                        else:
                            st.error(msg)

if not st.session_state["authenticated"]:
    render_login_page()
    st.stop()

# Si está autenticado, cargar su configuración aislada
current_username = st.session_state["username"]
current_user = auth_manager.get_user(current_username)
if not current_user:
    st.session_state["authenticated"] = False
    st.rerun()

config_data = current_user

def save_config(new_config):
    auth_manager.save_user_config(current_username, new_config)

# Título de la app
st.markdown('<h1 class="main-title">Triathlon Intervals.icu Suite 🏊‍♂️🚴‍♂️🏃‍♂️</h1>', unsafe_allow_html=True)

# --- SIDEBAR: CONFIGURACIÓN Y DEPORTISTAS ---
with st.sidebar:
    st.markdown(f"### 👑 Entrenador: **{config_data.get('display_name', current_username)}**")
    st.caption(f"Sesión activa: `@{current_username}`")

    col_out, col_chpwd = st.columns(2)
    with col_out:
        if st.button("🚪 Salir", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["username"] = None
            st.session_state["current_user"] = None
            st.rerun()

    with st.expander("🔐 Cambiar Contraseña"):
        with st.form("change_pwd_form"):
            old_p = st.text_input("Contraseña actual", type="password")
            new_p = st.text_input("Nueva contraseña", type="password")
            btn_cp = st.form_submit_button("Actualizar")
            if btn_cp:
                ok, msg = auth_manager.change_password(current_username, old_p, new_p)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    st.markdown("---")
    st.markdown("## ⚙️ Claves de Intervals.icu")
    
    # Entrada para la clave global del entrenador
    coach_api_key_input = st.text_input(
        "Tu API Key de Entrenador (Global)",
        type="password",
        value=config_data.get("coach_api_key", ""),
        help="Clave API de Intervals.icu de tu propia cuenta de entrenador."
    )
    
    # Entrada para la ID del entrenador
    coach_athlete_id_input = st.text_input(
        "Tu Athlete ID de Entrenador",
        value=config_data.get("coach_athlete_id", ""),
        help="Tu ID personal de Intervals.icu (usado para detectar cuándo te estás subiendo entrenamientos a ti mismo)."
    )
    
    if coach_api_key_input != config_data.get("coach_api_key", "") or coach_athlete_id_input != config_data.get("coach_athlete_id", ""):
        config_data["coach_api_key"] = coach_api_key_input
        config_data["coach_athlete_id"] = coach_athlete_id_input
        save_config(config_data)
        st.success("Configuración de entrenador guardada")
        st.rerun()

    st.markdown("---")
    st.markdown("## 👤 Deportistas")
    
    athletes_list = config_data["athletes"]
    athlete_names = [a["name"] for a in athletes_list]
    
    selected_name = st.selectbox(
        "Selecciona el deportista activo",
        options=["-- Registrar Nuevo --"] + athlete_names,
        index=1 if len(athlete_names) > 0 else 0
    )
    
    active_athlete = None
    
    if selected_name == "-- Registrar Nuevo --":
        st.info("Ingresa los datos del deportista a vincular con tu cuenta de entrenador.")
        with st.form("new_athlete_form", clear_on_submit=True):
            new_name = st.text_input("Nombre / Alias", placeholder="Ej. Juan Pérez")
            new_id = st.text_input("Athlete ID", placeholder="Ej. 123456")
            new_email = st.text_input("📧 Email (opcional)", placeholder="deportista@email.com")
            submit_btn = st.form_submit_button("Añadir Deportista")
            
            if submit_btn:
                if not new_name or not new_id:
                    st.error("El nombre y el Athlete ID son obligatorios.")
                else:
                    config_data["athletes"].append({
                        "name": new_name,
                        "athlete_id": str(new_id).strip(),
                        "email": new_email.strip()
                    })
                    save_config(config_data)
                    st.success(f"¡Deportista '{new_name}' añadido con éxito!")
                    st.rerun()
    else:
        active_athlete = next(a for a in athletes_list if a["name"] == selected_name)
        is_coach_account = (str(active_athlete["athlete_id"]).strip() == str(config_data["coach_athlete_id"]).strip())
        role_label = "Cuenta Entrenador (Propia)" if is_coach_account else "Deportista Tutorizado"
        st.success(f"Activo: **{active_athlete['name']}** ({role_label})")
        
        with st.expander("⚙️ Editar / Eliminar Deportista"):
            with st.form(f"edit_athlete_{active_athlete['name']}"):
                edit_name = st.text_input("Nombre / Alias", value=active_athlete["name"])
                edit_id = st.text_input("Athlete ID", value=active_athlete["athlete_id"])
                edit_email = st.text_input(
                    "📧 Email del deportista",
                    value=active_athlete.get("email", ""),
                    placeholder="deportista@email.com",
                    help="Email para recibir los informes semanales/mensuales automáticos"
                )
                
                col_upd, col_del = st.columns(2)
                update_btn = col_upd.form_submit_button("Guardar Cambios")
                delete_btn = col_del.form_submit_button("🗑️ Eliminar", type="primary")
                
                if update_btn:
                    active_athlete["name"] = edit_name
                    active_athlete["athlete_id"] = str(edit_id).strip()
                    active_athlete["email"] = edit_email.strip()
                    save_config(config_data)
                    st.success("Cambios guardados con éxito")
                    st.rerun()
                    
                if delete_btn:
                    config_data["athletes"].remove(active_athlete)
                    save_config(config_data)
                    st.warning("Deportista eliminado")
                    st.rerun()

    st.markdown("---")
    st.markdown("### 🕒 Configuración de Subida")
    default_hour = st.time_input("Hora de inicio por defecto", value=pd.to_datetime("08:00").time())



def render_email_tab(active_athlete, config_data):
    """
    Renderiza la pestaña de gestión de informes automáticos por email.
    Permite configurar SMTP, emails de deportistas, previsualizar y enviar informes.
    """
    import report_generator
    import email_service
    import streamlit.components.v1 as components

    st.markdown("### 📧 Informes Automáticos por Email")
    st.caption("Envía resúmenes semanales y balances mensuales personalizados a cada deportista directamente desde aquí.")

    athletes_list = config_data.get("athletes", [])
    smtp_config = config_data.get("smtp_config", {
        "server": "smtp.gmail.com",
        "port": 587,
        "user": "",
        "password": "",
        "coach_name": "Juanan Coy - Entrenador",
        "bcc_coach": True
    })

    # ─── SECCIÓN 1: Configuración SMTP ───────────────────────────────────────
    with st.expander("⚙️ Configuración del Servidor de Correo (SMTP)", expanded=not smtp_config.get("user")):
        with st.form("smtp_form"):
            col1, col2 = st.columns(2)
            with col1:
                smtp_server = st.text_input("Servidor SMTP", value=smtp_config.get("server", "smtp.gmail.com"),
                    help="Gmail: smtp.gmail.com | Outlook: smtp.office365.com")
                smtp_user = st.text_input("Email del entrenador (remitente)", value=smtp_config.get("user", ""),
                    placeholder="tu@gmail.com")
                smtp_coach_name = st.text_input("Nombre en el email", value=smtp_config.get("coach_name", "Juanan Coy - Entrenador"))
            with col2:
                smtp_port = st.number_input("Puerto", value=int(smtp_config.get("port", 587)), min_value=1, max_value=65535,
                    help="587 (STARTTLS, recomendado) | 465 (SSL)")
                smtp_password = st.text_input("Contraseña / App Password", type="password", value=smtp_config.get("password", ""),
                    help="Para Gmail: usa una 'Contraseña de Aplicación' (no la contraseña normal)")
                smtp_bcc = st.checkbox("Enviarme copia (BCC) de cada informe", value=smtp_config.get("bcc_coach", True))

            col_save, col_test = st.columns(2)
            save_smtp_btn = col_save.form_submit_button("💾 Guardar Configuración SMTP")
            test_smtp_btn = col_test.form_submit_button("🔌 Probar Conexión")

            if save_smtp_btn or test_smtp_btn:
                new_smtp = {
                    "server": smtp_server.strip(),
                    "port": int(smtp_port),
                    "user": smtp_user.strip(),
                    "password": smtp_password,
                    "coach_name": smtp_coach_name.strip(),
                    "bcc_coach": smtp_bcc
                }
                config_data["smtp_config"] = new_smtp
                save_config(config_data)
                smtp_config = new_smtp

                if save_smtp_btn:
                    st.success("✅ Configuración SMTP guardada correctamente.")

                if test_smtp_btn:
                    if not smtp_user or not smtp_password:
                        st.error("Introduce el email y la contraseña antes de probar la conexión.")
                    else:
                        with st.spinner("Probando conexión SMTP..."):
                            ok, msg = email_service.test_smtp_connection(new_smtp)
                        if ok:
                            st.success(f"✅ Conexión exitosa: {msg}")
                        else:
                            st.error(f"❌ Error de conexión: {msg}")

    st.markdown("---")

    # ─── SECCIÓN 2: Emails de deportistas ────────────────────────────────────
    with st.expander("👥 Emails de los Deportistas", expanded=False):
        st.caption("Puedes editar el email de cada deportista también desde la barra lateral (⚙️ Editar deportista).")
        emails_changed = False
        for ath in athletes_list:
            col_n, col_e = st.columns([1, 2])
            col_n.write(f"**{ath.get('name','?')}**")
            new_email_val = col_e.text_input(
                label=f"email_{ath.get('athlete_id')}",
                value=ath.get("email", ""),
                placeholder="email@dominio.com",
                label_visibility="collapsed",
                key=f"email_input_{ath.get('athlete_id')}"
            )
            if new_email_val != ath.get("email", ""):
                ath["email"] = new_email_val.strip()
                emails_changed = True

        if emails_changed:
            save_config(config_data)
            st.success("✅ Emails actualizados.")

        athletes_with_email = [a for a in athletes_list if a.get("email", "").strip() and "@" in a.get("email", "")]
        athletes_no_email = [a for a in athletes_list if not a.get("email", "").strip() or "@" not in a.get("email", "")]

        if athletes_no_email:
            st.warning(f"⚠️ {len(athletes_no_email)} deportista(s) sin email: {', '.join(a['name'] for a in athletes_no_email)}")
        if athletes_with_email:
            st.success(f"✅ {len(athletes_with_email)} deportista(s) con email configurado: {', '.join(a['name'] for a in athletes_with_email)}")

    st.markdown("---")

    # ─── SECCIÓN 3: Generar y enviar informes ────────────────────────────────
    st.markdown("#### 📨 Generar y Enviar Informe")

    col_ath, col_type = st.columns(2)
    with col_ath:
        target_options = ["Todos los deportistas"] + [a["name"] for a in athletes_list]
        selected_target = st.selectbox("¿A quién?", target_options, key="email_target_sel")
    with col_type:
        report_type = st.selectbox("Tipo de informe", ["Semanal (última semana)", "Mensual (mes en curso)"], key="email_type_sel")

    # Calcular fechas
    from datetime import datetime, timedelta
    today = datetime.now()
    days_since_monday = today.weekday()
    week_start = (today - timedelta(days=days_since_monday)).strftime("%Y-%m-%d")
    week_end = today.strftime("%Y-%m-%d")
    month_start = today.replace(day=1).strftime("%Y-%m-%d")
    month_end = today.strftime("%Y-%m-%d")

    mode = "weekly" if "Semanal" in report_type else "monthly"
    start_d = week_start if mode == "weekly" else month_start
    end_d = week_end if mode == "monthly" else week_end
    if mode == "monthly":
        end_d = month_end

    coach_api_key = config_data.get("coach_api_key", "")
    coach_ath_id = str(config_data.get("coach_athlete_id", "")).strip()

    # Determinar deportistas objetivo
    if selected_target == "Todos los deportistas":
        targets = athletes_list
    else:
        targets = [a for a in athletes_list if a["name"] == selected_target]

    # ── Previsualización HTML ──────────────────────────────────────
    with st.expander("👁️ Previsualizar Informe HTML", expanded=False):
        preview_ath = targets[0] if targets else None
        if preview_ath and coach_api_key:
            if st.button("🔄 Generar Vista Previa", key="btn_preview"):
                ath_id = str(preview_ath["athlete_id"]).strip()
                is_coach = (ath_id == coach_ath_id or ath_id == "0")
                with st.spinner(f"Generando informe para {preview_ath['name']}..."):
                    try:
                        match_data = report_generator.match_workouts_in_period(
                            ath_id, coach_api_key, start_d, end_d, is_coach=is_coach)
                        wellness_data = report_generator.get_wellness_summary(
                            ath_id, coach_api_key, start_d, end_d, is_coach=is_coach)
                        upcoming_races = report_generator.get_upcoming_races(
                            ath_id, coach_api_key, is_coach=is_coach)
                        recs = report_generator.generate_report_recommendations(
                            match_data, wellness_data, report_type=mode, athlete_name=preview_ath["name"])
                        html_preview = report_generator.build_report_html(
                            athlete_name=preview_ath["name"],
                            report_type=mode,
                            start_date=start_d,
                            end_date=end_d,
                            match_data=match_data,
                            wellness_data=wellness_data,
                            upcoming_races=upcoming_races,
                            recommendations=recs,
                            coach_name=smtp_config.get("coach_name", "Juanan Coy - Entrenador")
                        )
                        st.session_state["email_preview_html"] = html_preview
                        st.session_state["email_preview_name"] = preview_ath["name"]
                        st.success(f"Vista previa generada ({len(html_preview):,} bytes)")
                    except Exception as ex:
                        st.error(f"Error generando vista previa: {ex}")

            if st.session_state.get("email_preview_html"):
                st.caption(f"Vista previa: {st.session_state.get('email_preview_name', '')}")
                components.html(st.session_state["email_preview_html"], height=700, scrolling=True)
        else:
            st.info("Selecciona un deportista y asegúrate de tener la API Key configurada.")

    st.markdown("")

    # ── Botones de acción ──────────────────────────────────────────
    col_dry, col_send = st.columns(2)

    with col_dry:
        if st.button("🧪 Simulación (Dry-Run) — Sin enviar", use_container_width=True, key="btn_dry"):
            if not coach_api_key:
                st.error("Configura la API Key del entrenador en la barra lateral.")
            else:
                results = []
                progress = st.progress(0, text="Procesando deportistas...")
                for i, ath in enumerate(targets):
                    ath_id = str(ath["athlete_id"]).strip()
                    is_coach = (ath_id == coach_ath_id or ath_id == "0")
                    try:
                        match_data = report_generator.match_workouts_in_period(
                            ath_id, coach_api_key, start_d, end_d, is_coach=is_coach)
                        wellness_data = report_generator.get_wellness_summary(
                            ath_id, coach_api_key, start_d, end_d, is_coach=is_coach)
                        upcoming_races = report_generator.get_upcoming_races(
                            ath_id, coach_api_key, is_coach=is_coach)
                        recs = report_generator.generate_report_recommendations(
                            match_data, wellness_data, report_type=mode, athlete_name=ath["name"])
                        html_r = report_generator.build_report_html(
                            athlete_name=ath["name"],
                            report_type=mode,
                            start_date=start_d,
                            end_date=end_d,
                            match_data=match_data,
                            wellness_data=wellness_data,
                            upcoming_races=upcoming_races,
                            recommendations=recs,
                            coach_name=smtp_config.get("coach_name", "Juanan Coy - Entrenador")
                        )
                        email_val = ath.get("email", "")
                        results.append({
                            "name": ath["name"],
                            "email": email_val or "⚠️ Sin email",
                            "cumplimiento": f"{match_data.get('compliance_pct', 0)}%",
                            "hechos": match_data.get('completed_count', 0),
                            "saltados": match_data.get('skipped_count', 0),
                            "horas": match_data.get('total_hours', 0),
                            "TSS": match_data.get('total_tss', 0),
                            "html_size": f"{len(html_r):,} bytes",
                            "estado": "✅ Listo" if (email_val and "@" in email_val) else "⚠️ Sin email"
                        })
                    except Exception as ex:
                        results.append({"name": ath["name"], "email": "ERROR", "estado": f"❌ {ex}",
                            "cumplimiento": "-", "hechos": 0, "saltados": 0, "horas": 0, "TSS": 0, "html_size": "-"})
                    progress.progress((i + 1) / len(targets), text=f"Procesado: {ath['name']}")

                progress.empty()
                st.success("✅ Simulación completada. Revisa los resultados:")
                df_results = pd.DataFrame(results)[["name", "email", "cumplimiento", "hechos", "saltados", "horas", "TSS", "html_size", "estado"]]
                df_results.columns = ["Deportista", "Email", "Cumplimiento", "Hechos", "Saltados", "Horas", "TSS", "Tamaño HTML", "Estado"]
                st.dataframe(df_results, use_container_width=True)

    with col_send:
        send_disabled = not smtp_config.get("user") or not smtp_config.get("password")
        if st.button("🚀 Enviar Informes Ahora", type="primary", use_container_width=True,
                     disabled=send_disabled, key="btn_send",
                     help="Configura el servidor SMTP antes de enviar." if send_disabled else ""):
            athletes_with_mail = [a for a in targets if a.get("email", "").strip() and "@" in a.get("email", "")]
            athletes_no_mail = [a for a in targets if not a.get("email", "").strip() or "@" not in a.get("email", "")]

            if athletes_no_mail:
                st.warning(f"⚠️ Se omitirán {len(athletes_no_mail)} deportista(s) sin email: {', '.join(a['name'] for a in athletes_no_mail)}")
            if not athletes_with_mail:
                st.error("No hay deportistas con email configurado. Añade los emails en la sección anterior.")
            else:
                sent_ok = []
                sent_fail = []
                progress2 = st.progress(0, text="Enviando informes...")
                for i, ath in enumerate(athletes_with_mail):
                    ath_id = str(ath["athlete_id"]).strip()
                    is_coach = (ath_id == coach_ath_id or ath_id == "0")
                    try:
                        match_data = report_generator.match_workouts_in_period(
                            ath_id, coach_api_key, start_d, end_d, is_coach=is_coach)
                        wellness_data = report_generator.get_wellness_summary(
                            ath_id, coach_api_key, start_d, end_d, is_coach=is_coach)
                        upcoming_races = report_generator.get_upcoming_races(
                            ath_id, coach_api_key, is_coach=is_coach)
                        recs = report_generator.generate_report_recommendations(
                            match_data, wellness_data, report_type=mode, athlete_name=ath["name"])
                        html_r = report_generator.build_report_html(
                            athlete_name=ath["name"],
                            report_type=mode,
                            start_date=start_d,
                            end_date=end_d,
                            match_data=match_data,
                            wellness_data=wellness_data,
                            upcoming_races=upcoming_races,
                            recommendations=recs,
                            coach_name=smtp_config.get("coach_name", "Juanan Coy - Entrenador")
                        )

                        if mode == "weekly":
                            subject = f"📊 Tu Resumen Semanal ({start_d} al {end_d}) — {ath['name']}"
                        else:
                            subject = f"🏆 Tu Balance Mensual ({today.strftime('%B %Y')}) — {ath['name']}"

                        bcc = smtp_config.get("user") if smtp_config.get("bcc_coach", True) else None
                        ok, msg = email_service.send_email(
                            to_email=ath["email"],
                            subject=subject,
                            html_content=html_r,
                            smtp_config=smtp_config,
                            bcc_email=bcc
                        )
                        if ok:
                            sent_ok.append(ath["name"])
                        else:
                            sent_fail.append(f"{ath['name']} ({msg})")
                    except Exception as ex:
                        sent_fail.append(f"{ath['name']} (Error: {ex})")
                    progress2.progress((i + 1) / len(athletes_with_mail), text=f"Enviando a: {ath['name']}")

                progress2.empty()
                if sent_ok:
                    st.success(f"✅ Informes enviados con éxito a: {', '.join(sent_ok)}")
                if sent_fail:
                    st.error(f"❌ Errores en: {', '.join(sent_fail)}")

    st.markdown("---")

    # ─── SECCIÓN 4: Automatización con Task Scheduler ─────────────────────────
    with st.expander("🤖 Automatización — Programar Envíos (Windows Task Scheduler)", expanded=False):
        st.markdown("""
#### Envío automático cada domingo a las 21:00 (Informe Semanal)

Abre **PowerShell como administrador** y ejecuta:

```powershell
$action = New-ScheduledTaskAction -Execute 'python' `
    -Argument 'send_reports.py --mode weekly --force' `
    -WorkingDirectory 'D:\\Users\\juan_\\Documents\\Juanan\\Programación\\Carga de temporada intervals.uci'
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 21:00
Register-ScheduledTask -TaskName 'IntervalsUCI_InformeSemanal' `
    -Action $action -Trigger $trigger -RunLevel Highest -Force
```

#### Envío automático el último día de mes a las 21:00 (Informe Mensual)

```powershell
$action2 = New-ScheduledTaskAction -Execute 'python' `
    -Argument 'send_reports.py --mode monthly --force' `
    -WorkingDirectory 'D:\\Users\\juan_\\Documents\\Juanan\\Programación\\Carga de temporada intervals.uci'
$trigger2 = New-ScheduledTaskTrigger -Daily -At 21:00
Register-ScheduledTask -TaskName 'IntervalsUCI_InformeMensual' `
    -Action $action2 -Trigger $trigger2 -RunLevel Highest -Force
```

> ⚠️ **Nota para el informe mensual:** La tarea se ejecuta cada día a las 21:00, pero el script comprueba automáticamente si es el último día del mes antes de enviar. Si quieres, también puedes usar el archivo **`EnviarInformesMes.bat`** o **`EnviarInformesSemana.bat`** haciendo doble clic manualmente.

#### Verificar tareas programadas
```powershell
Get-ScheduledTask | Where-Object {$_.TaskName -like 'IntervalsUCI*'}
```
        """)
        st.info("💡 **Tip Gmail:** Para usar Gmail, activa la verificación en dos pasos y genera una **'Contraseña de Aplicación'** en tu cuenta de Google (Seguridad → Contraseñas de aplicación). Usa esa contraseña en el campo SMTP, no tu contraseña normal.")


def render_excel_uploader(active_athlete, config_data, default_hour):
    """
    Renderiza la sección completa de carga de entrenamientos estructurados desde Excel.
    """
    st.markdown("### 📤 Carga de Entrenamientos a Intervals.icu desde Excel")
    
    uploaded_file = st.file_uploader("Sube tu archivo Excel (.xlsx) con los entrenamientos estructurados", type=["xlsx"])

    # Inicializar variables de estado
    if "df" not in st.session_state:
        st.session_state.df = pd.DataFrame()
    if "processing_logs" not in st.session_state:
        st.session_state.processing_logs = []

    if uploaded_file:
        try:
            excel_file = pd.ExcelFile(uploaded_file)
            sheet_names = excel_file.sheet_names
        except Exception as e:
            st.error(f"Error al abrir el Excel: {e}")
            sheet_names = []
            
        if sheet_names:
            st.markdown("#### 📊 Configuración de Importación de Excel")
            
            col_s1, col_s2 = st.columns([1, 2])
            with col_s1:
                selected_sheet = st.selectbox("Selecciona la hoja de entrenamientos", sheet_names, index=0)
                
            try:
                df_preview = pd.read_excel(uploaded_file, sheet_name=selected_sheet, nrows=5)
                columns = list(df_preview.columns)
            except Exception as e:
                st.error(f"Error leyendo columnas: {e}")
                columns = []
                
            if columns:
                def autodetect(cols, keywords):
                    for kw in keywords:
                        for col in cols:
                            if kw in str(col).lower():
                                return col
                    return None
                    
                def_date = autodetect(columns, ["día", "dia", "fecha", "date"])
                
                def_workout1 = autodetect(columns, ["intervals 1", "intervals1", "entrenamiento intervals 1", "entrenamiento principal", "entrenamiento", "workout", "intervals"])
                def_sport1 = autodetect(columns, ["deporte 1", "deporte1", "deporte", "tipo", "sporttype", "sport"])
                def_name1 = autodetect(columns, ["nombre del entreno 1", "nombre 1", "nombre1", "nombre del entreno", "nombre", "título", "titulo", "name"])
                
                def_workout2 = autodetect(columns, ["intervals 2", "intervals2", "entrenamiento intervals 2"])
                def_sport2 = autodetect(columns, ["deporte 2", "deporte2"])
                def_name2 = autodetect(columns, ["nombre del entreno 2", "nombre 2", "nombre2"])
                
                def_workout3 = autodetect(columns, ["intervals 3", "intervals3", "entrenamiento intervals 3"])
                def_sport3 = autodetect(columns, ["deporte 3", "deporte3"])
                def_name3 = autodetect(columns, ["nombre del entreno 3", "nombre 3", "nombre3"])

                def_workout4 = autodetect(columns, ["intervals 4", "intervals4", "entrenamiento intervals 4"])
                def_sport4 = autodetect(columns, ["deporte 4", "deporte4"])
                def_name4 = autodetect(columns, ["nombre del entreno 4", "nombre 4", "nombre4"])

                def_cat = autodetect(columns, ["categoría", "categoria", "category"])
                def_explanation = autodetect(columns, ["explicación", "explicacion", "contexto", "explicacion semana", "explicación semana"])
                
                # Autodetectar cuántas sesiones tiene el Excel
                num_sessions = 1
                if def_sport2 or def_workout2:
                    num_sessions = max(num_sessions, 2)
                if def_sport3 or def_workout3:
                    num_sessions = max(num_sessions, 3)
                if def_sport4 or def_workout4:
                    num_sessions = max(num_sessions, 4)
                
                st.write("Indica qué columna del Excel corresponde a cada campo:")
                
                # Sesión 1
                st.markdown("##### 1️⃣ Sesión 1 / Principal")
                col_s1a, col_s1b, col_s1c = st.columns(3)
                with col_s1a:
                    col_date = st.selectbox(
                        "📅 Columna de Fecha (Obligatorio)", 
                        options=columns, 
                        index=columns.index(def_date) if def_date in columns else 0
                    )
                    col_workout1 = st.selectbox(
                        "📝 Entreno 1 / Intervals 1 (Obligatorio)", 
                        options=columns, 
                        index=columns.index(def_workout1) if def_workout1 in columns else 0
                    )
                with col_s1b:
                    col_sport1 = st.selectbox(
                        "🚴 Deporte 1 (Opcional)", 
                        options=["-- Autodetectar por contenido --"] + columns,
                        index=columns.index(def_sport1) + 1 if def_sport1 in columns else 0
                    )
                    col_name1 = st.selectbox(
                        "🏷️ Nombre 1 (Opcional)", 
                        options=["-- Por defecto (Deporte y Fecha) --"] + columns,
                        index=columns.index(def_name1) + 1 if def_name1 in columns else 0
                    )
                with col_s1c:
                    col_explanation = st.selectbox(
                        "ℹ️ Explicación Diaria / Nota (Opcional)",
                        options=["-- No importar explicaciones --"] + columns,
                        index=columns.index(def_explanation) + 1 if def_explanation in columns else 0
                    )
                    col_category = st.selectbox(
                        "📌 Categoría General (Opcional)", 
                        options=["-- Por defecto (WORKOUT) --"] + columns,
                        index=columns.index(def_cat) + 1 if def_cat in columns else 0
                    )
                
                col_workout2 = "-- Sin segundo entrenamiento --"
                col_sport2 = "-- Autodetectar por contenido --"
                col_name2 = "-- Por defecto (Deporte y Fecha) --"
                col_workout3 = "-- Sin tercer entrenamiento --"
                col_sport3 = "-- Autodetectar por contenido --"
                col_name3 = "-- Por defecto (Deporte y Fecha) --"
                col_workout4 = "-- Sin cuarto entrenamiento --"
                col_sport4 = "-- Autodetectar por contenido --"
                col_name4 = "-- Por defecto (Deporte y Fecha) --"
                
                if num_sessions >= 2:
                    st.markdown("##### 2️⃣ Sesión 2")
                    col_s2a, col_s2b, col_s2c = st.columns(3)
                    with col_s2a:
                        col_workout2 = st.selectbox(
                            "📝 Entreno 2 / Intervals 2", 
                            options=["-- Sin segundo entrenamiento --"] + columns, 
                            index=columns.index(def_workout2) + 1 if def_workout2 in columns else 0
                        )
                    with col_s2b:
                        col_sport2 = st.selectbox(
                            "🚴 Deporte 2", 
                            options=["-- Autodetectar por contenido --"] + columns,
                            index=columns.index(def_sport2) + 1 if def_sport2 in columns else 0
                        )
                    with col_s2c:
                        col_name2 = st.selectbox(
                            "🏷️ Nombre 2", 
                            options=["-- Por defecto (Deporte y Fecha) --"] + columns,
                            index=columns.index(def_name2) + 1 if def_name2 in columns else 0
                        )
                
                if num_sessions >= 3:
                    st.markdown("##### 3️⃣ Sesión 3")
                    col_s3a, col_s3b, col_s3c = st.columns(3)
                    with col_s3a:
                        col_workout3 = st.selectbox(
                            "📝 Entreno 3 / Intervals 3", 
                            options=["-- Sin tercer entrenamiento --"] + columns, 
                            index=columns.index(def_workout3) + 1 if def_workout3 in columns else 0
                        )
                    with col_s3b:
                        col_sport3 = st.selectbox(
                            "🚴 Deporte 3", 
                            options=["-- Autodetectar por contenido --"] + columns,
                            index=columns.index(def_sport3) + 1 if def_sport3 in columns else 0
                        )
                    with col_s3c:
                        col_name3 = st.selectbox(
                            "🏷️ Nombre 3", 
                            options=["-- Por defecto (Deporte y Fecha) --"] + columns,
                            index=columns.index(def_name3) + 1 if def_name3 in columns else 0
                        )
                
                if num_sessions >= 4:
                    st.markdown("##### 4️⃣ Sesión 4")
                    col_s4a, col_s4b, col_s4c = st.columns(3)
                    with col_s4a:
                        col_workout4 = st.selectbox(
                            "📝 Entreno 4 / Intervals 4", 
                            options=["-- Sin cuarto entrenamiento --"] + columns, 
                            index=columns.index(def_workout4) + 1 if def_workout4 in columns else 0
                        )
                    with col_s4b:
                        col_sport4 = st.selectbox(
                            "🚴 Deporte 4", 
                            options=["-- Autodetectar por contenido --"] + columns,
                            index=columns.index(def_sport4) + 1 if def_sport4 in columns else 0
                        )
                    with col_s4c:
                        col_name4 = st.selectbox(
                            "🏷️ Nombre 4", 
                            options=["-- Por defecto (Deporte y Fecha) --"] + columns,
                            index=columns.index(def_name4) + 1 if def_name4 in columns else 0
                        )
                
                mapping = {
                    'Día': col_date,
                    'IntervalsText': col_workout1,
                    'SportType': col_sport1 if col_sport1 != "-- Autodetectar por contenido --" else None,
                    'Name': col_name1 if col_name1 != "-- Por defecto (Deporte y Fecha) --" else None,
                    
                    'IntervalsText2': col_workout2 if col_workout2 != "-- Sin segundo entrenamiento --" else None,
                    'SportType2': col_sport2 if col_sport2 != "-- Autodetectar por contenido --" else None,
                    'Name2': col_name2 if col_name2 != "-- Por defecto (Deporte y Fecha) --" else None,
                    
                    'IntervalsText3': col_workout3 if col_workout3 != "-- Sin tercer entrenamiento --" else None,
                    'SportType3': col_sport3 if col_sport3 != "-- Autodetectar por contenido --" else None,
                    'Name3': col_name3 if col_name3 != "-- Por defecto (Deporte y Fecha) --" else None,

                    'IntervalsText4': col_workout4 if col_workout4 != "-- Sin cuarto entrenamiento --" else None,
                    'SportType4': col_sport4 if col_sport4 != "-- Autodetectar por contenido --" else None,
                    'Name4': col_name4 if col_name4 != "-- Por defecto (Deporte y Fecha) --" else None,

                    'Category': col_category if col_category != "-- Por defecto (WORKOUT) --" else None,
                    'ExplicacionSemana': col_explanation if col_explanation != "-- No importar explicaciones --" else None
                }
                
                if st.button("⚙️ Procesar y Cargar Entrenamientos", use_container_width=True):
                    with st.spinner("⏳ Leyendo y formateando Excel..."):
                        df = process_excel(uploaded_file, sheet_name=selected_sheet, column_mapping=mapping)
                        if not df.empty:
                            st.session_state.df = df
                            st.session_state.last_file = uploaded_file.name
                            st.success(f"✅ Se cargaron {len(df)} entrenamientos estructurados correctamente.")
                        else:
                            st.error("Error en la estructura del Excel o fechas inválidas.")

    # Edición y Subida
    if not st.session_state.df.empty:
        st.markdown("---")
        st.markdown("#### 📅 Filtrado y Selección de Días")
        
        st.session_state.df['Mes_Año'] = pd.to_datetime(st.session_state.df['Día']).dt.strftime('%Y-%m')
        meses_disponibles = sorted(st.session_state.df['Mes_Año'].unique().tolist())
        mes_actual = pd.Timestamp.now().strftime('%Y-%m')
        default_idx = meses_disponibles.index(mes_actual) if mes_actual in meses_disponibles else 0
        
        col_f1, col_f2 = st.columns([1, 2])
        with col_f1:
            selected_month = st.selectbox("Mes para planificar", meses_disponibles, index=default_idx)
            
        df_month = st.session_state.df[st.session_state.df['Mes_Año'] == selected_month]
        dias_opciones = sorted(df_month['Día'].unique().tolist())
        
        with col_f2:
            selected_days = st.multiselect("Días a editar/subir:", options=dias_opciones)
            
        if selected_days:
            st.info(f"📍 Tienes {len(selected_days)} días seleccionados abajo.")
            mask = st.session_state.df['Día'].isin(selected_days)
            
            edited_df = st.data_editor(
                st.session_state.df[mask],
                column_config={
                    "Status": st.column_config.SelectboxColumn("Estado", options=["✅ Listo", "✅ Subido"]),
                    "Día": st.column_config.TextColumn("Fecha", disabled=True),
                    "SportType": st.column_config.SelectboxColumn("Deporte", options=["Swim", "Ride", "Run", "WeightTraining", "Workout"]),
                    "Name": st.column_config.TextColumn("Nombre del Entrenamiento"),
                    "Category": st.column_config.SelectboxColumn("Categoría", options=["WORKOUT", "RACE_A", "RACE_B", "RACE_C", "NOTE"]),
                    "IntervalsText": st.column_config.TextColumn("Entrenamiento Intervals (Estructurado)", width="large"),
                    "Mes_Año": None, "Seleccionar": None
                },
                use_container_width=True,
                key="df_editor"
            )
            
            if not edited_df.equals(st.session_state.df[mask]):
                for idx in edited_df.index:
                    st.session_state.df.loc[idx] = edited_df.loc[idx]
                    
            st.subheader("🚀 Subida a Intervals.icu")
            sub_mask = mask & (st.session_state.df['Status'] == '✅ Listo')
            to_upload = st.session_state.df[sub_mask]
            
            if to_upload.empty:
                st.write("No hay entrenamientos pendientes de subir ('✅ Listo') en esta selección.")
            else:
                st.markdown("##### 📝 Vista Previa de Entrenamientos a Subir:")
                resumen_data = to_upload[['Día', 'SportType', 'Category', 'Name']].copy()
                resumen_data = resumen_data.rename(columns={
                    'Día': 'Fecha', 
                    'SportType': 'Deporte', 
                    'Category': 'Categoría', 
                    'Name': 'Nombre'
                })
                st.dataframe(resumen_data, use_container_width=True)
                
                if st.button("🚀 Subir TODOS los seleccionados a Intervals.icu", use_container_width=True):
                    if not active_athlete:
                        st.error("Por favor, selecciona un deportista en la barra lateral.")
                    elif not config_data["coach_api_key"]:
                        st.error("Por favor, introduce tu API Key de Entrenador en la barra lateral.")
                    else:
                        upload_status = st.empty()
                        for idx, row in to_upload.iterrows():
                            upload_status.info(f"Subiendo {row['Día']}...")
                            
                            iso_date = f"{row['Día']}T{default_hour.strftime('%H:%M:%S')}"
                            workout_name = row.get('Name') if pd.notna(row.get('Name')) and str(row.get('Name')).strip() != "" else f"{row['SportType']} - {row['Día']}"
                            
                            payload = {
                                "start_date_local": iso_date,
                                "type": row['SportType'],
                                "category": row.get('Category', 'WORKOUT'),
                                "name": workout_name,
                                "workout_text": sanitize_workout_text(row['IntervalsText'])
                            }
                            
                            coach_athlete_id = str(config_data.get("coach_athlete_id", "")).strip()
                            target_athlete_id = str(active_athlete["athlete_id"]).strip()
                            is_own_account = (target_athlete_id == coach_athlete_id or target_athlete_id == "0")
                            
                            success, msg = upload_to_intervals(
                                athlete_id=active_athlete["athlete_id"],
                                api_key=config_data["coach_api_key"],
                                payload=payload,
                                use_athlete_key=is_own_account
                            )
                            
                            if success:
                                st.session_state.df.at[idx, 'Status'] = '✅ Subido'
                                st.session_state.processing_logs.append(f"{time.strftime('%H:%M:%S')} - {row['Día']} ({row['SportType']}) subido con éxito.")
                            else:
                                st.error(f"Error subiendo el entreno del {row['Día']}: {msg}")
                                
                        upload_status.success("✅ ¡Proceso de subida completado!")
                        time.sleep(1.5)
                        st.rerun()

                for idx, row in to_upload.iterrows():
                    workout_name = row.get('Name') if pd.notna(row.get('Name')) and str(row.get('Name')).strip() != "" else f"{row['SportType']} - {row['Día']}"
                    with st.expander(f"📍 {row['Día']} - {workout_name}", expanded=False):
                        st.write(f"**Deporte:** {row['SportType']} | **Categoría:** {row['Category']}")
                        st.text_area("Entrenamiento estructurado:", value=row['IntervalsText'], height=120, key=f"txt_{idx}", disabled=True)
                        
                        if st.button(f"Subir entreno del {row['Día']} 🚀", key=f"btn_up_{idx}"):
                            if not active_athlete:
                                st.error("Selecciona un deportista en la barra lateral.")
                            elif not config_data["coach_api_key"]:
                                st.error("Introduce tu API Key de Entrenador en la barra lateral.")
                            else:
                                iso_date = f"{row['Día']}T{default_hour.strftime('%H:%M:%S')}"
                                payload = {
                                    "start_date_local": iso_date,
                                    "type": row['SportType'],
                                    "category": row.get('Category', 'WORKOUT'),
                                    "name": workout_name,
                                    "workout_text": sanitize_workout_text(row['IntervalsText'])
                                }
                                
                                coach_athlete_id = str(config_data.get("coach_athlete_id", "")).strip()
                                target_athlete_id = str(active_athlete["athlete_id"]).strip()
                                is_own_account = (target_athlete_id == coach_athlete_id or target_athlete_id == "0")
                                
                                success, msg = upload_to_intervals(
                                    athlete_id=active_athlete["athlete_id"],
                                    api_key=config_data["coach_api_key"],
                                    payload=payload,
                                    use_athlete_key=is_own_account
                                )
                                if success:
                                    st.session_state.df.at[idx, 'Status'] = '✅ Subido'
                                    st.success("¡Subido con éxito!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"Fallo al subir: {msg}")

        else:
            st.info("💡 Por favor, selecciona uno o varios días arriba para empezar a editar y subir.")

        if st.session_state.processing_logs:
            with st.expander("📜 Registro de Actividad Reciente"):
                for log in st.session_state.processing_logs:
                    st.write(log)
                if st.button("Limpiar Registro"):
                    st.session_state.processing_logs = []
                    st.rerun()


# --- CUERPO PRINCIPAL CON PESTAÑAS (TABS) ---
tab_dashboard, tab_uploader, tab_email = st.tabs([
    "📊 Dashboard de Rendimiento",
    "📤 Carga de Entrenamientos (Excel)",
    "📧 Informes y Email"
])

with tab_dashboard:
    if active_athlete:
        dashboard.render_dashboard(
            active_athlete=active_athlete,
            coach_api_key=config_data.get("coach_api_key", ""),
            coach_athlete_id=config_data.get("coach_athlete_id", ""),
            athletes_list=config_data.get("athletes", [])
        )
    else:
        st.info("👈 Por favor, selecciona un deportista en la barra lateral para ver su Dashboard de Rendimiento.")

with tab_uploader:
    render_excel_uploader(active_athlete, config_data, default_hour)

with tab_email:
    render_email_tab(active_athlete, config_data)
