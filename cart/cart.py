from decimal import Decimal
from django.conf import settings
from shop.models import Product
from orders.models import Coupon


class Cart:
    def __init__(self, request):
        """
        Khởi tạo giỏ hàng từ session của request.
        Chỉ ghi vào session khi thực sự có thao tác thay đổi giỏ hàng.
        """
        self.session = request.session
        self.cart = self.session.get(settings.CART_SESSION_ID, {})
        self.coupon_id = self.session.get('coupon_id')
        self.removed_items = []

    def add(self, product, quantity=1, override_quantity=False):
        """
        Thêm sản phẩm vào giỏ hoặc cập nhật số lượng (giới hạn không vượt quá stock).
        """
        if not product.available or product.stock <= 0:
            return False, "Sản phẩm hiện đã hết hàng hoặc ngừng kinh doanh."

        if settings.CART_SESSION_ID not in self.session:
            self.session[settings.CART_SESSION_ID] = self.cart

        product_id = str(product.id)
        current_qty = int(self.cart.get(product_id, {}).get('quantity', 0))
        new_qty = quantity if override_quantity else current_qty + quantity

        if new_qty <= 0:
            self.remove(product)
            return True, "Đã xóa sản phẩm khỏi giỏ hàng."

        if new_qty > product.stock:
            return False, f"Số lượng tối đa còn lại trong kho cho '{product.name}' là {product.stock}."

        self.cart[product_id] = {'quantity': int(new_qty)}
        self.save()
        return True, None

    def save(self):
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session.modified = True

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def _clean_and_fetch_products(self):
        product_ids = list(self.cart.keys())
        if not product_ids:
            return {}

        products = Product.objects.filter(id__in=product_ids, available=True, stock__gt=0)
        product_map = {str(p.id): p for p in products}

        removed_any = False
        for pid in product_ids:
            if pid not in product_map:
                del self.cart[pid]
                self.removed_items.append(pid)
                removed_any = True
            else:
                qty = int(self.cart[pid].get('quantity', 0))
                if qty <= 0:
                    del self.cart[pid]
                    removed_any = True

        if removed_any:
            self.save()

        return product_map

    def __iter__(self):
        product_map = self._clean_and_fetch_products()
        for pid, item_data in list(self.cart.items()):
            product = product_map.get(pid)
            if not product:
                continue
            qty = int(item_data.get('quantity', 0))
            price = product.price
            yield {
                'product': product,
                'quantity': qty,
                'price': price,
                'total_price': price * qty,
            }

    def __len__(self):
        return sum(int(item.get('quantity', 0)) for item in self.cart.values())

    def get_total_price(self):
        product_map = self._clean_and_fetch_products()
        total = Decimal(0)
        for pid, item_data in self.cart.items():
            product = product_map.get(pid)
            if product:
                total += product.price * int(item_data.get('quantity', 0))
        return total

    @property
    def coupon(self):
        if self.coupon_id:
            try:
                c = Coupon.objects.get(id=self.coupon_id)
                ok, _ = c.validate_for_order(self.get_total_price())
                if ok:
                    return c
            except Coupon.DoesNotExist:
                pass
        return None

    def get_discount(self):
        if self.coupon:
            return (Decimal(self.coupon.discount_percent) / Decimal(100)) * self.get_total_price()
        return Decimal(0)

    def get_total_price_after_discount(self):
        return max(Decimal(0), self.get_total_price() - self.get_discount())

    def get_shipping_fee(self):
        after_discount = self.get_total_price_after_discount()
        if after_discount <= 0:
            return Decimal(0)
        threshold = Decimal(getattr(settings, 'FREE_SHIPPING_THRESHOLD', 1000000))
        fee = Decimal(getattr(settings, 'STANDARD_SHIPPING_FEE', 30000))
        return Decimal(0) if after_discount >= threshold else fee

    def get_grand_total(self):
        return self.get_total_price_after_discount() + self.get_shipping_fee()

    def clear(self):
        if settings.CART_SESSION_ID in self.session:
            del self.session[settings.CART_SESSION_ID]
        if 'coupon_id' in self.session:
            del self.session['coupon_id']
        self.cart = {}
        self.session.modified = True
