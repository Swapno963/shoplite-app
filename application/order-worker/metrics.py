from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from prometheus_client import REGISTRY, Counter, Gauge, Histogram
from prometheus_client.openmetrics.exposition import (
    CONTENT_TYPE_LATEST,
    generate_latest,
)

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


class _OpenMetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        payload = generate_latest(REGISTRY)
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPE_LATEST)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


def start_metrics_server(port: int) -> None:
    server = ThreadingHTTPServer(("0.0.0.0", port), _OpenMetricsHandler)
    thread = Thread(target=server.serve_forever, name="metrics", daemon=True)
    thread.start()
