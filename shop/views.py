import json
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_POST
from django.db.models import Q, Sum
from django.urls import reverse
from django.utils import timezone
from .models import Category, Product
from .forms import ReviewForm
from cart.forms import CartAddProductForm
from orders.models import Order, Coupon


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True).select_related('category').prefetch_related('reviews')

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    # Server-side Search, Price Filter & Sort (also works with live GSAP client-side filter)
    search_query = request.GET.get('q', '').strip()
    price_range = request.GET.get('price', 'all')
    sort_by = request.GET.get('sort', 'newest')

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(flavor__icontains=search_query) |
            Q(origin__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    if price_range == 'under_1m':
        products = products.filter(price__lt=1000000)
    elif price_range == '1m_to_1_8m':
        products = products.filter(price__gte=1000000, price__lte=2000000)
    elif price_range == 'over_1_8m':
        products = products.filter(price__gt=2000000)

    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    else:
        products = products.order_by('-created')

    # Prepare product catalog JSON for the Fitness Macro Calculator recommendations
    all_available = Product.objects.filter(available=True).select_related('category').prefetch_related('reviews')
    calc_catalog = []
    for p in all_available:
        calc_catalog.append({
            'id': p.id,
            'name': p.name,
            'brand': p.brand or 'WheyStore',
            'origin': p.origin or 'USA',
            'category': p.category.name,
            'category_slug': p.category.slug,
            'price': int(p.price),
            'price_formatted': f"{int(p.price):,}".replace(",", "."),
            'old_price': int(p.old_price) if p.old_price else 0,
            'old_price_formatted': f"{int(p.old_price):,}".replace(",", ".") if p.old_price else '',
            'discount_percent': p.discount_percent,
            'weight': p.weight or '5lbs',
            'servings': p.servings or '70 Servings',
            'protein_per_serving': p.protein_per_serving or '25g',
            'bcaa_per_serving': p.bcaa_per_serving or '5.5g',
            'calories': p.calories or '110 kcal',
            'flavor': p.flavor or 'Tiêu chuẩn',
            'free_gift': p.free_gift or 'Tặng Bình Lắc Shaker + Freeship',
            'url': p.get_absolute_url(),
            'add_cart_url': reverse('cart:cart_add', args=[p.id]),
            'image_url': p.image.url if p.image else '',
            'rating': p.average_rating,
            'review_count': p.review_count,
        })

    cart_product_form = CartAddProductForm()
    return render(
        request,
        'shop/product/list.html',
        {
            'category': category,
            'categories': categories,
            'products': products,
            'cart_product_form': cart_product_form,
            'search_query': search_query,
            'price_range': price_range,
            'sort_by': sort_by,
            'calc_catalog_json': json.dumps(calc_catalog, ensure_ascii=False),
        }
    )


def product_detail(request, id, slug):
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('reviews'),
        id=id,
        slug=slug,
        available=True
    )
    reviews = product.reviews.all()

    if request.method == 'POST' and 'submit_review' in request.POST:
        review_form = ReviewForm(request.POST)
        if review_form.is_valid():
            new_review = review_form.save(commit=False)
            new_review.product = product
            new_review.verified_purchase = True
            new_review.save()
            messages.success(
                request,
                f"Cảm ơn {new_review.user_name}! Đánh giá {new_review.rating} sao của bạn đã được ghi nhận."
            )
            return redirect(product.get_absolute_url())
    else:
        review_form = ReviewForm()

    cart_product_form = CartAddProductForm()
    return render(
        request,
        'shop/product/detail.html',
        {
            'product': product,
            'cart_product_form': cart_product_form,
            'reviews': reviews,
            'review_form': review_form,
        }
    )


# ==============================================================================
# Custom Admin Dashboard (/dashboard/) for Store Owner (Staff / Superuser)
# ==============================================================================

def dashboard_login(request):
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None and (user.is_staff or user.is_superuser):
            login(request, user)
            messages.success(request, f"Chào mừng Quản trị viên {user.username} quay trở lại Dashboard!")
            next_url = request.GET.get('next') or 'dashboard'
            return redirect(next_url)
        else:
            messages.error(request, "Tài khoản hoặc mật khẩu không đúng, hoặc không có quyền Staff/Superuser.")

    return render(request, 'shop/dashboard/login.html')


def dashboard_logout(request):
    logout(request)
    messages.info(request, "Đã đăng xuất khỏi phiên Quản trị viên.")
    return redirect('dashboard_login')


def admin_dashboard(request):
    if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
        return redirect(f"{reverse('dashboard_login')}?next={request.path}")

    # 1. Overview KPI Metrics
    valid_orders = Order.objects.exclude(status='CANCELLED')
    total_revenue = int(valid_orders.aggregate(total=Sum('total_amount'))['total'] or 0)
    pending_orders_count = Order.objects.filter(status='PENDING').count()
    total_orders_count = Order.objects.count()
    active_products_count = Product.objects.filter(available=True).count()
    low_stock_products = Product.objects.filter(stock__lte=5).select_related('category').order_by('stock')
    low_stock_count = low_stock_products.count()

    # 2. Chart.js Data: Revenue over Last 7 Days
    today = timezone.localdate()
    revenue_labels = []
    revenue_values = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_rev = valid_orders.filter(created__date=day).aggregate(s=Sum('total_amount'))['s'] or 0
        revenue_labels.append(day.strftime('%d/%m'))
        revenue_values.append(int(day_rev))

    # 3. Chart.js Data: Payment Method Ratio (COD vs BANK VietQR)
    cod_count = Order.objects.filter(payment_method='COD').count()
    bank_count = Order.objects.filter(payment_method='BANK').count()

    # 4. Recent Orders & All Products for Quick Management
    recent_orders = Order.objects.prefetch_related('items__product').select_related('coupon').order_by('-created')[:20]
    all_products = Product.objects.select_related('category').order_by('stock')
    coupons = Coupon.objects.all()

    return render(
        request,
        'shop/dashboard/index.html',
        {
            'total_revenue': total_revenue,
            'pending_orders_count': pending_orders_count,
            'total_orders_count': total_orders_count,
            'active_products_count': active_products_count,
            'low_stock_products': low_stock_products,
            'low_stock_count': low_stock_count,
            'revenue_labels_json': json.dumps(revenue_labels),
            'revenue_values_json': json.dumps(revenue_values),
            'cod_count': cod_count,
            'bank_count': bank_count,
            'recent_orders': recent_orders,
            'all_products': all_products,
            'coupons': coupons,
        }
    )


@require_POST
def dashboard_update_order_status(request, order_id):
    if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
        return redirect('dashboard_login')

    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status', '').strip()
    valid_statuses = dict(Order.STATUS_CHOICES).keys()

    if new_status in valid_statuses:
        order.status = new_status
        order.save()
        messages.success(
            request,
            f"Đã cập nhật đơn hàng #DH{order.id} ({order.full_name}) sang trạng thái: {order.get_status_display()}!"
        )
    return redirect('dashboard')


@require_POST
def dashboard_quick_restock(request, product_id):
    if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
        return redirect('dashboard_login')

    product = get_object_or_404(Product, id=product_id)
    add_qty = int(request.POST.get('add_qty', 20))
    product.stock += add_qty
    if product.stock > 0:
        product.available = True
    product.save()
    messages.success(
        request,
        f"Đã nhập thêm +{add_qty} hộp cho '{product.name}'. Tồn kho mới: {product.stock} hộp!"
    )
    return redirect('dashboard')


def robots_txt(request):
    """
    Serve robots.txt following claude-seo technical crawlability & AI crawler standards.
    """
    sitemap_url = f"{request.scheme}://{request.get_host()}/sitemap.xml"
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /dashboard/",
        "Disallow: /cart/",
        "Disallow: /orders/create/",
        "",
        "# Allow Search & AI Answer Engine Crawlers (Googlebot, OAI-SearchBot, Claude-SearchBot, PerplexityBot)",
        "User-agent: Googlebot",
        "Allow: /",
        "User-agent: OAI-SearchBot",
        "Allow: /",
        "User-agent: Claude-SearchBot",
        "Allow: /",
        "User-agent: PerplexityBot",
        "Allow: /",
        "",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")

