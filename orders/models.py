import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from shop.models import Product


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã giảm giá (Coupon)")
    discount_percent = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        default=10,
        verbose_name="Phần trăm giảm giá (%)"
    )
    valid_from = models.DateTimeField(null=True, blank=True, verbose_name="Hiệu lực từ")
    valid_to = models.DateTimeField(null=True, blank=True, verbose_name="Hiệu lực đến")
    min_order_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Đơn tối thiểu (VNĐ)"
    )
    max_uses = models.PositiveIntegerField(
        default=0,
        verbose_name="Số lượt dùng tối đa (0 = không giới hạn)"
    )
    used_count = models.PositiveIntegerField(default=0, verbose_name="Đã sử dụng")
    active = models.BooleanField(default=True, verbose_name="Đang kích hoạt")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    class Meta:
        ordering = ['-discount_percent']
        verbose_name = 'Mã giảm giá (Coupon)'
        verbose_name_plural = 'Mã giảm giá (Coupons)'

    def __str__(self):
        return f"{self.code} (-{self.discount_percent}%)"

    def validate_for_order(self, order_amount=None):
        """Kiểm tra đầy đủ điều kiện hiệu lực coupon. Trả về (is_valid, error_message)."""
        now = timezone.now()
        if not self.active:
            return False, "Mã giảm giá hiện đang tạm ngưng."
        if self.valid_from and now < self.valid_from:
            return False, "Mã giảm giá chưa đến thời gian áp dụng."
        if self.valid_to and now > self.valid_to:
            return False, "Mã giảm giá đã hết hạn sử dụng."
        if self.max_uses > 0 and self.used_count >= self.max_uses:
            return False, "Mã giảm giá đã hết lượt sử dụng."
        if order_amount is not None and Decimal(order_amount) < self.min_order_amount:
            min_fmt = f"{int(self.min_order_amount):,}".replace(",", ".")
            return False, f"Mã '{self.code}' yêu cầu đơn hàng tối thiểu {min_fmt}đ."
        return True, None


class Order(models.Model):
    PAYMENT_CHOICES = [
        ('COD', 'Thanh toán khi nhận hàng (COD)'),
        ('BANK', 'Chuyển khoản VietQR'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Chờ xử lý'),
        ('PAID', 'Đã thanh toán'),
        ('SHIPPING', 'Đang giao'),
        ('COMPLETED', 'Hoàn thành'),
        ('CANCELLED', 'Đã hủy'),
    ]

    ALLOWED_TRANSITIONS = {
        'PENDING': {'PAID', 'SHIPPING', 'CANCELLED'},
        'PAID': {'SHIPPING', 'CANCELLED'},
        'SHIPPING': {'COMPLETED', 'CANCELLED'},
        'COMPLETED': set(),
        'CANCELLED': {'PENDING'},
    }

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='orders',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Tài khoản khách hàng"
    )
    full_name = models.CharField(max_length=150, verbose_name="Họ và tên")
    phone = models.CharField(max_length=20, verbose_name="Số điện thoại")
    email = models.EmailField(blank=True, null=True, verbose_name="Email (không bắt buộc)")
    address = models.CharField(max_length=255, verbose_name="Địa chỉ nhận hàng chi tiết")
    city = models.CharField(max_length=100, verbose_name="Tỉnh / Thành phố")
    note = models.TextField(blank=True, verbose_name="Ghi chú giao hàng")
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_CHOICES,
        default='COD',
        verbose_name="Phương thức thanh toán"
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name="Trạng thái đơn hàng"
    )
    coupon = models.ForeignKey(
        Coupon,
        related_name='orders',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Mã giảm giá áp dụng"
    )
    discount_percent = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Phần trăm giảm (%)"
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Số tiền được giảm (VNĐ)"
    )
    shipping_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Phí vận chuyển (VNĐ)"
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Tổng thanh toán (VNĐ)"
    )
    access_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="Mã truy cập bảo mật"
    )
    stock_deducted = models.BooleanField(
        default=True,
        verbose_name="Đã trừ tồn kho"
    )
    created = models.DateTimeField(auto_now_add=True, verbose_name="Ngày đặt hàng")
    updated = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lần cuối")

    class Meta:
        ordering = ['-created']
        indexes = [
            models.Index(fields=['-created']),
            models.Index(fields=['phone']),
            models.Index(fields=['status']),
        ]
        verbose_name = 'Đơn hàng'
        verbose_name_plural = 'Đơn hàng'

    def __str__(self):
        return f'Đơn hàng #{self.id} - {self.full_name}'

    def get_subtotal_cost(self):
        return sum(item.get_cost() for item in self.items.all())

    def get_total_cost(self):
        subtotal = self.get_subtotal_cost()
        if self.discount_percent > 0:
            discount = (Decimal(self.discount_percent) / Decimal(100)) * subtotal
            return subtotal - discount
        return subtotal

    @property
    def vietqr_url(self):
        from urllib.parse import quote
        amount_int = int(self.total_amount)
        bank_id = getattr(settings, 'VIETQR_BANK_ID', 'MB')
        account_no = getattr(settings, 'VIETQR_ACCOUNT_NO', '0000000000')
        account_name = quote(getattr(settings, 'VIETQR_ACCOUNT_NAME', 'WHEYSTORE'))
        return (
            f"https://img.vietqr.io/image/{bank_id}-{account_no}-compact2.png"
            f"?amount={amount_int}&addInfo=WHEYSTORE%20DH{self.id}&accountName={account_name}"
        )

    def can_transition_to(self, new_status: str) -> bool:
        if new_status == self.status:
            return True
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, set())


class OrderStatusLog(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='status_logs',
        on_delete=models.CASCADE,
        verbose_name="Đơn hàng"
    )
    status = models.CharField(max_length=15, choices=Order.STATUS_CHOICES, verbose_name="Trạng thái")
    changed_by = models.CharField(max_length=150, default='Hệ thống', verbose_name="Người thực hiện")
    note = models.CharField(max_length=255, blank=True, verbose_name="Ghi chú")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian")

    class Meta:
        ordering = ['created']
        verbose_name = 'Lịch sử trạng thái đơn'
        verbose_name_plural = 'Lịch sử trạng thái đơn'

    def __str__(self):
        return f"#DH{self.order_id} -> {self.status} ({self.changed_by})"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE,
        verbose_name="Đơn hàng"
    )
    product = models.ForeignKey(
        Product,
        related_name='order_items',
        on_delete=models.CASCADE,
        verbose_name="Sản phẩm"
    )
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Đơn giá")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Số lượng")

    class Meta:
        verbose_name = 'Chi tiết món hàng'
        verbose_name_plural = 'Chi tiết các món hàng'

    def __str__(self):
        return f'{self.product.name} (x{self.quantity})'

    def get_cost(self):
        return self.price * self.quantity
