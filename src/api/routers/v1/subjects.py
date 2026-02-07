import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Path, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.db.subjectsManager import subjects_manager
from src.schemes import subjects
from src.db.connection import get_async_session
from src.service.redisManager import redis_manager
from src.utils.filters_db import serialize_filters
from src.utils.key_redis import create_key_filters

router = APIRouter(tags=["subjects"])

router_logger = logging.getLogger('Роутер Subjects')


def get_request_id(request: Request) -> str:
    try:
        return str(request.state.request_id)
    except AttributeError:
        router_logger.warning('request_id не найден в request.state')
        return ''


def get_filter_query(
        id_min: int | None = Query(None, ge=0, le=2147483647, ),
        id_max: int | None = Query(None, gt=0, le=2147483647, ),
        weight_min: int | None = Query(None, gt=0, le=1000000, ),
        weight_max: int | None = Query(None, gt=0, le=1000000, ),
        length_min: int | None = Query(None, gt=0, le=100000, ),
        length_max: int | None = Query(None, gt=0, le=100000, ),
        is_active: bool | None = Query(None),
        created_after: date | None = Query(None, examples=['2026-12-07', '2026-12-03']),
        created_before: date | None = Query(None, examples=['2026-12-07', '2026-12-03']),
        deleted_after: date | None = Query(None, examples=['2026-12-08', '2026-12-04']),
        deleted_before: date | None = Query(None, examples=['2026-12-09', '2026-12-05']),
):
    return serialize_filters(locals())


@router.post('/subjects',
             response_model=subjects.ReadSubjects,
             status_code=status.HTTP_201_CREATED,
             summary="Create subject",
             responses={
                 201: {"description": "Subject created successfully",
                       "model": subjects.ReadSubjects},
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
        await redis_manager.delete_subject_with_filters(request_id)
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
                   200: {"description": "Subject delete successfully",
                         "model": subjects.ReadSubjects},
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
        await redis_manager.delete_subject_with_filters(request_id)
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
            detail='Error delete subject',
        )


@router.get('/subjects',
            response_model=list[subjects.ReadSubjects],
            status_code=status.HTTP_200_OK,
            summary="Get subjects",
            responses={
                200: {"description": "Subjects get successfully",
                      "model": list[subjects.ReadSubjects]},
                404: {"description": "Subjects not found"},
                500: {"description": "Database connection error | Error in object delete"}
            }
            )
async def get_with_filters(
        filters: dict = Depends(get_filter_query),
        request_id: str = Depends(get_request_id),
        session: AsyncSession = Depends(get_async_session),

):
    router_logger.info(f"{request_id} | Получение Subjects")
    key = create_key_filters(filters)

    result = await redis_manager.get_subject_with_filters(key, request_id)

    if result:
        return [subjects.ReadSubjects.model_validate(res, from_attributes=True) for res in result]

    try:
        result = await subjects_manager.get_with_filters(session, request_id, **filters)
        router_logger.info(f"{request_id} | Успешное получение Subjects")

        if result:
            await redis_manager.set_subject_with_filters(key, result, request_id)

        return result

    except HTTPException as e:
        router_logger.info(f'{request_id} |' + e.detail)
        raise

    except ConnectionError:
        router_logger.critical(f'{request_id} | База данных не доступна')

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Database connection error',
        )

    except Exception as e:
        router_logger.error(f'{request_id} | Ошибка в получении', exc_info=e)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Error select subject',
        )


@router.get('/subjects/statistics')
async def get_statistics(
        start_date: datetime | None = Query(None),
        end_date: datetime | None = Query(None),
        request_id: str = Depends(get_request_id),
        session: AsyncSession = Depends(get_async_session)):
    router_logger.info(f"{request_id} | Получение статистики по Subjects")
    try:
        return await subjects_manager.get_subjects_statistics(
            start_date=start_date,
            end_date=end_date,
            request_id=request_id,
            session=session,
        )

    except HTTPException as e:
        router_logger.info(f'{request_id} |' + e.detail)
        raise

    except ConnectionError:
        router_logger.critical(f'{request_id} | База данных не доступна')

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Database connection error',
        )

    except Exception as e:
        router_logger.error(f'{request_id} | Ошибка в получении статистики', exc_info=e)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Error select subject',
        )
@router.get('/subjects/{subject_id}',
            response_model=subjects.ReadSubjects,
            status_code=status.HTTP_200_OK,
            )
async def get_subject(
        subject_id: int,
        request_id: str = Depends(get_request_id),
        session: AsyncSession = Depends(get_async_session),
):
    router_logger.info(f'{request_id} | Получение Subject, id={subject_id}')
    try:
        subject_read: subjects.ReadSubjects = await subjects_manager.get(subject_id,session , request_id)

        router_logger.info(f'{request_id} | Успешно получен Subject, id={subject_id}')
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
        router_logger.error(f'{request_id} | Ошибка в получении')

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Error find subject',
        )
