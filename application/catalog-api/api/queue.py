import json
import logging

import redis
from django.conf import settings

logger = logging.getLogger(__name__)

_client = None


def get_redis():
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def enqueue_order(order_id: int) -> None:
    payload = json.dumps({"order_id": order_id})
    get_redis().lpush(settings.ORDERS_QUEUE, payload)
    logger.info("enqueued order %s", order_id)


def ping_redis() -> bool:
    get_redis().ping()
    return True
