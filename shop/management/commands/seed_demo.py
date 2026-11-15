from django.core.management.base import BaseCommand
from shop.models import Category, Product
from orders.models import Coupon


class Command(BaseCommand):
    help = "Tạo dữ liệu mẫu an toàn (idempotent, không ghi đè dữ liệu hiện có)."

    def handle(self, *args, **options):
        cat_whey, _ = Category.objects.get_or_create(
            slug="whey-protein-isolate",
            defaults={"name": "Whey Protein Isolate"},
        )
        cat_creatine, _ = Category.objects.get_or_create(
            slug="pre-workout-creatine",
            defaults={"name": "Pre-Workout & Creatine"},
        )

        demo_products = [
            {
                "slug": "rule-1-r1-protein-5lbs",
                "category": cat_whey,
                "name": "Rule 1 R1 Protein 5lbs (2.3kg)",
                "brand": "Rule 1",
                "price": 1950000,
                "old_price": 2250000,
                "weight": "2.3kg (5lbs)",
                "flavor": "Chocolate Fudge",
                "servings": "76 Servings",
                "protein_per_serving": "25g",
                "bcaa_per_serving": "6g",
                "calories": "110 kcal",
                "sugar": "0g",
                "origin": "USA",
                "free_gift": "Tặng Bình Lắc Shaker + Freeship",
                "stock": 20,
                "available": True,
            },
            {
                "slug": "ostrovit-creatine-monohydrate-500g",
                "category": cat_creatine,
                "name": "OstroVit Creatine Monohydrate 500g",
                "brand": "OstroVit",
                "price": 450000,
                "old_price": 550000,
                "weight": "500g",
                "flavor": "Tự nhiên",
                "servings": "100 Servings",
                "protein_per_serving": "0g",
                "bcaa_per_serving": "5g Creatine",
                "calories": "0 kcal",
                "sugar": "0g",
                "origin": "Poland",
                "free_gift": "Muỗng đong tiêu chuẩn",
                "stock": 35,
                "available": True,
            },
        ]

        created_count = 0
        for item in demo_products:
            _, created = Product.objects.get_or_create(slug=item["slug"], defaults=item)
            if created:
                created_count += 1

        Coupon.objects.get_or_create(
            code="GYMBRO10",
            defaults={"discount_percent": 10, "active": True, "min_order_amount": 0},
        )
        Coupon.objects.get_or_create(
            code="WHEYVIP20",
            defaults={"discount_percent": 20, "active": True, "min_order_amount": 1000000},
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_demo hoàn tất: thêm mới {created_count} sản phẩm mẫu (dữ liệu cũ giữ nguyên)."
            )
        )
