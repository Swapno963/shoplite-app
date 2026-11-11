from django.core.management.base import BaseCommand

from api.models import Product

SEED_PRODUCTS = [
    {"name": "Ceramic Pour-Over Kettle", "price": "42.00", "stock": 40},
    {"name": "Single-Origin Coffee Beans", "price": "18.50", "stock": 120},
    {"name": "Wireless Over-Ear Headphones", "price": "129.99", "stock": 35},
    {"name": "Mechanical Keyboard", "price": "89.00", "stock": 22},
    {"name": "USB-C Hub", "price": "34.75", "stock": 60},
    {"name": "Desk Lamp", "price": "27.00", "stock": 48},
    {"name": "Canvas Tote Bag", "price": "16.00", "stock": 90},
    {"name": "Stainless Water Bottle", "price": "22.40", "stock": 75},
    {"name": "Notebook Set", "price": "12.99", "stock": 150},
    {"name": "Wireless Mouse", "price": "24.50", "stock": 80},
    {"name": "Monitor Stand", "price": "39.00", "stock": 28},
    {"name": "LED Strip Lights", "price": "19.95", "stock": 55},
]


class Command(BaseCommand):
    help = "Seed the products table if it is empty."

    def handle(self, *args, **options):
        if Product.objects.exists():
            self.stdout.write("Products already seeded; skipping.")
            return

        Product.objects.bulk_create([Product(**item) for item in SEED_PRODUCTS])
        self.stdout.write(f"Seeded {len(SEED_PRODUCTS)} products.")
