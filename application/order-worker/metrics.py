from prometheus_client import Counter, Gauge, Histogram, start_http_server

ORDERS_PROCESSED_TOTAL = Counter(
    "orders_processed_total",
    "Orders processed by the worker",
    ["result"],
)

ORDER_QUEUE_DEPTH = Gauge(
    "order_queue_depth",
    "Number of pending orders in the Redis queue",
)

ORDER_PROCESSING_SECONDS = Histogram(
    "order_processing_seconds",
    "Time spent processing a single order",
    buckets=(0.5, 1, 1.5, 2, 3, 5, 10, 30),
)


def start_metrics_server(port: int) -> None:
    start_http_server(port)
