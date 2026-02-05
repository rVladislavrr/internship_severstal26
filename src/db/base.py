from typing import Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.connection import async_session_maker
from src.logger import setup_logging
from src.models import Base

TCreate = TypeVar("TCreate", bound=BaseModel)
TRead = TypeVar("TRead", bound=BaseModel)
TUpdate = TypeVar("TUpdate", bound=BaseModel)
TModel = TypeVar("TModel", bound=Base)

database_logger = setup_logging("Бд")

class BaseManager(Generic[TCreate, TRead, TUpdate, TModel]):

    create_schema: type[TCreate]
    read_schema: type[TRead]
    update_schema: type[TUpdate]
    model: type[TModel]

    async def __create_entity(self, data: dict, session: AsyncSession) -> TModel:
        instance = self.model(**data)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance

    async def create(self, create_data: TCreate, session: AsyncSession | None = None) -> TRead:
        database_logger.debug(f"Начало создания {self.model.__name__}")

        data = create_data.model_dump(exclude_unset=True)

        try:
            if session is None:

                async with async_session_maker() as session:
                    entity = await self.__create_entity(data, session)

            else:
                entity = await self.__create_entity(data, session)

            await session.commit()

            database_logger.debug(f"Успешно создан {self.model.__name__}: {entity}")

            return self.read_schema.model_validate(entity, from_attributes=True)

        except OperationalError as e:
            database_logger.critical(
                f"База данных недоступна {self.model.__name__}: {e}",
                exc_info=True,
            )
            raise ConnectionError(f"База данных недоступна: {e}") from e

        except SQLAlchemyError as e:
            database_logger.error(
                f"Ошибка БД при создании {self.model.__name__}: {data}, Ошибка: {e}",
                exc_info=True,
            )
            raise

        except Exception as e:
            database_logger.error(
                f"Ошибка при создании {self.model.__name__}: {e}",
                exc_info=True,
            )
            raise

    @property
    def __name__(self):
        return self.__class__.__name__

