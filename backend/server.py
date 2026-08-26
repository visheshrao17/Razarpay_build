from dotenv import load_dotenv
load_dotenv()

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import engine, Base
from auth import router as auth_router, seed_users
from routers.runs import router as runs_router
from routers.exceptions import router as exceptions_router
from routers.misc import router as misc_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("settlesense")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_users()
    logger.info("SettleSense backend ready (synthetic mode default)")
    yield


app = FastAPI(title="SettleSense API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(runs_router)
app.include_router(exceptions_router)
app.include_router(misc_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={
        "error": {"code": "INTERNAL_ERROR", "message": str(exc)[:300]}})
