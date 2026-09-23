import asyncio
from fastapi import FastAPI

from ..api import router

from .config import settings

from ..db.database import engine
from ..db.model import Base

from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
app.include_router(router)