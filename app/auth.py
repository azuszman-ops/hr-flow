import hashlib
import os
import base64
import smtplib
from email.mime.text import MIMEText
from itsdangerous import URLSafeTimedSerializer, BadData
from fastapi import Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db


class NeedsLogin(Exception):
    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return base64.b64encode(salt + key).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        data = base64.b64decode(stored.encode())
        salt, stored_key = data[:16], data[16:]
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return key == stored_key
    except Exception:
        return False


def generate_reset_token(tenant_id: int) -> str:
    s = URLSafeTimedSerializer(os.getenv("SECRET_KEY", "dev-secret-change-in-production"))
    return s.dumps(tenant_id, salt="password-reset")


def verify_reset_token(token: str, max_age: int = 3600) -> int | None:
    s = URLSafeTimedSerializer(os.getenv("SECRET_KEY", "dev-secret-change-in-production"))
    try:
        return s.loads(token, salt="password-reset", max_age=max_age)
    except BadData:
        return None


def send_reset_email(to_email: str, reset_url: str, tenant_name: str) -> bool:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    if not smtp_host or not smtp_user:
        print(f"[EMAIL] SMTP not configured. Reset URL: {reset_url}")
        return False

    body = (
        f"Cześć,\n\n"
        f"Otrzymaliśmy prośbę o reset hasła do panelu HR-Flow ({tenant_name}).\n\n"
        f"Kliknij link aby ustawić nowe hasło (ważny 1 godzinę):\n{reset_url}\n\n"
        f"Jeśli to nie Ty, zignoruj tę wiadomość.\n\nHR-Flow"
    )
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"Reset hasła — {tenant_name}"
    msg["From"] = smtp_from
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, [to_email], msg.as_string())
        print(f"[EMAIL] Reset sent to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL] Error: {e}")
        return False


async def get_authed_tenant(
    request: Request,
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
):
    from app.models import Tenant
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(404)
    if tenant.login_password_hash and not request.session.get(f"auth_{tenant_id}"):
        raise NeedsLogin(tenant_id)
    return tenant
