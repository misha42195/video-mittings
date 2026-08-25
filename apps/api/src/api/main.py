from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth.router import router as auth_router
from api.config import get_settings
from api.database import Base, engine
from api.meeting_files.models import MeetingFile  # noqa: F401 — ensure table is registered
from api.routers.meeting_files import router as meeting_files_router
from api.routers.meetings import router as meetings_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    Path(get_settings().storage_root).mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(meetings_router)
app.include_router(meeting_files_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
