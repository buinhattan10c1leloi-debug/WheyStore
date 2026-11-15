from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from shop.models import Product


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã giảm giá (Coupon)")
    discount_percent = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        default=10,
        verbose_name="Phần trăm giảm giá (%)"
    )
    active = models.BooleanField(default=True, verbose_name="Đang kích hoạt")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")

    class Meta:
        ordering = ['-discount_percent']
        verbose_name = 'Mã giảm giá (Coupon)'
        verbose_name_plural = 'Mã giảm giá (Coupons)'

    def __str__(self):
        return f"{self.code} (-{self.discount_percent}%)"


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
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Tổng thanh toán (VNĐ)"
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
        amount_int = int(self.total_amount)
        return (
            f"https://img.vietqr.io/image/MB-0123456789-compact2.png"
            f"?amount={amount_int}&addInfo=WHEYSTORE%20DH{self.id}&accountName=WHEYSTORE"
        )


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
