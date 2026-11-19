from prometheus_client import REGISTRY, Counter, Gauge, Histogram
from prometheus_client.openmetrics.exposition import (
    CONTENT_TYPE_LATEST,
    generate_latest,
)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

ORDERS_CREATED_TOTAL = Counter(
    "orders_created_total",
    "Total orders accepted by the catalog API",
)

ORDERS_ENQUEUE_FAILURES_TOTAL = Counter(
    "orders_enqueue_failures_total",
    "Orders that failed to enqueue",
)

ORDER_QUEUE_DEPTH = Gauge(
    "order_queue_depth",
    "Number of pending orders in the Redis queue",
)


def _queue_depth() -> float:
    try:
        from api.queue import queue_depth

        return float(queue_depth())
    except Exception:
        return 0.0


ORDER_QUEUE_DEPTH.set_function(_queue_depth)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
