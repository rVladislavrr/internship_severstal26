import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
from starlette.middleware.cors import CORSMiddleware

import src.api.routers.v1 as v1
from src.config import settings
from src.logger import setup_logging
from src.middlewares.loggingMiddleware import LoggingMiddleware
from src.utils.check_db import ping_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    log = logging.getLogger(__name__)

    log.info('Начинается lifespan')
    await ping_database()
    log.info('Стартовый lifespan успешно прошёл')
    yield
    log.info('завершающий lifespan')

if __name__ == "__main__":
    app = FastAPI(
        lifespan=lifespan,
    )

    app.include_router(v1.subjects_router, prefix='/api')

    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(LoggingMiddleware)
    uvicorn.run(
        app,
        host=settings.APP_HOST,
        port=settings.APP_PORT,
    )
