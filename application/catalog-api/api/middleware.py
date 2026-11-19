import time
import uuid

from django.utils.deprecation import MiddlewareMixin
from opentelemetry import trace

from api.metrics import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL
from catalog.tracing import set_trace_id


def _normalize_path(path: str) -> str:
    parts = path.rstrip("/").split("/")
    if len(parts) >= 3 and parts[1] == "products" and parts[2].isdigit():
        return "/products/{id}"
    if len(parts) >= 3 and parts[1] == "orders" and parts[2].isdigit():
        return "/orders/{id}"
    return path.rstrip("/") or "/"


def _current_trace_id() -> str:
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx is not None and ctx.is_valid:
        return format(ctx.trace_id, "032x")
    return uuid.uuid4().hex


class TraceIdMiddleware(MiddlewareMixin):
    def process_request(self, request):
        trace_id = _current_trace_id()
        request.trace_id = trace_id
        set_trace_id(trace_id)


class MetricsMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._metrics_start = time.perf_counter()

    def process_response(self, request, response):
        route = _normalize_path(request.path)
        if route != "/metrics":
            duration = time.perf_counter() - getattr(
                request, "_metrics_start", time.perf_counter()
            )
            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                route=route,
                status=str(response.status_code),
            ).inc()
            exemplar = None
            trace_id = getattr(request, "trace_id", None)
            if trace_id:
                exemplar = {"trace_id": trace_id}
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=request.method,
                route=route,
            ).observe(duration, exemplar=exemplar)
        if hasattr(request, "trace_id"):
            response["X-Trace-Id"] = request.trace_id
        return response
