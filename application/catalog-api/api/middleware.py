import time
import uuid

from django.utils.deprecation import MiddlewareMixin

from api.metrics import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL
from catalog.tracing import set_trace_id


def _normalize_path(path: str) -> str:
    parts = path.rstrip("/").split("/")
    if len(parts) >= 3 and parts[1] == "products" and parts[2].isdigit():
        return "/products/{id}"
    if len(parts) >= 3 and parts[1] == "orders" and parts[2].isdigit():
        return "/orders/{id}"
    return path.rstrip("/") or "/"


class TraceIdMiddleware(MiddlewareMixin):
    def process_request(self, request):
        trace_id = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
        request.trace_id = trace_id
        set_trace_id(trace_id)


class MetricsMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._metrics_start = time.perf_counter()

    def process_response(self, request, response):
        endpoint = _normalize_path(request.path)
        if endpoint != "/metrics":
            duration = time.perf_counter() - getattr(request, "_metrics_start", time.perf_counter())
            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                endpoint=endpoint,
                status=str(response.status_code),
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=request.method,
                endpoint=endpoint,
            ).observe(duration)
        if hasattr(request, "trace_id"):
            response["X-Trace-Id"] = request.trace_id
        return response
