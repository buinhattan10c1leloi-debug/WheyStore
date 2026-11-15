from decimal import Decimal
from django.conf import settings
from shop.models import Product
from orders.models import Coupon


class Cart:
    def __init__(self, request):
        """
        Khởi tạo giỏ hàng từ session của request.
        """
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart
        # Lưu ID của mã giảm giá hiện tại trong session
        self.coupon_id = self.session.get('coupon_id')

    def add(self, product, quantity=1, override_quantity=False):
        """
        Thêm một sản phẩm vào giỏ hàng hoặc cập nhật số lượng của nó.
        """
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {
                'quantity': 0,
                'price': str(product.price)
            }
        if override_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
        self.save()

    def save(self):
        """
        Đánh dấu session đã được thay đổi (modified) để đảm bảo Django lưu lại.
        """
        self.session.modified = True

    def remove(self, product):
        """
        Xóa một sản phẩm khỏi giỏ hàng.
        """
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        """
        Lặp qua các mặt hàng trong giỏ và lấy đối tượng Product tương ứng từ database.
        """
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        cart = self.cart.copy()
        for product in products:
            cart[str(product.id)]['product'] = product
        for item in cart.values():
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        """
        Đếm tổng số lượng sản phẩm có trong giỏ hàng.
        """
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        """
        Tính tổng tiền tạm tính (chưa trừ mã giảm giá).
        """
        return sum(
            Decimal(item['price']) * item['quantity']
            for item in self.cart.values()
        )

    @property
    def coupon(self):
        if self.coupon_id:
            try:
                return Coupon.objects.get(id=self.coupon_id, active=True)
            except Coupon.DoesNotExist:
                pass
        return None

    def get_discount(self):
        if self.coupon:
            return (Decimal(self.coupon.discount_percent) / Decimal(100)) * self.get_total_price()
        return Decimal(0)

    def get_total_price_after_discount(self):
        return self.get_total_price() - self.get_discount()

    def clear(self):
        """
        Xóa sạch giỏ hàng và mã giảm giá khỏi session.
        """
        if settings.CART_SESSION_ID in self.session:
            del self.session[settings.CART_SESSION_ID]
        if 'coupon_id' in self.session:
            del self.session['coupon_id']
        self.save()
