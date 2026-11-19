import json
import logging

import redis
from django.conf import settings
from opentelemetry.propagate import inject

logger = logging.getLogger(__name__)

_client = None


def get_redis():
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def enqueue_order(order_id: int) -> None:
    payload = {"order_id": order_id}
    inject(payload)
    get_redis().lpush(settings.ORDERS_QUEUE, json.dumps(payload))
    logger.info("enqueued order %s", order_id)


def queue_depth() -> int:
    return int(get_redis().llen(settings.ORDERS_QUEUE))


def ping_redis() -> bool:
    get_redis().ping()
    return True
