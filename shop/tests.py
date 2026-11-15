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


class Phase5AExperienceTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name='Whey Isolate', slug='whey-iso-5a')
        self.p1 = Product.objects.create(
            category=self.cat, name='Rule 1 R1', slug='rule-1-r1',
            brand='Rule 1', flavor='Chocolate', goal='lean_bulk',
            price=Decimal('1950000'), servings='76 Servings', stock=5, available=True
        )
        self.p2 = Product.objects.create(
            category=self.cat, name='OstroVit Creatine', slug='ostrovit-creatine',
            brand='OstroVit', flavor='Unflavored', goal='strength',
            price=Decimal('450000'), servings='100 Servings', stock=10, available=True
        )

    def test_bundle_add_to_cart_and_stock_check(self):
        from shop.models import Bundle
        bundle = Bundle.objects.create(
            name='Combo Tang Co', slug='combo-tang-co', bundle_price=Decimal('2200000'), active=True
        )
        bundle.products.add(self.p1, self.p2)
        self.assertEqual(bundle.savings_amount, Decimal('200000'))
        resp = self.client.post(reverse('shop:bundle_add', args=[bundle.id]))
        self.assertRedirects(resp, reverse('cart:cart_detail'))
        self.assertEqual(len(self.client.session.get('cart', {})), 2)

    def test_wishlist_guest_session_and_login_sync(self):
        from shop.models import WishlistItem
        self.client.post(reverse('shop:wishlist_toggle', args=[self.p1.id]))
        self.assertIn(self.p1.id, self.client.session.get('wishlist', []))
        user = User.objects.create_user(username='gymer1', password='Password123!')
        self.client.login(username='gymer1', password='Password123!')
        self.assertTrue(WishlistItem.objects.filter(user=user, product=self.p1).exists())

    def test_compare_limit_3_and_view(self):
        p3 = Product.objects.create(category=self.cat, name='P3', slug='p3', price=Decimal('1000000'), stock=3)
        p4 = Product.objects.create(category=self.cat, name='P4', slug='p4', price=Decimal('1100000'), stock=3)
        for p in [self.p1, self.p2, p3, p4]:
            self.client.post(reverse('shop:compare_toggle', args=[p.id]))
        self.assertEqual(len(self.client.session.get('compare', [])), 3)
        resp = self.client.get(reverse('shop:compare'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Rule 1 R1')

    def test_recently_viewed_and_advanced_filters(self):
        self.client.get(self.p1.get_absolute_url())
        self.assertIn(self.p1.id, self.client.session.get('recently_viewed', []))
        resp = self.client.get(reverse('shop:product_list'), {'brand': 'Rule 1', 'goal': 'lean_bulk', 'in_stock': '1'})
        self.assertEqual(list(resp.context['products']), [self.p1])
