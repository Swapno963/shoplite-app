import os

from opentelemetry import context, trace
from opentelemetry.propagate import extract

_initialized = False


def setup_telemetry() -> None:
    global _initialized
    if _initialized:
        return
    if os.getenv("OTEL_SDK_DISABLED", "").lower() in ("1", "true", "yes"):
        _initialized = True
        return

    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.logging import LoggingInstrumentor
        from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        name = os.getenv("OTEL_SERVICE_NAME") or os.getenv("SERVICE_NAME", "order-worker")
        resource = Resource.create({"service.name": name})
        provider = TracerProvider(resource=resource)
        if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip():
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)
        PsycopgInstrumentor().instrument()
        RedisInstrumentor().instrument()
        LoggingInstrumentor().instrument(set_logging_format=False)
    except Exception:
        _initialized = True
        return
    _initialized = True


def current_trace_id() -> str:
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx is not None and ctx.is_valid:
        return format(ctx.trace_id, "032x")
    return "-"


def attach_queue_context(payload: dict):
    ctx = extract(payload)
    return context.attach(ctx)


def detach_queue_context(token) -> None:
    context.detach(token)


def start_process_span(order_id: int):
    tracer = trace.get_tracer("order-worker")
    span = tracer.start_as_current_span(
        "process_order",
        attributes={"order.id": order_id},
    )
    return span
