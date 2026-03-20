from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.database import init_db
from app.api.routes import router
from app.services.scheduler import start_scheduler, stop_scheduler
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="HR-Flow", lifespan=lifespan)
app.include_router(router)
