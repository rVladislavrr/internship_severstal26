import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Path
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.db.subjectsManager import subjects_manager
from src.logger import setup_logging
from src.schemes import subjects
from src.db.connection import get_async_session

router = APIRouter(tags=["subjects"])

router_logger = logging.getLogger('Роутер Subjects')


def get_request_id(request: Request) -> str:
    try:
        return str(request.state.request_id)
    except AttributeError:
        router_logger.warning('request_id не найден в request.state')
        return ''


@router.post('/subjects',
             response_model=subjects.ReadSubjects,
             status_code=status.HTTP_201_CREATED,
             summary="Create subject",
             responses={
                 201: {"description": "Subject created successfully"},
                 500: {"description": "Database connection error | Error in object creation"}
             }
             )
async def create_subjects(subject_data: subjects.CreateSubjects,
                          request_id: str = Depends(get_request_id),
                          session: AsyncSession = Depends(get_async_session)):
    router_logger.info(f'{request_id} | Создание Subject')

    try:

        subject_read: subjects.ReadSubjects = await subjects_manager.create(subject_data,
                                                                            session,
                                                                            request_id)

        router_logger.info(f"{request_id} | Успешное создание Subject: id={subject_read.id}")
        return subject_read

    except ConnectionError:
        router_logger.critical(f'{request_id} | База данных не доступна')

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Database connection error',
        )
    except Exception:
        router_logger.error(f'{request_id} | Ошибка в создании')

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Error in object creation',
        )


@router.delete('/subjects/{subject_id}',
               response_model=subjects.ReadSubjects,
               status_code=status.HTTP_200_OK,
               summary="Delete subject",
               responses={
                   200: {"description": "Subject delete successfully"},
                   404: {"description": "Subject not found"},
                   409: {"description": "Subject already deleted"},
                   500: {"description": "Database connection error | Error in object delete"}
               }
               )
async def delete_subject(subject_id: int = Path(..., ge=0, description='Айди удаляемого объекта', ),
                         request_id: str = Depends(get_request_id),
                         session: AsyncSession = Depends(get_async_session)):
    router_logger.info(f'{request_id} | Удаление Subject, id={subject_id}')

    try:

        subject_read: subjects.ReadSubjects = await subjects_manager.delete(subject_id,
                                                                            session,
                                                                            request_id)

        router_logger.info(f"{request_id} | Успешное удаление Subject: id={subject_read.id}")
        return subject_read
    except HTTPException as e:
        router_logger.info(f'{request_id} |' + e.detail)
        raise
    except ConnectionError:
        router_logger.critical(f'{request_id} | База данных не доступна')

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Database connection error',
        )
    except Exception:
        router_logger.error(f'{request_id} | Ошибка в удалении')

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Error in object creation',
        )
