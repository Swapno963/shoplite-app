from django.urls import path

from api import views

urlpatterns = [
    path("products", views.list_products),
    path("products/<int:product_id>", views.get_product),
    path("orders", views.create_order),
    path("orders/<int:order_id>", views.get_order),
    path("healthz", views.healthz),
    path("readyz", views.readyz),
    path("metrics", views.metrics),
]
