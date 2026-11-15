from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from shop.models import Category, Product
from orders.models import Order, OrderStatusLog


class Phase2ShopAndDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.cat = Category.objects.create(name='Whey Isolate', slug='whey-isolate')
        self.p1 = Product.objects.create(
            category=self.cat,
            name='Rule 1 R1 Protein 5lbs',
            slug='rule-1-r1-protein-5lbs',
            brand='Rule 1',
            price=Decimal('1950000'),
            stock=10,
            available=True,
        )
        self.staff = User.objects.create_user(username='admin_test', password='Password123!', is_staff=True)

    def test_search_suggest_api(self):
        resp = self.client.get(reverse('search_suggest_api'), {'q': 'Rule 1'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['name'], 'Rule 1 R1 Protein 5lbs')

    def test_order_status_transition_and_logs(self):
        self.client.force_login(self.staff)
        order = Order.objects.create(
            full_name='Nguyen Van E',
            phone='0909090909',
            address='12 Nguyen Trai',
            city='TP HCM',
            status='PENDING',
            total_amount=Decimal('1950000')
        )
        # PENDING -> COMPLETED (không hợp lệ trực tiếp nếu chưa SHIPPING, theo ALLOWED_TRANSITIONS)
        self.client.post(reverse('dashboard_update_order_status', args=[order.id]), {'status': 'COMPLETED'})
        order.refresh_from_db()
        self.assertEqual(order.status, 'PENDING')

        # PENDING -> PAID -> SHIPPING -> COMPLETED (hợp lệ)
        self.client.post(reverse('dashboard_update_order_status', args=[order.id]), {'status': 'PAID'})
        self.client.post(reverse('dashboard_update_order_status', args=[order.id]), {'status': 'SHIPPING'})
        self.client.post(reverse('dashboard_update_order_status', args=[order.id]), {'status': 'COMPLETED'})
        order.refresh_from_db()
        self.assertEqual(order.status, 'COMPLETED')
        self.assertEqual(OrderStatusLog.objects.filter(order=order).count(), 3)

    def test_dashboard_export_csv(self):
        self.client.force_login(self.staff)
        Order.objects.create(
            full_name='Khach CSV',
            phone='0988776655',
            address='10 Le Loi',
            city='Da Nang',
            total_amount=Decimal('1950000')
        )
        resp = self.client.get(reverse('dashboard_export_orders_csv'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/csv', resp['Content-Type'])
        self.assertContains(resp, 'Khach CSV')
