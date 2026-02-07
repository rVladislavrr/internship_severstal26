import logging
from datetime import datetime, timedelta, time

from fastapi import HTTPException, status
from sqlalchemy import select, and_, func, or_, text, DateTime, Date, literal, union_all
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

    async def get_subjects_statistics(
            self,
            session: AsyncSession,
            start_date: datetime,
            end_date: datetime,
            request_id: str,
    ):
        logger.debug(f'{request_id} | Получение даты')
        try:
            if start_date is None:
                first_date_query = select(func.min(SubjectsORM.create_at))
                first_date_result = await session.execute(first_date_query)
                first_date = first_date_result.scalar()
                start_date = first_date or datetime.now()

            if end_date is None:
                end_date = datetime.now()
        except Exception as e:
            logger.error(f'{request_id} | ошибка в получении периода', exc_info=e)
        logger.debug(f'{request_id} | Период получен')

        start_of_day = datetime.combine(start_date.date(), time.min)
        end_of_day = datetime.combine(end_date.date(), time.max)

        logger.debug(f'{request_id} | Начинаем получение статистики')

        added_count_query = select(func.count(SubjectsORM.id)).where(
            and_(
                SubjectsORM.create_at >= start_of_day,
                SubjectsORM.create_at <= end_of_day
            )
        )
        added_count_result = await session.execute(added_count_query)
        added_count = added_count_result.scalar() or 0

        deleted_count_query = select(func.count(SubjectsORM.id)).where(
            and_(
                SubjectsORM.delete_at >= start_of_day,
                SubjectsORM.delete_at <= end_of_day,
                SubjectsORM.is_active == False
            )
        )
        deleted_count_result = await session.execute(deleted_count_query)
        deleted_count = deleted_count_result.scalar() or 0

        stats_query = select(
            func.avg(SubjectsORM.length).label('avg_length'),
            func.avg(SubjectsORM.weight).label('avg_weight'),
            func.max(SubjectsORM.length).label('max_length'),
            func.min(SubjectsORM.length).label('min_length'),
            func.max(SubjectsORM.weight).label('max_weight'),
            func.min(SubjectsORM.weight).label('min_weight'),
            func.sum(SubjectsORM.weight).label('total_weight'),
            func.count(SubjectsORM.id).label('total_count')
        ).where(
            and_(
                SubjectsORM.create_at <= end_of_day,
                or_(
                    SubjectsORM.delete_at > start_of_day,
                    SubjectsORM.delete_at.is_(None),
                    SubjectsORM.is_active == True
                )
            )
        )

        stats_result = await session.execute(stats_query)
        stats = stats_result.first()

        time_stats_query = select(
            func.max(SubjectsORM.delete_at - SubjectsORM.create_at).label('max_time'),
            func.min(SubjectsORM.delete_at - SubjectsORM.create_at).label('min_time')
        ).where(
            and_(
                SubjectsORM.delete_at.isnot(None),
                SubjectsORM.delete_at >= start_of_day,
                SubjectsORM.delete_at <= end_of_day
            )
        )

        time_stats_result = await session.execute(time_stats_query)
        time_stats = time_stats_result.first()

        logger.debug(f'{request_id} | Получаем дни')
        try:
            extreme_days = await self._get_extreme_days(session, start_of_day, end_of_day, request_id)
            max_subjects_day = extreme_days.get('max_subjects') or {'date': None, 'count': 0}
            min_subjects_day = extreme_days.get('min_subjects') or {'date': None, 'count': 0}
            max_weight_day = extreme_days.get('max_weight') or {'date': None, 'total_weight': 0}
            min_weight_day = extreme_days.get('min_weight') or {'date': None, 'total_weight': 0}

            day_stats = {
                "max_subjects_day": {
                    "date": max_subjects_day['date'].isoformat() if max_subjects_day.get('date') else None,
                    "count": max_subjects_day['count']
                },
                "min_subjects_day": {
                    "date": min_subjects_day['date'].isoformat() if min_subjects_day.get('date') else None,
                    "count": min_subjects_day['count']
                },
                "max_weight_day": {
                    "date": max_weight_day['date'].isoformat() if max_weight_day.get('date') else None,
                    "weight": round(max_weight_day['total_weight'], 2)
                },
                "min_weight_day": {
                    "date": min_weight_day['date'].isoformat() if min_weight_day.get('date') else None,
                    "weight": round(min_weight_day['total_weight'], 2)
                }
            }
            logger.debug(f'{request_id} | Статистика по дням получена')
        except Exception as e:
            logger.error(f'{request_id} | Ошибка в получении дней', exc_info=e)
            day_stats = {}

        result = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "added_count": added_count,
            "deleted_count": deleted_count,
            "average_length": round(float(stats.avg_length) if stats and stats.avg_length else 0, 2),
            "average_weight": round(float(stats.avg_weight) if stats and stats.avg_weight else 0, 2),
            "max_length": round(float(stats.max_length) if stats and stats.max_length else 0, 2),
            "min_length": round(float(stats.min_length) if stats and stats.min_length else 0, 2),
            "max_weight": round(float(stats.max_weight) if stats and stats.max_weight else 0, 2),
            "min_weight": round(float(stats.min_weight) if stats and stats.min_weight else 0, 2),
            "total_weight": round(float(stats.total_weight) if stats and stats.total_weight else 0, 2),
            "total_count": stats.total_count if stats else 0,
            "max_time_in_storage": str(time_stats.max_time) if time_stats and time_stats.max_time else None,
            "min_time_in_storage": str(time_stats.min_time) if time_stats and time_stats.min_time else None,
        }
        result.update(day_stats)
        return result

    @staticmethod
    async def _get_extreme_days(
            session: AsyncSession,
            start_date: datetime,
            end_date: datetime,
            request_id: str
    ):
        logger.debug(f'{request_id} | Ищем дни')

        dates = []
        current_date = start_date.date()
        while current_date <= end_date.date():
            dates.append(current_date)
            current_date += timedelta(days=1)

        if not dates:
            return {}

        subqueries = []

        for day in dates:
            day_start = datetime.combine(day, datetime.min.time())
            day_end = datetime.combine(day, datetime.max.time())

            subquery = select(
                literal(day).label('date'),
                func.count(SubjectsORM.id).label('count'),
                func.coalesce(func.sum(SubjectsORM.weight), 0).label('total_weight')
            ).where(
                and_(
                    SubjectsORM.create_at <= day_end,
                    or_(
                        SubjectsORM.delete_at > day_start,
                        SubjectsORM.delete_at.is_(None),
                        SubjectsORM.is_active == True
                    )
                )
            )
            subqueries.append(subquery)

        if len(subqueries) == 1:
            union_query = subqueries[0]
        else:
            union_query = union_all(*subqueries)

        result = await session.execute(union_query)
        rows = result.all()

        stats_by_date = {day: {'count': 0, 'total_weight': 0.0} for day in dates}

        for row in rows:
            date = row.date
            if date in stats_by_date:
                stats_by_date[date]['count'] = row.count
                stats_by_date[date]['total_weight'] = float(row.total_weight)

        stats_list = [
            {'date': date, 'count': data['count'], 'total_weight': data['total_weight']}
            for date, data in stats_by_date.items()
        ]

        if not stats_list:
            return {}

        result_dict = {}
        max_subjects = max(stats_list, key=lambda x: x['count'])
        result_dict['max_subjects'] = {
            'date': max_subjects['date'],
            'count': max_subjects['count']
        }

        min_subjects = min(stats_list, key=lambda x: x['count'])
        result_dict['min_subjects'] = {
            'date': min_subjects['date'],
            'count': min_subjects['count']
        }

        max_weight = max(stats_list, key=lambda x: x['total_weight'])
        result_dict['max_weight'] = {
            'date': max_weight['date'],
            'total_weight': max_weight['total_weight']
        }

        min_weight = min(stats_list, key=lambda x: x['total_weight'])
        result_dict['min_weight'] = {
            'date': min_weight['date'],
            'total_weight': min_weight['total_weight']
        }

        logger.debug(f'{request_id} | Экстремальные дни найдены')
        return result_dict


subjects_manager = SubjectsManager()
