from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.cache import cache
from shop.models import Category, Product, Review
from orders.models import Order, OrderItem


class Phase1SecurityAndBugfixTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.category = Category.objects.create(name='Whey Isolate', slug='whey-isolate')
        self.product = Product.objects.create(
            category=self.category,
            name='Rule 1 R1 Protein 5lbs',
            slug='rule-1-r1-protein-5lbs',
            brand='Rule 1',
            price=Decimal('1950000'),
            stock=5,
            available=True,
        )
        self.staff_user = User.objects.create_user(
            username='staff_admin',
            password='StrongPassword123!',
            is_staff=True
        )

    def test_BUG_01_idor_order_success_uses_uuid_token_not_sequential_id(self):
        order = Order.objects.create(
            full_name='Nguyen Van A',
            phone='0987654321',
            address='123 Le Loi, Q1',
            city='TP HCM',
            total_amount=Decimal('1950000')
        )
        # Truy cập bằng ID tuần tự phải bị 404
        resp_id = self.client.get(f'/orders/success/{order.id}/')
        self.assertEqual(resp_id.status_code, 404)

        # Truy cập bằng UUID access_token thành công
        resp_tok = self.client.get(reverse('orders:order_success', args=[order.access_token]))
        self.assertEqual(resp_tok.status_code, 200)

    def test_BUG_02_order_track_requires_exact_phone_and_rate_limits(self):
        order = Order.objects.create(
            full_name='Nguyen Van B',
            phone='0912345678',
            address='456 Nguyen Hue, Q1',
            city='TP HCM',
            total_amount=Decimal('1950000')
        )
        # Tìm một phần SĐT không được phép ra kết quả
        resp_partial = self.client.get(reverse('orders:order_track'), {'q': str(order.id), 'phone': '0912'})
        self.assertEqual(resp_partial.status_code, 200)
        self.assertNotContains(resp_partial, f'#DH{order.id}')

        # Đúng mã đơn + đúng SĐT (kể cả dạng +84) mới ra kết quả
        resp_exact = self.client.get(reverse('orders:order_track'), {'q': f'#DH{order.id}', 'phone': '+84912345678'})
        self.assertEqual(resp_exact.status_code, 200)
        self.assertContains(resp_exact, f'#DH{order.id}')

        # Rate limit sau 15 lần
        for _ in range(15):
            self.client.get(reverse('orders:order_track'), {'q': str(order.id), 'phone': '0912345678'})
        resp_rl = self.client.get(reverse('orders:order_track'), {'q': str(order.id), 'phone': '0912345678'})
        self.assertTrue(resp_rl.context['rate_limited'])

    def test_BUG_03_open_redirect_blocked_on_coupon_and_dashboard_login(self):
        resp_coupon = self.client.post(reverse('cart:coupon_apply'), {
            'code': 'INVALID',
            'next': 'https://evil.example.com/phish'
        })
        self.assertEqual(resp_coupon.status_code, 302)
        self.assertEqual(resp_coupon.url, reverse('cart:cart_detail'))

        resp_login = self.client.post(reverse('dashboard_login'), {
            'username': 'staff_admin',
            'password': 'StrongPassword123!',
            'next': '//evil.example.com/steal'
        })
        self.assertEqual(resp_login.status_code, 302)
        self.assertEqual(resp_login.url, reverse('dashboard'))

    def test_BUG_04_cart_and_order_stock_validation(self):
        # Không cho thêm vượt stock (stock=5)
        self.client.post(reverse('cart:cart_add', args=[self.product.id]), {'quantity': 6, 'override': False})
        resp_cart = self.client.get(reverse('cart:cart_detail'))
        self.assertEqual(len(resp_cart.context['cart']), 0)

        # Thêm 3 hộp hợp lệ
        self.client.post(reverse('cart:cart_add', args=[self.product.id]), {'quantity': 3, 'override': False})
        # Giảm stock DB xuống 2 trước khi đặt hàng
        self.product.stock = 2
        self.product.save()

        resp_order = self.client.post(reverse('orders:order_create'), {
            'full_name': 'Tran Van C',
            'phone': '0988888888',
            'address': '789 Cach Mang Thang 8',
            'city': 'TP HCM',
            'payment_method': 'COD'
        })
        self.assertEqual(resp_order.status_code, 302)
        self.assertEqual(Order.objects.count(), 0)

    def test_BUG_05_cart_uses_live_db_price_and_removes_unavailable_products(self):
        self.client.post(reverse('cart:cart_add', args=[self.product.id]), {'quantity': 1, 'override': False})
        # Đổi giá trong DB
        self.product.price = Decimal('2100000')
        self.product.save()
        resp_cart = self.client.get(reverse('cart:cart_detail'))
        self.assertEqual(resp_cart.context['cart'].get_total_price(), Decimal('2100000'))

        # Ngừng bán sản phẩm -> tự gỡ khỏi giỏ, không lỗi 500
        self.product.available = False
        self.product.save()
        resp_cart2 = self.client.get(reverse('cart:cart_detail'))
        self.assertEqual(resp_cart2.status_code, 200)
        self.assertEqual(len(resp_cart2.context['cart']), 0)

    def test_BUG_06_cancel_order_restocks_once_and_re_deducts_on_restore(self):
        self.client.force_login(self.staff_user)
        order = Order.objects.create(
            full_name='Le Van D',
            phone='0977777777',
            address='12 Hai Ba Trung',
            city='Ha Noi',
            total_amount=Decimal('3900000'),
            stock_deducted=True
        )
        OrderItem.objects.create(order=order, product=self.product, price=self.product.price, quantity=2)
        self.product.stock = 3
        self.product.save()

        # Hủy lần 1 -> hoàn +2 vào kho (stock=5)
        self.client.post(reverse('dashboard_update_order_status', args=[order.id]), {'status': 'CANCELLED'})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

        # Hủy lần 2 -> không được hoàn kho thêm
        self.client.post(reverse('dashboard_update_order_status', args=[order.id]), {'status': 'CANCELLED'})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

        # Khôi phục lại PENDING -> trừ kho lại 2 (stock=3)
        self.client.post(reverse('dashboard_update_order_status', args=[order.id]), {'status': 'PENDING'})
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

    def test_BUG_07_dashboard_restock_validation_logout_post_and_login_lockout(self):
        self.client.force_login(self.staff_user)
        # add_qty âm hoặc chữ không được lỗi 500
        resp_bad = self.client.post(reverse('dashboard_quick_restock', args=[self.product.id]), {'add_qty': 'abc'})
        self.assertEqual(resp_bad.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

        # Logout GET bị từ chối (405)
        resp_get_logout = self.client.get(reverse('dashboard_logout'))
        self.assertEqual(resp_get_logout.status_code, 405)

        # Logout POST thành công
        resp_post_logout = self.client.post(reverse('dashboard_logout'))
        self.assertEqual(resp_post_logout.status_code, 302)

        # Đăng nhập sai 5 lần -> khóa tạm
        for _ in range(5):
            self.client.post(reverse('dashboard_login'), {'username': 'staff_admin', 'password': 'wrong'})
        resp_locked = self.client.post(reverse('dashboard_login'), {
            'username': 'staff_admin',
            'password': 'StrongPassword123!'
        })
        self.assertContains(resp_locked, 'khóa')

    def test_BUG_08_order_form_phone_and_length_validation(self):
        self.client.post(reverse('cart:cart_add', args=[self.product.id]), {'quantity': 1, 'override': False})
        resp = self.client.post(reverse('orders:order_create'), {
            'full_name': 'A',
            'phone': '12345',
            'address': '123',
            'city': 'H',
            'payment_method': 'COD'
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['form'].is_valid())
        self.assertIn('phone', resp.context['form'].errors)
        self.assertIn('full_name', resp.context['form'].errors)
        self.assertIn('address', resp.context['form'].errors)

    def test_BUG_09_review_verified_purchase_default_false_and_no_reviews_text(self):
        resp_detail = self.client.get(self.product.get_absolute_url())
        self.assertContains(resp_detail, 'Chưa có đánh giá nào')

        # Gửi review khi chưa mua -> verified_purchase=False
        self.client.post(self.product.get_absolute_url(), {
            'submit_review': '1',
            'user_name': 'Khach Chua Mua',
            'rating': 5,
            'comment': 'San pham rat tot!'
        })
        rev = Review.objects.get(product=self.product, user_name='Khach Chua Mua')
        self.assertFalse(rev.verified_purchase)


class Phase4ConcurrencyAndIntegrityTests(TestCase):
    def test_last_item_stock_prevents_oversell(self):
        cat = Category.objects.create(name='Whey', slug='whey-conc')
        prod = Product.objects.create(
            category=cat, name='Last Item Whey', slug='last-item-whey',
            price=Decimal('1500000'), stock=1, available=True
        )
        client1 = Client()
        client2 = Client()
        client1.post(reverse('cart:cart_add', args=[prod.id]), {'quantity': 1, 'override': False})
        client2.post(reverse('cart:cart_add', args=[prod.id]), {'quantity': 1, 'override': False})

        payload1 = {
            'full_name': 'Khach Mot',
            'phone': '0911111111',
            'address': '123 Duong A, Quan 1',
            'city': 'TP.HCM',
            'payment_method': 'COD',
        }
        payload2 = {
            'full_name': 'Khach Hai',
            'phone': '0922222222',
            'address': '456 Duong B, Quan 2',
            'city': 'TP.HCM',
            'payment_method': 'COD',
        }
        r1 = client1.post(reverse('orders:order_create'), payload1)
        r2 = client2.post(reverse('orders:order_create'), payload2)

        self.assertEqual(r1.status_code, 302)
        self.assertEqual(Order.objects.count(), 1)
        prod.refresh_from_db()
        self.assertEqual(prod.stock, 0)
        self.assertRedirects(r2, reverse('cart:cart_detail'))
        self.assertEqual(Order.objects.count(), 1)
