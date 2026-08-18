import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings


def send_reset_email(to_email: str, reset_token: str) -> None:
    reset_link = f"{settings.URL_FRONTEND}/reset-password?token={reset_token}"

    if not settings.SMTP_HOST:
        print(f"[DEV] Email de réinitialisation pour {to_email} : {reset_link}")
        return

    message = MIMEMultipart("alternative")
    message["Subject"] = "Réinitialisation de votre mot de passe"
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to_email

    text_body = (
        "Vous avez demandé la réinitialisation de votre mot de passe.\n\n"
        f"Cliquez sur ce lien pour choisir un nouveau mot de passe : {reset_link}\n\n"
        "Ce lien expire dans 30 minutes. Si vous n'êtes pas à l'origine de cette demande, ignorez cet email."
    )
    html_body = f"""
    <p>Vous avez demandé la réinitialisation de votre mot de passe.</p>
    <p><a href="{reset_link}">Cliquez ici pour choisir un nouveau mot de passe</a></p>
    <p>Ce lien expire dans 30 minutes. Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.</p>
    """

    message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        if settings.SMTP_USE_TLS:
            server.starttls()
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM_EMAIL, to_email, message.as_string())
