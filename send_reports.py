import argparse
import json
import os
import sys
from datetime import datetime, timedelta
import email_service
import report_generator

ATHLETES_FILE = "athletes.json"
LOG_FILE = "reports_sent.log"

def log_event(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}\n"
    print(line.strip())
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        print(f"Error escribiendo log: {e}")

def load_config():
    if not os.path.exists(ATHLETES_FILE):
        log_event(f"ERROR: No se encontró {ATHLETES_FILE}")
        return None
    try:
        with open(ATHLETES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log_event(f"ERROR leyendo {ATHLETES_FILE}: {e}")
        return None

def run_reports(mode="auto", target_athlete="all", dry_run=False, force=False):
    config = load_config()
    if not config:
        return

    coach_api_key = config.get("coach_api_key", "")
    coach_athlete_id = str(config.get("coach_athlete_id", "")).strip()
    smtp_config = config.get("smtp_config", {})
    athletes = config.get("athletes", [])

    if not coach_api_key:
        log_event("ERROR: No hay 'coach_api_key' configurada en athletes.json")
        return

    today = datetime.now()
    is_sunday = (today.weekday() == 6)
    is_month_end = ((today + timedelta(days=1)).day == 1)

    # Determinar qué informes corresponden
    run_weekly = False
    run_monthly = False

    if mode == "weekly":
        run_weekly = True
    elif mode == "monthly":
        run_monthly = True
    elif mode == "auto":
        if is_sunday or force:
            run_weekly = True
        if is_month_end or force:
            run_monthly = True
        if not run_weekly and not run_monthly:
            log_event(f"Modo auto: Hoy {today.strftime('%Y-%m-%d')} no es domingo ni fin de mes. Usa --force para forzar el envío.")
            return

    # Determinar fechas semanales (último lunes a hoy domingo)
    # Si hoy es domingo, el lunes fue hace 6 días
    days_since_monday = today.weekday()
    week_start = (today - timedelta(days=days_since_monday)).strftime("%Y-%m-%d")
    week_end = today.strftime("%Y-%m-%d")

    # Fechas mensuales (día 1 de este mes hasta hoy)
    month_start = today.replace(day=1).strftime("%Y-%m-%d")
    month_end = today.strftime("%Y-%m-%d")

    log_event(f"Iniciando proceso de informes [Modo: {mode} | Dry-run: {dry_run} | Atletas: {len(athletes)}]")

    for ath in athletes:
        name = ath.get("name", "Deportista")
        ath_id = str(ath.get("athlete_id", "")).strip()
        email = str(ath.get("email", "")).strip()
        is_coach = (ath_id == coach_athlete_id or ath_id == "0")

        if target_athlete != "all":
            if target_athlete.lower() not in name.lower() and target_athlete != ath_id:
                continue

        log_event(f"\n--- Procesando: {name} (ID: {ath_id}) ---")

        if not email or "@" not in email:
            if not dry_run:
                log_event(f"AVISO: {name} no tiene email configurado en athletes.json. Se omite el envío.")
                continue
            else:
                log_event(f"AVISO: {name} no tiene email configurado (simulando generación por --dry-run).")

        # 1. Enviar Informe Semanal
        if run_weekly:
            log_event(f"Generando informe semanal ({week_start} al {week_end}) para {name}...")
            match_data = report_generator.match_workouts_in_period(ath_id, coach_api_key, week_start, week_end, is_coach=is_coach)
            wellness_data = report_generator.get_wellness_summary(ath_id, coach_api_key, week_start, week_end, is_coach=is_coach)
            upcoming_races = report_generator.get_upcoming_races(ath_id, coach_api_key, is_coach=is_coach)
            recs = report_generator.generate_report_recommendations(match_data, wellness_data, report_type="weekly", athlete_name=name)

            html = report_generator.build_report_html(
                athlete_name=name,
                report_type="weekly",
                start_date=week_start,
                end_date=week_end,
                match_data=match_data,
                wellness_data=wellness_data,
                upcoming_races=upcoming_races,
                recommendations=recs,
                coach_name=smtp_config.get("coach_name", "Juanan Coy - Entrenador")
            )

            subject = f"📊 Tu Resumen Semanal de Entrenamientos ({week_start} al {week_end}) - {name}"

            if dry_run:
                log_event(f"[DRY-RUN] Email semanal generado con éxito ({len(html)} bytes). Cumplimiento: {match_data['compliance_pct']}% ({match_data['completed_count']} hechos / {match_data['skipped_count']} saltados). No enviado por --dry-run.")
            else:
                bcc = smtp_config.get("user") if smtp_config.get("bcc_coach", True) else None
                success, msg = email_service.send_email(
                    to_email=email,
                    subject=subject,
                    html_content=html,
                    smtp_config=smtp_config,
                    bcc_email=bcc
                )
                if success:
                    log_event(f"✅ Email semanal enviado con éxito a {email} (Cumplimiento: {match_data['compliance_pct']}%)")
                else:
                    log_event(f"❌ Error enviando email semanal a {email}: {msg}")

        # 2. Enviar Informe Mensual
        if run_monthly:
            log_event(f"Generando balance mensual ({month_start} al {month_end}) para {name}...")
            match_data_m = report_generator.match_workouts_in_period(ath_id, coach_api_key, month_start, month_end, is_coach=is_coach)
            wellness_data_m = report_generator.get_wellness_summary(ath_id, coach_api_key, month_start, month_end, is_coach=is_coach)
            upcoming_races_m = report_generator.get_upcoming_races(ath_id, coach_api_key, is_coach=is_coach)
            recs_m = report_generator.generate_report_recommendations(match_data_m, wellness_data_m, report_type="monthly", athlete_name=name)

            html_m = report_generator.build_report_html(
                athlete_name=name,
                report_type="monthly",
                start_date=month_start,
                end_date=month_end,
                match_data=match_data_m,
                wellness_data=wellness_data_m,
                upcoming_races=upcoming_races_m,
                recommendations=recs_m,
                coach_name=smtp_config.get("coach_name", "Juanan Coy - Entrenador")
            )

            subject_m = f"🏆 Tu Balance Mensual de Entrenamiento ({today.strftime('%B %Y')}) - {name}"

            if dry_run:
                log_event(f"[DRY-RUN] Email mensual generado con éxito ({len(html_m)} bytes). Volumen: {match_data_m['total_hours']}h | TSS: {match_data_m['total_tss']}. No enviado por --dry-run.")
            else:
                bcc = smtp_config.get("user") if smtp_config.get("bcc_coach", True) else None
                success, msg = email_service.send_email(
                    to_email=email,
                    subject=subject_m,
                    html_content=html_m,
                    smtp_config=smtp_config,
                    bcc_email=bcc
                )
                if success:
                    log_event(f"✅ Email mensual enviado con éxito a {email}")
                else:
                    log_event(f"❌ Error enviando email mensual a {email}: {msg}")

    log_event("Proceso de informes finalizado.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Envío automatizado de informes de entrenamiento por email.")
    parser.add_argument("--mode", choices=["auto", "weekly", "monthly"], default="auto", help="Tipo de informe (auto detecta si es domingo o fin de mes)")
    parser.add_argument("--athlete", default="all", help="Nombre o ID del deportista ('all' para todos)")
    parser.add_argument("--dry-run", action="store_true", help="Genera los informes y comprueba datos sin enviar el correo")
    parser.add_argument("--force", action="store_true", help="Fuerza el envío aunque no sea domingo o fin de mes")

    args = parser.parse_args()
    run_reports(mode=args.mode, target_athlete=args.athlete, dry_run=args.dry_run, force=args.force)
