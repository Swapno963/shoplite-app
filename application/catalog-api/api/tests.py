from unittest.mock import patch

from django.test import override_settings
from rest_framework.test import APITestCase

from api.models import Order, Product


class CatalogApiTests(APITestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Test Mug",
            price="9.99",
            stock=10,
        )

    def test_list_products_returns_seeded_items(self):
        response = self.client.get("/products")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["name"], "Test Mug")

    def test_get_product_returns_404_when_missing(self):
        response = self.client.get("/products/999")
        self.assertEqual(response.status_code, 404)

    def test_get_product_returns_item(self):
        response = self.client.get(f"/products/{self.product.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.product.id)

    @patch("api.views.enqueue_order")
    def test_create_order_returns_201_and_pending_status(self, enqueue):
        response = self.client.post(
            "/orders",
            {"product_id": self.product.id, "quantity": 2},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "PENDING")
        self.assertTrue(body["id"])
        enqueue.assert_called_once()
        order = Order.objects.get(pk=body["id"])
        self.assertEqual(order.quantity, 2)

    def test_create_order_rejects_invalid_payload(self):
        response = self.client.post(
            "/orders",
            {"product_id": self.product.id, "quantity": 0},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_get_order_status(self):
        order = Order.objects.create(
            product=self.product,
            quantity=1,
            status=Order.Status.PENDING,
        )
        response = self.client.get(f"/orders/{order.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "PENDING")

    def test_healthz_is_alive(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    @patch("api.views.ping_redis")
    def test_readyz_requires_database_and_queue(self, ping_redis):
        ping_redis.return_value = True
        response = self.client.get("/readyz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")

    @override_settings(CHAOS_ERROR_RATE=1.0)
    def test_chaos_error_rate_returns_500_on_create_order(self):
        response = self.client.post(
            "/orders",
            {"product_id": self.product.id, "quantity": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 500)
