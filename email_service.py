import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

def test_smtp_connection(smtp_config):
    """
    Prueba la conexión y autenticación con el servidor SMTP configurado.
    """
    server_host = str(smtp_config.get("server", "smtp.gmail.com")).strip()
    server_port = int(smtp_config.get("port", 587))
    user = str(smtp_config.get("user", "")).strip()
    password = str(smtp_config.get("password", "")).strip()

    if not user or not password:
        return False, "Usuario o contraseña de correo no configurados."

    try:
        if server_port == 465:
            server = smtplib.SMTP_SSL(server_host, server_port, timeout=12)
        else:
            server = smtplib.SMTP(server_host, server_port, timeout=12)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(user, password)
        server.quit()
        return True, "¡Conexión y autenticación SMTP exitosa!"
    except smtplib.SMTPAuthenticationError as e:
        msg = f"Fallo de autenticación: {e}."
        if "gmail" in server_host.lower():
            msg += "\n💡 En Gmail debes usar una 'Contraseña de Aplicación' de 16 letras (no tu contraseña normal). Ve a tu cuenta de Google > Seguridad > Contraseñas de aplicaciones."
        return False, msg
    except Exception as e:
        return False, f"Error de conexión con {server_host}:{server_port} -> {str(e)}"

def send_email(to_email, subject, html_content, text_content=None, smtp_config=None, bcc_email=None):
    """
    Envía un correo electrónico en formato HTML enriquecido (con fallback en texto plano).
    """
    if not smtp_config:
        return False, "Configuración SMTP no especificada."

    to_email = str(to_email).strip()
    if not to_email or "@" not in to_email:
        return False, f"Dirección de correo de destino no válida: '{to_email}'"

    server_host = str(smtp_config.get("server", "smtp.gmail.com")).strip()
    server_port = int(smtp_config.get("port", 587))
    user = str(smtp_config.get("user", "")).strip()
    password = str(smtp_config.get("password", "")).strip()
    coach_name = str(smtp_config.get("coach_name", "Entrenador")).strip()

    if not user or not password:
        return False, "Credenciales de correo (usuario o contraseña) incompletas."

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{coach_name} <{user}>"
    msg["To"] = to_email

    recipients = [to_email]

    # Copia oculta si está activada
    if bcc_email and str(bcc_email).strip() and "@" in str(bcc_email):
        bcc_clean = str(bcc_email).strip()
        if bcc_clean.lower() != to_email.lower():
            recipients.append(bcc_clean)

    # Texto alternativo básico
    if not text_content:
        text_content = "Por favor, visualiza este mensaje con un cliente de correo que soporte formato HTML para ver tu informe completo."

    part1 = MIMEText(text_content, "plain", "utf-8")
    part2 = MIMEText(html_content, "html", "utf-8")
    msg.attach(part1)
    msg.attach(part2)

    try:
        if server_port == 465:
            server = smtplib.SMTP_SSL(server_host, server_port, timeout=15)
        else:
            server = smtplib.SMTP(server_host, server_port, timeout=15)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(user, password)
        server.sendmail(user, recipients, msg.as_string())
        server.quit()
        return True, f"Correo enviado correctamente a {to_email}"
    except smtplib.SMTPAuthenticationError as e:
        err = f"Fallo de autenticación: {e}."
        if "gmail" in server_host.lower():
            err += " En Gmail, crea una contraseña de aplicación en myaccount.google.com/apppasswords."
        return False, err
    except Exception as e:
        return False, f"Fallo al enviar correo: {str(e)}"
