from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
from app.database import init_db
from app.api.routes import router
from app.services.scheduler import start_scheduler, stop_scheduler
from app.auth import NeedsLogin
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="HR-Flow", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-secret-change-in-production"),
)

app.include_router(router)


@app.exception_handler(NeedsLogin)
async def needs_login_handler(request: Request, exc: NeedsLogin):
    return RedirectResponse(f"/admin/{exc.tenant_id}/login", status_code=302)
