import json
import logging

import redis
from django.conf import settings
from opentelemetry import trace
from opentelemetry.propagate import inject

logger = logging.getLogger(__name__)

_client = None


def get_redis():
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def enqueue_order(order_id: int) -> None:
    tracer = trace.get_tracer("catalog-api")
    with tracer.start_as_current_span(
        "enqueue_order",
        attributes={
            "order.id": order_id,
            "messaging.system": "redis",
            "messaging.destination": settings.ORDERS_QUEUE,
        },
    ):
        payload = {"order_id": order_id}
        inject(payload)
        get_redis().lpush(settings.ORDERS_QUEUE, json.dumps(payload))
        logger.info("enqueued order %s", order_id)


def queue_depth() -> int:
    return int(get_redis().llen(settings.ORDERS_QUEUE))


def ping_redis() -> bool:
    get_redis().ping()
    return True
