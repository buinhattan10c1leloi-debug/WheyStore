import os
from datetime import timedelta
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from shop.models import Category, Product, Review
from orders.models import Coupon, Order, OrderItem


def run_seed():
    # 1. Tạo Superuser: admin / admin@wheystore.com / admin123
    User = get_user_model()
    admin_user, _ = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@wheystore.com',
            'is_staff': True,
            'is_superuser': True,
        }
    )
    admin_user.email = 'admin@wheystore.com'
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.set_password('admin123')
    admin_user.save()
    print("[OK] Superuser 'admin' (admin@wheystore.com / admin123) sẵn sàng.")

    # 2. Tạo 2 danh mục: 'Whey Isolate' và 'Pre-Workout'
    cat_isolate, _ = Category.objects.update_or_create(
        slug='whey-isolate',
        defaults={'name': 'Whey Isolate'}
    )
    cat_preworkout, _ = Category.objects.update_or_create(
        slug='pre-workout',
        defaults={'name': 'Pre-Workout'}
    )

    # 3. Tạo hoặc cập nhật 4 sản phẩm mẫu (ISO HD đặt stock=4 để test cảnh báo stock <= 5)
    sample_products = [
        {
            'slug': 'rule-1-protein-5lbs',
            'defaults': {
                'category': cat_isolate,
                'name': 'Rule 1 Protein 5lbs',
                'price': 1750000,
                'weight': '5lbs',
                'flavor': 'Chocolate',
                'stock': 35,
                'available': True,
                'description': (
                    'Rule 1 R1 Protein 100% Whey Isolate & Hydrolyzed siêu tinh khiết.\n'
                    '- 25g Protein hấp thu nhanh mỗi serving\n'
                    '- Hơn 6g BCAA hỗ trợ phục hồi cơ bắp\n'
                    '- 0g Đường, 0g Chất béo, 0g Gluten, không độn Amino'
                ),
            }
        },
        {
            'slug': 'gold-standard-100-whey-5lbs',
            'defaults': {
                'category': cat_isolate,
                'name': 'Gold Standard 100% Whey 5lbs',
                'price': 1850000,
                'weight': '5lbs',
                'flavor': 'Vanilla',
                'stock': 42,
                'available': True,
                'description': (
                    'Optimum Nutrition Gold Standard 100% Whey - Sản phẩm Whey bán chạy số 1 thế giới.\n'
                    '- 24g Protein chất lượng cao với thành phần chính là Whey Isolate\n'
                    '- 5.5g BCAA tự nhiên và 4g Glutamine & Glutamic Acid\n'
                    '- Bột mịn, dễ hòa tan, hương vị Vanilla thơm dịu'
                ),
            }
        },
        {
            'slug': 'iso-hd-5lbs',
            'defaults': {
                'category': cat_isolate,
                'name': 'ISO HD 5lbs',
                'price': 1650000,
                'weight': '5lbs',
                'flavor': 'Cookies & Cream',
                'stock': 4,
                'available': True,
                'description': (
                    'BPI Sports ISO HD chứa 100% Whey Protein Isolate tinh khiết.\n'
                    '- 25g Protein siêu tinh khiết phát triển cơ nạc tối đa\n'
                    '- Hàm lượng Calo, Carb và Fat cực thấp\n'
                    '- Phù hợp cho giai đoạn siết cơ (Cutting) và tăng cơ giảm mỡ'
                ),
            }
        },
        {
            'slug': 'c4-original-pre-workout',
            'defaults': {
                'category': cat_preworkout,
                'name': 'C4 Original Pre-Workout',
                'price': 750000,
                'weight': '60 Servings (390g)',
                'flavor': 'Fruit Punch',
                'stock': 50,
                'available': True,
                'description': (
                    'Cellucor C4 Original Pre-Workout bùng nổ sức mạnh và sự tỉnh táo trước buổi tập.\n'
                    '- 1.6g CarnoSyn Beta-Alanine giảm mỏi cơ, tăng sức bền\n'
                    '- 1g Creatine Nitrate & 1g Arginine AKG hỗ trợ bơm cơ cực đại\n'
                    '- 150mg Caffeine giúp tập trung cao độ trong suốt buổi tập'
                ),
            }
        },
    ]

    created_products = {}
    for item in sample_products:
        prod, _ = Product.objects.update_or_create(slug=item['slug'], defaults=item['defaults'])
        created_products[prod.slug] = prod

    # 4. Tạo 2 mã giảm giá mẫu: GYMBRO10 (10%) và WHEYVIP20 (20%)
    c1, _ = Coupon.objects.update_or_create(
        code='GYMBRO10',
        defaults={'discount_percent': 10, 'active': True}
    )
    c2, _ = Coupon.objects.update_or_create(
        code='WHEYVIP20',
        defaults={'discount_percent': 20, 'active': True}
    )

    # 5. Tạo đánh giá 5 sao mẫu
    Review.objects.all().delete()
    sample_reviews = [
        ('rule-1-protein-5lbs', 'Hoàng Nam (PT Gym Quận 1)', 5, 'Rule 1 vị Chocolate uống cực kỳ thanh, lắc 3 cái là tan hết sạch, không bị ngọt gắt. Tập xong làm 1 muỗng phục hồi cơ cực tốt!'),
        ('rule-1-protein-5lbs', 'Trần Đức Mạnh', 5, 'Hàng chuẩn chính hãng tem mác đầy đủ, giá tốt. Dòng Isolate này bụng yếu uống êm ru không lo đầy bụng.'),
        ('gold-standard-100-whey-5lbs', 'Lê Minh Khôi', 5, 'Huyền thoại Gold Standard vị Vanilla pha với sữa tươi không đường hay nước lọc đều đỉnh. Đáng đồng tiền bát gạo!'),
        ('gold-standard-100-whey-5lbs', 'Nguyễn Quốc Bảo', 5, 'Shop giao hàng siêu tốc, đóng gói kỹ. Đã dùng hết 2 hũ lên cơ nạc rất nét.'),
        ('iso-hd-5lbs', 'Phạm Hải Đăng', 5, 'Vị Cookies & Cream thơm béo mà lượng calo thấp, quá hợp cho anh em đang siết cơ Cutting.'),
        ('c4-original-pre-workout', 'Vũ Tuấn Kiệt (Powerlifter)', 5, 'Làm 1 muỗng C4 trước tập 20 phút vào phòng tạ tỉnh như sáo, bơm cơ căng đét, đẩy mức tạ PR mới luôn!'),
    ]
    for slug, user_name, rating, comment in sample_reviews:
        if slug in created_products:
            Review.objects.create(
                product=created_products[slug],
                user_name=user_name,
                rating=rating,
                comment=comment,
                verified_purchase=True,
            )

    # 6. Tạo 4 đơn hàng mẫu trải đều các ngày gần đây để Dashboard hiển thị biểu đồ sống động
    if Order.objects.count() == 0:
        now = timezone.now()
        p_r1 = created_products['rule-1-protein-5lbs']
        p_gold = created_products['gold-standard-100-whey-5lbs']
        p_iso = created_products['iso-hd-5lbs']
        p_c4 = created_products['c4-original-pre-workout']

        sample_orders = [
            {
                'full_name': 'Nguyễn Minh Quân',
                'phone': '0901234567',
                'email': 'quan.gym@gmail.com',
                'address': '88 Nguyễn Huệ, Quận 1',
                'city': 'TP. Hồ Chí Minh',
                'payment_method': 'BANK',
                'status': 'COMPLETED',
                'total_amount': 3500000,
                'days_ago': 3,
                'items': [(p_r1, 2, 1750000)],
            },
            {
                'full_name': 'Lê Hoàng Long',
                'phone': '0918765432',
                'email': 'long.fitness@gmail.com',
                'address': '12 Cầu Giấy',
                'city': 'Hà Nội',
                'payment_method': 'COD',
                'status': 'SHIPPING',
                'total_amount': 2600000,
                'days_ago': 1,
                'items': [(p_gold, 1, 1850000), (p_c4, 1, 750000)],
            },
            {
                'full_name': 'Trần Tuấn Anh',
                'phone': '0987654321',
                'email': 'tuananh.pt@gmail.com',
                'address': '45 Lê Duẩn, Hải Châu',
                'city': 'Đà Nẵng',
                'payment_method': 'BANK',
                'status': 'PENDING',
                'coupon': c1,
                'discount_percent': 10,
                'discount_amount': 165000,
                'total_amount': 1485000,
                'days_ago': 0,
                'items': [(p_iso, 1, 1650000)],
            },
            {
                'full_name': 'Phạm Gia Huy',
                'phone': '0933445566',
                'email': 'huy.power@gmail.com',
                'address': '210 Võ Văn Ngân, Thủ Đức',
                'city': 'TP. Hồ Chí Minh',
                'payment_method': 'COD',
                'status': 'PENDING',
                'total_amount': 2500000,
                'days_ago': 0,
                'items': [(p_r1, 1, 1750000), (p_c4, 1, 750000)],
            },
        ]

        for od in sample_orders:
            items = od.pop('items')
            days_ago = od.pop('days_ago')
            order = Order.objects.create(**od)
            target_time = now - timedelta(days=days_ago)
            Order.objects.filter(id=order.id).update(created=target_time)
            for prod, qty, price in items:
                OrderItem.objects.create(order=order, product=prod, quantity=qty, price=price)

    print(f"[HOÀN TẤT] Tổng đơn hàng trên Dashboard: {Order.objects.count()} | Sản phẩm sắp hết kho (<=5): {Product.objects.filter(stock__lte=5).count()}")


if __name__ == '__main__':
    run_seed()
