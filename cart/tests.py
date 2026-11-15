from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from shop.models import Category, Product
from orders.models import Coupon, Order


class Phase2CartAndCouponTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.cat = Category.objects.create(name='Pre-Workout', slug='pre-workout')
        self.p_cheap = Product.objects.create(
            category=self.cat,
            name='OstroVit Creatine 500g',
            slug='ostrovit-creatine-500g',
            brand='OstroVit',
            price=Decimal('640000'),
            stock=10,
            available=True,
        )
        self.p_expensive = Product.objects.create(
            category=self.cat,
            name='Rule 1 R1 Protein 5lbs',
            slug='rule-1-r1-protein-5lbs',
            brand='Rule 1',
            price=Decimal('1950000'),
            stock=10,
            available=True,
        )

    def test_ajax_cart_add_returns_json(self):
        resp = self.client.post(
            reverse('cart:cart_add', args=[self.p_cheap.id]),
            {'quantity': 1, 'override': False},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['cart_count'], 1)
        self.assertEqual(data['cart_total'], 640000)

    def test_shipping_fee_rules(self):
        # Dưới 1.000.000đ -> phí ship 30.000đ
        self.client.post(reverse('cart:cart_add', args=[self.p_cheap.id]), {'quantity': 1, 'override': False})
        self.client.post(reverse('orders:order_create'), {
            'full_name': 'Khach Ship 30k',
            'phone': '0987654321',
            'address': '123 Duong So 1',
            'city': 'TP HCM',
            'payment_method': 'COD'
        })
        order1 = Order.objects.get(full_name='Khach Ship 30k')
        self.assertEqual(order1.shipping_fee, Decimal('30000'))
        self.assertEqual(order1.total_amount, Decimal('670000'))

        # Từ 1.000.000đ trở lên -> Freeship (0đ)
        self.client.post(reverse('cart:cart_add', args=[self.p_expensive.id]), {'quantity': 1, 'override': False})
        self.client.post(reverse('orders:order_create'), {
            'full_name': 'Khach Freeship',
            'phone': '0987654322',
            'address': '456 Duong So 2',
            'city': 'TP HCM',
            'payment_method': 'COD'
        })
        order2 = Order.objects.get(full_name='Khach Freeship')
        self.assertEqual(order2.shipping_fee, Decimal('0'))
        self.assertEqual(order2.total_amount, Decimal('1950000'))

    def test_advanced_coupon_validation_and_used_count(self):
        now = timezone.now()
        expired_coupon = Coupon.objects.create(
            code='EXPIRED10',
            discount_percent=10,
            valid_to=now - timedelta(days=1),
            active=True
        )
        min_order_coupon = Coupon.objects.create(
            code='MIN2M',
            discount_percent=15,
            min_order_amount=Decimal('2000000'),
            max_uses=1,
            active=True
        )

        self.client.post(reverse('cart:cart_add', args=[self.p_cheap.id]), {'quantity': 1, 'override': False})

        # Hết hạn -> không áp dụng được
        self.client.post(reverse('cart:coupon_apply'), {'code': 'EXPIRED10'})
        self.assertIsNone(self.client.session.get('coupon_id'))

        # Chưa đạt đơn tối thiểu -> không áp dụng được
        self.client.post(reverse('cart:coupon_apply'), {'code': 'MIN2M'})
        self.assertIsNone(self.client.session.get('coupon_id'))

        # Thêm đủ >= 2.000.000đ -> áp dụng thành công & tăng used_count khi đặt hàng
        self.client.post(reverse('cart:cart_add', args=[self.p_expensive.id]), {'quantity': 1, 'override': False})
        self.client.post(reverse('cart:coupon_apply'), {'code': 'MIN2M'})
        self.assertEqual(self.client.session.get('coupon_id'), min_order_coupon.id)

        self.client.post(reverse('orders:order_create'), {
            'full_name': 'Khach Coupon',
            'phone': '0911223344',
            'address': '789 Duong So 3',
            'city': 'Ha Noi',
            'payment_method': 'COD'
        })
        min_order_coupon.refresh_from_db()
        self.assertEqual(min_order_coupon.used_count, 1)
