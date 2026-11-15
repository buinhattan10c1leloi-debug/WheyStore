import csv
import json
import logging
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum, Avg, Count
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.core.cache import cache
from .models import Category, Product, Bundle, WishlistItem, Post
from .forms import ReviewForm
from cart.cart import Cart
from cart.forms import CartAddProductForm
from orders.models import Order, OrderItem, OrderStatusLog, Coupon

logger = logging.getLogger('shop')


@receiver(user_logged_in)
def sync_session_wishlist_on_login(sender, request, user, **kwargs):
    """Đồng bộ danh sách yêu thích từ session vào tài khoản khi người dùng đăng nhập."""
    session_ids = request.session.get('wishlist', [])
    if not session_ids:
        return
    for pid in session_ids:
        prod = Product.objects.filter(id=pid, available=True).first()
        if prod:
            WishlistItem.objects.get_or_create(user=user, product=prod)
    request.session['wishlist'] = []
    request.session.modified = True


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = (
        Product.objects.filter(available=True)
        .select_related('category')
        .annotate(
            annotated_avg_rating=Avg('reviews__rating'),
            annotated_review_count=Count('reviews')
        )
    )

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    # Server-side Search, Price Filter, Advanced Filters & Sort
    search_query = request.GET.get('q', '').strip()
    price_range = request.GET.get('price', 'all')
    sort_by = request.GET.get('sort', 'newest')
    selected_brand = request.GET.get('brand', '').strip()
    selected_flavor = request.GET.get('flavor', '').strip()
    selected_goal = request.GET.get('goal', '').strip()
    in_stock_only = request.GET.get('in_stock', '') == '1'

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(flavor__icontains=search_query) |
            Q(origin__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    if selected_brand:
        products = products.filter(brand__iexact=selected_brand)
    if selected_flavor:
        products = products.filter(flavor__icontains=selected_flavor)
    if selected_goal:
        products = products.filter(goal=selected_goal)
    if in_stock_only:
        products = products.filter(stock__gt=0)

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

    paginator = Paginator(products, 12)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Prepare product catalog JSON for the Fitness Macro Calculator recommendations
    all_available = (
        Product.objects.filter(available=True)
        .select_related('category')
        .annotate(
            annotated_avg_rating=Avg('reviews__rating'),
            annotated_review_count=Count('reviews')
        )
    )
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

    bundles = Bundle.objects.filter(active=True).prefetch_related('products')[:4]
    brands = (
        Product.objects.filter(available=True)
        .exclude(brand='')
        .values_list('brand', flat=True)
        .distinct()
        .order_by('brand')
    )
    if request.user.is_authenticated:
        wishlist_ids = set(WishlistItem.objects.filter(user=request.user).values_list('product_id', flat=True))
    else:
        wishlist_ids = set(request.session.get('wishlist', []))
    compare_ids = set(request.session.get('compare', []))

    cart_product_form = CartAddProductForm()
    return render(
        request,
        'shop/product/list.html',
        {
            'category': category,
            'categories': categories,
            'products': page_obj,
            'page_obj': page_obj,
            'cart_product_form': cart_product_form,
            'search_query': search_query,
            'price_range': price_range,
            'sort_by': sort_by,
            'selected_brand': selected_brand,
            'selected_flavor': selected_flavor,
            'selected_goal': selected_goal,
            'in_stock_only': in_stock_only,
            'brands': brands,
            'goal_choices': Product.GOAL_CHOICES,
            'bundles': bundles,
            'wishlist_ids': wishlist_ids,
            'compare_ids': compare_ids,
            'calc_catalog_json': json.dumps(calc_catalog, ensure_ascii=False),
        }
    )


def search_suggest_api(request):
    """API nhẹ trả về JSON gợi ý sản phẩm theo từ khóa q."""
    q = request.GET.get('q', '').strip()
    if len(q) < 1:
        return JsonResponse({'results': []})
    matches = (
        Product.objects.filter(available=True)
        .filter(Q(name__icontains=q) | Q(brand__icontains=q) | Q(flavor__icontains=q))
        .only('id', 'name', 'slug', 'brand', 'price', 'image')[:6]
    )
    results = [
        {
            'id': p.id,
            'name': p.name,
            'brand': p.brand,
            'price': int(p.price),
            'price_formatted': f"{int(p.price):,}".replace(",", ".") + "đ",
            'url': p.get_absolute_url(),
            'image_url': p.image.url if p.image else '',
        }
        for p in matches
    ]
    return JsonResponse({'results': results})


def product_detail(request, id, slug):
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('reviews'),
        id=id,
        slug=slug,
        available=True
    )
    reviews = product.reviews.all()

    if request.method == 'POST' and 'submit_review' in request.POST:
        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', '127.0.0.1')
        rl_key = f"review_rl_{ip}_{product.id}"
        if cache.get(rl_key):
            messages.error(request, "Bạn vừa gửi đánh giá cho sản phẩm này. Vui lòng đợi ít phút trước khi gửi lại.")
            return redirect(product.get_absolute_url())

        review_form = ReviewForm(request.POST)
        if review_form.is_valid():
            new_review = review_form.save(commit=False)
            new_review.product = product
            # Chỉ đánh dấu verified_purchase=True nếu thực sự có đơn COMPLETED mua sản phẩm này
            has_completed_purchase = OrderItem.objects.filter(
                product=product,
                order__status='COMPLETED',
                order__full_name__iexact=new_review.user_name.strip()
            ).exists()
            new_review.verified_purchase = has_completed_purchase
            new_review.save()
            cache.set(rl_key, True, timeout=300)
            messages.success(
                request,
                f"Cảm ơn {new_review.user_name}! Đánh giá {new_review.rating} sao của bạn đã được ghi nhận."
            )
            return redirect(product.get_absolute_url())
    else:
        review_form = ReviewForm()

    # Đã xem gần đây (session) & Sản phẩm liên quan
    recent_ids = request.session.get('recently_viewed', [])
    recent_ids = [pid for pid in recent_ids if pid != product.id][:5]
    recently_viewed_products = list(
        Product.objects.filter(id__in=recent_ids, available=True)
        .annotate(annotated_avg_rating=Avg('reviews__rating'), annotated_review_count=Count('reviews'))
    )
    recently_viewed_products.sort(key=lambda p: recent_ids.index(p.id) if p.id in recent_ids else 999)
    request.session['recently_viewed'] = [product.id] + recent_ids
    request.session.modified = True

    related_products = (
        Product.objects.filter(available=True)
        .filter(Q(category=product.category) | Q(brand=product.brand))
        .exclude(id=product.id)
        .annotate(annotated_avg_rating=Avg('reviews__rating'), annotated_review_count=Count('reviews'))[:4]
    )

    if request.user.is_authenticated:
        in_wishlist = WishlistItem.objects.filter(user=request.user, product=product).exists()
    else:
        in_wishlist = product.id in request.session.get('wishlist', [])
    in_compare = product.id in request.session.get('compare', [])

    cart_product_form = CartAddProductForm()
    return render(
        request,
        'shop/product/detail.html',
        {
            'product': product,
            'cart_product_form': cart_product_form,
            'reviews': reviews,
            'review_form': review_form,
            'recently_viewed_products': recently_viewed_products[:4],
            'related_products': related_products,
            'in_wishlist': in_wishlist,
            'in_compare': in_compare,
        }
    )


@require_POST
def bundle_add_to_cart(request, bundle_id):
    bundle = get_object_or_404(Bundle.objects.prefetch_related('products'), id=bundle_id, active=True)
    products = list(bundle.products.all())
    if not products:
        messages.error(request, "Combo này hiện chưa có sản phẩm.")
        return redirect('shop:product_list')

    cart = Cart(request)
    for prod in products:
        current_qty = cart.cart.get(str(prod.id), {}).get('quantity', 0)
        if not prod.available or prod.stock < current_qty + 1:
            messages.error(
                request,
                f"Không thể thêm combo '{bundle.name}': sản phẩm '{prod.name}' không đủ tồn kho."
            )
            return redirect('shop:product_list')

    for prod in products:
        cart.add(product=prod, quantity=1, override_quantity=False)

    messages.success(request, f"Đã thêm toàn bộ combo '{bundle.name}' vào giỏ hàng!")
    return redirect('cart:cart_detail')


@require_POST
def wishlist_toggle(request, product_id):
    product = get_object_or_404(Product, id=product_id, available=True)
    added = False
    if request.user.is_authenticated:
        obj, created = WishlistItem.objects.get_or_create(user=request.user, product=product)
        if not created:
            obj.delete()
        else:
            added = True
    else:
        wlist = request.session.get('wishlist', [])
        if product.id in wlist:
            wlist.remove(product.id)
        else:
            wlist.append(product.id)
            added = True
        request.session['wishlist'] = wlist
        request.session.modified = True

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'added': added})

    messages.success(
        request,
        f"Đã {'thêm' if added else 'gỡ'} '{product.name}' {'vào' if added else 'khỏi'} danh sách yêu thích."
    )
    next_url = request.POST.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(next_url)
    return redirect('shop:wishlist')


def wishlist_view(request):
    if request.user.is_authenticated:
        products = Product.objects.filter(
            wishlisted_by__user=request.user, available=True
        ).annotate(annotated_avg_rating=Avg('reviews__rating'), annotated_review_count=Count('reviews'))
    else:
        ids = request.session.get('wishlist', [])
        products = Product.objects.filter(
            id__in=ids, available=True
        ).annotate(annotated_avg_rating=Avg('reviews__rating'), annotated_review_count=Count('reviews'))
    return render(request, 'shop/wishlist.html', {'products': products})


@require_POST
def compare_toggle(request, product_id):
    product = get_object_or_404(Product, id=product_id, available=True)
    clist = request.session.get('compare', [])
    if product.id in clist:
        clist.remove(product.id)
        messages.info(request, f"Đã gỡ '{product.name}' khỏi bảng so sánh.")
    else:
        if len(clist) >= 3:
            messages.warning(request, "Chỉ có thể so sánh tối đa 3 sản phẩm cùng lúc.")
        else:
            clist.append(product.id)
            messages.success(request, f"Đã thêm '{product.name}' vào bảng so sánh ({len(clist)}/3).")
    request.session['compare'] = clist
    request.session.modified = True
    return redirect('shop:compare')


def compare_view(request):
    ids = request.session.get('compare', [])[:3]
    products = list(Product.objects.filter(id__in=ids, available=True))
    return render(request, 'shop/compare.html', {'products': products})


def blog_list(request):
    posts = Post.objects.filter(published=True).prefetch_related('related_products')
    return render(request, 'shop/blog/list.html', {'posts': posts})


def blog_detail(request, slug):
    post = get_object_or_404(Post.objects.prefetch_related('related_products'), slug=slug, published=True)
    return render(request, 'shop/blog/detail.html', {'post': post})


STATIC_PAGES = {
    'gioi-thieu': {
        'title': 'Giới Thiệu WheyStore',
        'subtitle': 'Hệ thống dinh dưỡng thể hình chính hãng hàng đầu Việt Nam',
        'paragraphs': [
            'WheyStore chuyên cung cấp Whey Protein, Mass Gainer, Pre-Workout và Creatine nhập khẩu chính hãng từ USA & EU với đầy đủ tem xác thực.',
            'Sứ mệnh của chúng tôi là giúp cộng đồng Gymer Việt Nam tiếp cận nguồn dinh dưỡng sạch, minh bạch thành phần và giao hàng siêu tốc toàn quốc.',
        ],
    },
    'chinh-sach-doi-tra': {
        'title': 'Chính Sách Đổi Trả & Hoàn Tiền',
        'subtitle': 'Cam kết 100% chính hãng — Đổi trả miễn phí trong 7 ngày',
        'paragraphs': [
            'Sản phẩm được đổi trả miễn phí trong vòng 7 ngày nếu còn nguyên tem niêm phong, hoặc phát hiện lỗi từ nhà sản xuất / hư hỏng do vận chuyển.',
            'Hoàn tiền 200% nếu phát hiện hàng giả, hàng kém chất lượng.',
        ],
    },
    'chinh-sach-bao-mat': {
        'title': 'Chính Sách Bảo Mật Thông Tin',
        'subtitle': 'An toàn dữ liệu khách hàng là ưu tiên số 1 tại WheyStore',
        'paragraphs': [
            'Mọi thông tin cá nhân (Họ tên, SĐT, địa chỉ, lịch sử đơn hàng) chỉ được sử dụng cho mục đích giao hàng, chăm sóc khách hàng và bảo hành sản phẩm.',
            'WheyStore tuyệt đối không chia sẻ hoặc bán dữ liệu khách hàng cho bên thứ ba.',
        ],
    },
}


def static_page(request, page_slug):
    from django.http import Http404
    page = STATIC_PAGES.get(page_slug)
    if not page:
        raise Http404("Trang không tồn tại")
    return render(request, 'shop/pages/static.html', {'page': page})


def contact_page(request):
    from django.conf import settings
    from django.core.mail import send_mail

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        message_text = request.POST.get('message', '').strip()
        if len(name) < 2 or len(message_text) < 5:
            messages.error(request, "Vui lòng nhập đầy đủ họ tên và nội dung liên hệ.")
        else:
            recipient = getattr(settings, 'OWNER_NOTIFY_EMAIL', '') or getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@wheystore.vn')
            send_mail(
                subject=f"[WheyStore Liên Hệ] Từ {name}",
                message=f"Người gửi: {name}\nEmail: {email}\n\nNội dung:\n{message_text}",
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@wheystore.vn'),
                recipient_list=[recipient],
                fail_silently=True,
            )
            messages.success(request, "Cảm ơn bạn! Tin nhắn liên hệ đã được gửi tới đội ngũ WheyStore.")
            return redirect('shop:contact')
    return render(request, 'shop/pages/contact.html')


# ==============================================================================
# Custom Admin Dashboard (/dashboard/) for Store Owner (Staff / Superuser)
# ==============================================================================

def dashboard_login(request):
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')

    ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', '127.0.0.1')
    lock_key = f"dash_login_lock_{ip}"
    fail_key = f"dash_login_fail_{ip}"

    if request.method == 'POST':
        if cache.get(lock_key):
            messages.error(request, "Tài khoản tạm khóa 10 phút do đăng nhập sai quá 5 lần.")
            return render(request, 'shop/dashboard/login.html')

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None and (user.is_staff or user.is_superuser):
            cache.delete(fail_key)
            cache.delete(lock_key)
            login(request, user)
            messages.success(request, f"Chào mừng Quản trị viên {user.username} quay trở lại Dashboard!")
            raw_next = request.POST.get('next') or request.GET.get('next') or ''
            if raw_next and url_has_allowed_host_and_scheme(
                url=raw_next,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(raw_next)
            return redirect('dashboard')
        else:
            fails = cache.get(fail_key, 0) + 1
            cache.set(fail_key, fails, timeout=600)
            if fails >= 5:
                cache.set(lock_key, True, timeout=600)
                messages.error(request, "Bạn đã đăng nhập sai 5 lần. Vui lòng thử lại sau 10 phút.")
            else:
                messages.error(request, "Tài khoản hoặc mật khẩu không đúng, hoặc không có quyền Staff/Superuser.")

    return render(request, 'shop/dashboard/login.html')


@require_POST
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

    # 4. Lọc, phân trang đơn hàng & Top sản phẩm bán chạy
    orders_qs = Order.objects.prefetch_related('items__product', 'status_logs').select_related('coupon').order_by('-created')
    filter_status = request.GET.get('status', '').strip()
    filter_phone = request.GET.get('phone', '').strip()
    filter_date_from = request.GET.get('date_from', '').strip()
    filter_date_to = request.GET.get('date_to', '').strip()

    if filter_status:
        orders_qs = orders_qs.filter(status=filter_status)
    if filter_phone:
        orders_qs = orders_qs.filter(phone__icontains=filter_phone)
    if filter_date_from:
        orders_qs = orders_qs.filter(created__date__gte=filter_date_from)
    if filter_date_to:
        orders_qs = orders_qs.filter(created__date__lte=filter_date_to)

    orders_paginator = Paginator(orders_qs, 10)
    recent_orders = orders_paginator.get_page(request.GET.get('page', 1))

    top_selling_products = (
        OrderItem.objects.exclude(order__status='CANCELLED')
        .values('product__id', 'product__name', 'product__brand')
        .annotate(total_qty=Sum('quantity'), total_rev=Sum('price'))
        .order_by('-total_qty')[:5]
    )

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
            'top_selling_products': top_selling_products,
            'filter_status': filter_status,
            'filter_phone': filter_phone,
            'filter_date_from': filter_date_from,
            'filter_date_to': filter_date_to,
            'all_products': all_products,
            'coupons': coupons,
        }
    )


def dashboard_export_orders_csv(request):
    if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
        return redirect('dashboard_login')

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="wheystore_orders.csv"'
    writer = csv.writer(response)
    writer.writerow(['Mã đơn', 'Khách hàng', 'SĐT', 'Thành phố', 'Thanh toán', 'Trạng thái', 'Phí ship', 'Tổng tiền', 'Ngày đặt'])
    for o in Order.objects.order_by('-created'):
        writer.writerow([
            f'#DH{o.id}',
            o.full_name,
            o.phone,
            o.city,
            o.get_payment_method_display(),
            o.get_status_display(),
            int(o.shipping_fee),
            int(o.total_amount),
            o.created.strftime('%d/%m/%Y %H:%M'),
        ])
    return response


@require_POST
def dashboard_update_order_status(request, order_id):
    if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
        return redirect('dashboard_login')

    new_status = request.POST.get('status', '').strip()
    valid_statuses = dict(Order.STATUS_CHOICES).keys()
    if new_status not in valid_statuses:
        messages.error(request, "Trạng thái đơn hàng không hợp lệ.")
        return redirect('dashboard')

    try:
        with transaction.atomic():
            order = get_object_or_404(
                Order.objects.select_for_update().prefetch_related('items__product'),
                id=order_id
            )
            if not order.can_transition_to(new_status):
                raise ValueError(
                    f"Không thể chuyển trạng thái từ '{order.get_status_display()}' sang '{dict(Order.STATUS_CHOICES)[new_status]}'."
                )

            if new_status == 'CANCELLED' and order.stock_deducted:
                for item in order.items.all():
                    prod = Product.objects.select_for_update().get(id=item.product_id)
                    prod.stock += item.quantity
                    if prod.stock > 0:
                        prod.available = True
                    prod.save()
                order.stock_deducted = False
            elif new_status != 'CANCELLED' and not order.stock_deducted:
                for item in order.items.all():
                    prod = Product.objects.select_for_update().get(id=item.product_id)
                    if prod.stock < item.quantity:
                        raise ValueError(
                            f"Không đủ tồn kho để khôi phục đơn #DH{order.id}: '{prod.name}' chỉ còn {prod.stock}."
                        )
                    prod.stock -= item.quantity
                    if prod.stock == 0:
                        prod.available = False
                    prod.save()
                order.stock_deducted = True

            old_status_display = order.get_status_display()
            order.status = new_status
            order.save()
            OrderStatusLog.objects.create(
                order=order,
                status=new_status,
                changed_by=request.user.username,
                note=f"Đổi trạng thái từ {old_status_display} -> {order.get_status_display()}"
            )
            from orders.notifications import send_order_status_email
            send_order_status_email(order)
            messages.success(
                request,
                f"Đã cập nhật đơn hàng #DH{order.id} ({order.full_name}) sang trạng thái: {order.get_status_display()}!"
            )
    except ValueError as exc:
        messages.error(request, str(exc))

    return redirect('dashboard')


@require_POST
def dashboard_quick_restock(request, product_id):
    if not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
        return redirect('dashboard_login')

    product = get_object_or_404(Product, id=product_id)
    raw_qty = request.POST.get('add_qty', '20')
    try:
        add_qty = int(raw_qty)
    except (TypeError, ValueError):
        messages.error(request, "Số lượng nhập kho phải là số nguyên.")
        return redirect('dashboard')

    if add_qty <= 0 or add_qty > 10000:
        messages.error(request, "Số lượng nhập kho phải từ 1 đến 10.000 hộp.")
        return redirect('dashboard')

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

