import logging
import random
import time

from django.conf import settings
from django.db import connection
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.metrics import ORDERS_CREATED_TOTAL, ORDERS_ENQUEUE_FAILURES_TOTAL, render_metrics
from api.models import Order, Product
from api.queue import enqueue_order, ping_redis
from api.serializers import OrderCreateSerializer, OrderSerializer, ProductSerializer

logger = logging.getLogger(__name__)


@api_view(["GET"])
def list_products(request):
    products = Product.objects.all()
    return Response(ProductSerializer(products, many=True).data)


@api_view(["GET"])
def get_product(request, product_id: int):
    if settings.CHAOS_LATENCY_MS > 0 and random.random() < 0.3:
        delay = settings.CHAOS_LATENCY_MS / 1000.0
        logger.info("chaos latency injected for %sms", settings.CHAOS_LATENCY_MS)
        time.sleep(delay)

    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return Response({"detail": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(ProductSerializer(product).data)


@api_view(["POST"])
def create_order(request):
    if settings.CHAOS_ERROR_RATE > 0 and random.random() < settings.CHAOS_ERROR_RATE:
        logger.warning("chaos error injected on POST /orders")
        return Response(
            {"detail": "Injected failure"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    serializer = OrderCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    product_id = serializer.validated_data["product_id"]
    quantity = serializer.validated_data["quantity"]

    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return Response({"detail": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

    order = Order.objects.create(
        product=product,
        quantity=quantity,
        status=Order.Status.PENDING,
    )

    try:
        enqueue_order(order.id)
    except Exception:
        logger.exception("failed to enqueue order %s", order.id)
        ORDERS_ENQUEUE_FAILURES_TOTAL.inc()
        order.status = Order.Status.FAILED
        order.save(update_fields=["status"])
        return Response(
            {"detail": "Failed to enqueue order"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    ORDERS_CREATED_TOTAL.inc()
    logger.info("created order %s", order.id)
    return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def get_order(request, order_id: int):
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return Response({"detail": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(OrderSerializer(order).data)


@api_view(["GET"])
def healthz(_request):
    return Response({"status": "ok"})


@api_view(["GET"])
def readyz(_request):
    checks = {"database": False, "queue": False}
    try:
        connection.ensure_connection()
        checks["database"] = True
    except Exception:
        logger.exception("readiness database check failed")

    try:
        ping_redis()
        checks["queue"] = True
    except Exception:
        logger.exception("readiness queue check failed")

    if all(checks.values()):
        return Response({"status": "ready", "checks": checks})
    return Response(
        {"status": "not_ready", "checks": checks},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@api_view(["GET"])
def metrics(_request):
    body, content_type = render_metrics()
    return HttpResponse(body, content_type=content_type)
