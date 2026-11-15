import re
from django.conf import settings
from django.db import models
from django.db.models import Avg, Count
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator


def _extract_number(text, default=0.0):
    if not text:
        return default
    match = re.search(r'(\d+(?:\.\d+)?)', str(text))
    return float(match.group(1)) if match else default


class Category(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="Tên danh mục")
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Danh mục'
        verbose_name_plural = 'Danh mục'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:product_list_by_category', args=[self.slug])


class Product(models.Model):
    GOAL_CHOICES = (
        ('lean_bulk', 'Tăng cơ nạc'),
        ('cutting', 'Giảm mỡ / Siết cơ'),
        ('mass_gain', 'Tăng cân / Tăng cơ'),
        ('strength', 'Sức mạnh & Phục hồi'),
    )
    category = models.ForeignKey(
        Category,
        related_name='products',
        on_delete=models.CASCADE,
        verbose_name="Danh mục"
    )
    name = models.CharField(max_length=255, verbose_name="Tên sản phẩm")
    slug = models.SlugField(max_length=255)
    brand = models.CharField(max_length=100, blank=True, default='', verbose_name="Thương hiệu")
    goal = models.CharField(max_length=20, choices=GOAL_CHOICES, default='lean_bulk', verbose_name="Mục tiêu tập luyện")
    image = models.ImageField(upload_to='products/%Y/%m/%d', blank=True, null=True, verbose_name="Ảnh sản phẩm")
    description = models.TextField(blank=True, verbose_name="Mô tả")
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Giá bán (VNĐ)")
    old_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Giá gốc trước khi giảm (VNĐ)"
    )
    weight = models.CharField(max_length=50, blank=True, verbose_name="Trọng lượng (VD: 5lbs)")
    servings = models.CharField(max_length=50, blank=True, default='', verbose_name="Số lần dùng (VD: 76 Servings)")
    protein_per_serving = models.CharField(max_length=50, blank=True, default='25g', verbose_name="Protein / Serving")
    bcaa_per_serving = models.CharField(max_length=50, blank=True, default='5.5g', verbose_name="BCAA / Hoạt chất")
    calories = models.CharField(max_length=50, blank=True, default='110 kcal', verbose_name="Calories / Serving")
    sugar = models.CharField(max_length=50, blank=True, default='0g', verbose_name="Đường (Sugar)")
    flavor = models.CharField(max_length=100, blank=True, verbose_name="Hương vị (VD: Chocolate)")
    origin = models.CharField(max_length=50, blank=True, default='USA', verbose_name="Xuất xứ")
    free_gift = models.CharField(
        max_length=150,
        blank=True,
        default='Tặng Bình Lắc Shaker + Freeship',
        verbose_name="Quà tặng kèm"
    )
    stock = models.PositiveIntegerField(default=0, verbose_name="Số lượng trong kho")
    available = models.BooleanField(default=True, verbose_name="Đang bán")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated = models.DateTimeField(auto_now=True, verbose_name="Ngày cập nhật")

    class Meta:
        ordering = ['-created']
        indexes = [
            models.Index(fields=['id', 'slug']),
            models.Index(fields=['name']),
            models.Index(fields=['brand']),
            models.Index(fields=['price']),
            models.Index(fields=['-created']),
        ]
        verbose_name = 'Sản phẩm'
        verbose_name_plural = 'Sản phẩm'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:product_detail', args=[self.id, self.slug])

    @property
    def discount_percent(self):
        if self.old_price and self.old_price > self.price and self.old_price > 0:
            pct = round(float((self.old_price - self.price) / self.old_price * 100))
            return max(1, pct)
        return 0

    @property
    def protein_number(self):
        val = _extract_number(self.protein_per_serving, 0)
        return int(val) if val == int(val) else round(val, 1)

    @property
    def protein_decimals(self):
        val = _extract_number(self.protein_per_serving, 0)
        return 0 if val == int(val) else 1

    @property
    def protein_progress(self):
        val = _extract_number(self.protein_per_serving, 0)
        if val <= 0:
            return 0.08
        return round(min(0.98, max(0.25, val / 30.0)), 2)

    @property
    def bcaa_number(self):
        val = _extract_number(self.bcaa_per_serving, 0)
        return int(val) if val == int(val) else round(val, 1)

    @property
    def bcaa_decimals(self):
        val = _extract_number(self.bcaa_per_serving, 0)
        return 0 if val == int(val) else 1

    @property
    def bcaa_label_suffix(self):
        raw = (self.bcaa_per_serving or '').strip()
        cleaned = re.sub(r'^\d+(?:\.\d+)?\s*', '', raw)
        return cleaned if cleaned else 'g'

    @property
    def bcaa_progress(self):
        val = _extract_number(self.bcaa_per_serving, 0)
        if val <= 0:
            return 0.1
        return round(min(0.96, max(0.35, val / 7.0)), 2)

    @property
    def calories_number(self):
        val = _extract_number(self.calories, 0)
        return int(val)

    @property
    def calories_progress(self):
        val = _extract_number(self.calories, 0)
        if val <= 0:
            return 0.06
        if val > 300:
            return 0.96
        return round(min(0.92, max(0.2, val / 220.0)), 2)

    @property
    def sugar_number(self):
        val = _extract_number(self.sugar, 0)
        return int(val) if val == int(val) else round(val, 1)

    @property
    def sugar_progress(self):
        val = _extract_number(self.sugar, 0)
        if val <= 0:
            return 0.06
        return round(min(0.85, max(0.12, val / 20.0)), 2)

    @property
    def average_rating(self):
        annotated = getattr(self, 'annotated_avg_rating', None)
        if annotated is not None:
            return round(float(annotated), 1)
        avg = self.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating']
        return round(avg, 1) if avg else 0.0

    @property
    def review_count(self):
        annotated = getattr(self, 'annotated_review_count', None)
        if annotated is not None:
            return int(annotated)
        return self.reviews.count()

    @property
    def price_per_serving(self):
        servs = _extract_number(self.servings, 0)
        if servs <= 0:
            return None
        return round(float(self.price) / servs)


class Bundle(models.Model):
    name = models.CharField(max_length=200, verbose_name="Tên Combo")
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True, verbose_name="Mô tả combo")
    products = models.ManyToManyField(Product, related_name='bundles', verbose_name="Sản phẩm trong combo")
    bundle_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Giá Combo (VNĐ)")
    active = models.BooleanField(default=True, verbose_name="Đang bán")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created']
        verbose_name = 'Combo sản phẩm'
        verbose_name_plural = 'Combo sản phẩm'

    def __str__(self):
        return self.name

    @property
    def original_total_price(self):
        return sum(p.price for p in self.products.all())

    @property
    def savings_amount(self):
        diff = self.original_total_price - self.bundle_price
        return diff if diff > 0 else 0


class WishlistItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='wishlist_items',
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        related_name='wishlisted_by',
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']
        verbose_name = 'Sản phẩm yêu thích'
        verbose_name_plural = 'Sản phẩm yêu thích'

    def __str__(self):
        return f"{self.user} - {self.product.name}"


class Post(models.Model):
    title = models.CharField(max_length=255, verbose_name="Tiêu đề bài viết")
    slug = models.SlugField(max_length=255, unique=True)
    cover_image = models.ImageField(upload_to='blog/%Y/%m/%d', blank=True, null=True, verbose_name="Ảnh bìa")
    excerpt = models.TextField(blank=True, verbose_name="Tóm tắt ngắn")
    content = models.TextField(verbose_name="Nội dung bài viết")
    meta_title = models.CharField(max_length=255, blank=True, verbose_name="SEO Title")
    meta_description = models.CharField(max_length=320, blank=True, verbose_name="SEO Description")
    related_products = models.ManyToManyField(Product, blank=True, related_name='blog_posts', verbose_name="Sản phẩm liên kết")
    published = models.BooleanField(default=True, verbose_name="Xuất bản")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Bài viết kiến thức'
        verbose_name_plural = 'Bài viết kiến thức'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('shop:blog_detail', args=[self.slug])


class Review(models.Model):
    RATING_CHOICES = [(i, f'{i} Sao') for i in range(1, 6)]

    product = models.ForeignKey(
        Product,
        related_name='reviews',
        on_delete=models.CASCADE,
        verbose_name="Sản phẩm"
    )
    user_name = models.CharField(max_length=100, verbose_name="Tên khách hàng")
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Đánh giá (1-5 sao)"
    )
    comment = models.TextField(verbose_name="Nhận xét chi tiết")
    verified_purchase = models.BooleanField(default=False, verbose_name="Đã mua hàng xác thực")
    created = models.DateTimeField(auto_now_add=True, verbose_name="Ngày đánh giá")

    class Meta:
        ordering = ['-created']
        verbose_name = 'Đánh giá sản phẩm'
        verbose_name_plural = 'Đánh giá sản phẩm'

    def __str__(self):
        return f'{self.user_name} ({self.rating}*) - {self.product.name}'
