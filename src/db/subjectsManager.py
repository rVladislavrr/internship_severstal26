import logging

from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import BaseManager
from src.schemes import subjects
from src.models import SubjectsORM
from src.utils.filters_db import build_filters

logger = logging.getLogger('Бд')

class SubjectsManager(BaseManager[subjects.CreateSubjects, subjects.ReadSubjects, subjects.UpdateSubjects,
                                  SubjectsORM]):
    model = SubjectsORM
    create_schema = subjects.CreateSubjects
    read_schema = subjects.ReadSubjects
    update_schema = subjects.UpdateSubjects

    async def get_with_filters(
            self,
            session: AsyncSession,
            request_id: str,
            **filters
    ) -> list[read_schema]:

        logger.debug(f'{request_id} | Начинаем получение Subject с фильтрами')

        try:
            logger.debug(f'{request_id} | Создание фильтров')
            filters = build_filters(
                self.model,
                **filters
            )
            logger.debug(f'{request_id} | Фильтры успешно созданы')
        except Exception as e:
            logger.error(f'{request_id} | Ошибка при создании фильтров', exc_info=e)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Filters create failed')

        try:
            logger.debug(f'{request_id} | Выполнение запроса к бд')

            query = select(self.model)
            if filters:
                query = query.where(and_(*filters))

            result = await session.execute(query)
            result = result.scalars().all()

            if result is None:
                logger.debug(f'{request_id} | Subjects не было найдено по таким фильтрам')
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Subjects not found')

            logger.debug(f'{request_id} | Subject успешно получены с фильтрами')

        except HTTPException:
            raise

        except (OperationalError, InterfaceError) as e:
            logger.critical(
                f"{request_id} | База данных недоступна {self.model.__name__}: {e}",
                exc_info=True,
            )
            raise ConnectionError(f"{request_id} | База данных недоступна: {e}") from e

        except Exception as e:
            logger.error(
                f"{request_id} |Ошибка при получении {self.model.__name__}: {e}",
                exc_info=True,
            )
            raise

        return [self.read_schema.model_validate(entity, from_attributes=True)
                for entity in result]


subjects_manager = SubjectsManager()
