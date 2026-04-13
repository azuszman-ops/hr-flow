import hashlib
import os
import base64
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
