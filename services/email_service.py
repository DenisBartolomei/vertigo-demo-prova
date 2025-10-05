import os
from typing import Optional

import smtplib
from email.mime.text import MIMEText


SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@vertigo-ai.local")


def send_interview_link(to_email: str, token: str, frontend_base_url: str) -> bool:
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS):
        return False
    url = f"{frontend_base_url.rstrip('/')}/interview/{token}"
    subject = "Il tuo colloquio Vertigo AI"
    body = f"Ciao,\n\nper iniziare il colloquio clicca qui: {url}\n\nGrazie"
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception:
        return False



