from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

import src.api.routers.v1 as v1
from src.config import settings
from src.db.connection import ping_database
from src.logger import setup_logging

log = setup_logging('main')

@asynccontextmanager
async def lifespan(app: FastAPI):

    log.info('Начинается lifespan')
    await ping_database()
    log.info('Стартовый lifespan успешно прошёл')
    yield
    log.info('завершающий lifespan')


app = FastAPI(
    lifespan=lifespan,
)
app.include_router(v1.auth_router)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.APP_HOST,
        port=settings.APP_PORT,
    )
