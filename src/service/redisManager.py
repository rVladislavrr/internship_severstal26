import json
import logging
from src.service.redis_conn import redis_client

logger = logging.getLogger('Редис')


class RedisManager:

    @staticmethod
    async def get_subject_with_filters(filters_key: str, request_id: str):
        try:
            logger.debug(f'{request_id} | Получение данных из кеша')

            r = await redis_client.get_redis()
            result = await r.get('subject:' + filters_key)

            if result:
                logger.debug(f'{request_id} | Успешно получены данные из кеша')
                return [json.loads(res) for res in json.loads(result)]

            logger.debug(f'{request_id} | В кеше нету')
            return None
        except RuntimeError:
            return None
        except Exception as e:
            logger.error(f'{request_id} | Ошибка в получении данных из редиса', exc_info=e)
            return None

    @staticmethod
    async def set_subject_with_filters(filters_key: str, result, request_id: str):
        try:
            logger.debug(f'{request_id} | Кладём данные в кеш')
            r = await redis_client.get_redis()

            json_data = json.dumps([res.model_dump_json(exclude_unset=True) for res in result])
            await r.set('subject:' + filters_key, json_data, ex=300)
            logger.debug(f'{request_id} | Успешно положили')

        except RuntimeError:
            pass
        except Exception as e:
            logger.error(f'{request_id} | Ошибка при создании кеша с данными', exc_info=e)

    @staticmethod
    async def delete_subject_with_filters(request_id: str):
        try:
            logger.debug(f'{request_id} | Удаляем весь кеш по subject')
            r = await redis_client.get_redis()

            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await r.scan(cursor=cursor, match='subject:*', count=100)

                if keys:
                    await r.delete(*keys)
                    deleted_count += len(keys)

                if cursor == 0:
                    break

            logger.debug(f'{request_id} | Успешно удалено {deleted_count} ключей')
        except RuntimeError:
            pass
        except Exception as e:
            logger.error(f'{request_id} | Ошибка в удалении кеша', exc_info=e)


redis_manager = RedisManager()
