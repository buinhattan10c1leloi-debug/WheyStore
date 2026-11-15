import re
import uuid
import logging
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.cache import cache
from django.db import transaction
from django.views.decorators.http import require_POST
from cart.cart import Cart
from cart.forms import CouponApplyForm
from shop.models import Product
from .models import Coupon, Order, OrderItem, OrderStatusLog
from .forms import OrderCreateForm, normalize_vn_phone

logger = logging.getLogger('orders')


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


def order_create(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('shop:product_list')

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            cart_items = list(cart)
            if not cart_items:
                messages.error(request, "Giỏ hàng của bạn hiện đang trống hoặc sản phẩm đã ngừng bán.")
                return redirect('cart:cart_detail')

            try:
                with transaction.atomic():
                    product_ids = [item['product'].id for item in cart_items]
                    locked_products = {
                        p.id: p
                        for p in Product.objects.select_for_update().filter(id__in=product_ids)
                    }

                    subtotal = Decimal(0)
                    for item in cart_items:
                        prod = locked_products.get(item['product'].id)
                        qty = item['quantity']
                        if not prod or not prod.available:
                            raise ValueError(f"Sản phẩm '{item['product'].name}' hiện đã ngừng kinh doanh.")
                        if prod.stock < qty:
                            raise ValueError(
                                f"Sản phẩm '{prod.name}' chỉ còn {prod.stock} hộp trong kho (bạn đặt {qty})."
                            )
                        subtotal += prod.price * qty

                    order = form.save(commit=False)
                    if request.user.is_authenticated:
                        order.user = request.user

                    discount_amount = Decimal(0)
                    if cart.coupon_id:
                        locked_coupon = Coupon.objects.select_for_update().filter(id=cart.coupon_id).first()
                        if locked_coupon:
                            ok, err_msg = locked_coupon.validate_for_order(subtotal)
                            if not ok:
                                raise ValueError(err_msg)
                            order.coupon = locked_coupon
                            order.discount_percent = locked_coupon.discount_percent
                            discount_amount = (Decimal(locked_coupon.discount_percent) / Decimal(100)) * subtotal
                            order.discount_amount = discount_amount
                            locked_coupon.used_count += 1
                            locked_coupon.save(update_fields=['used_count'])

                    after_discount = max(Decimal(0), subtotal - discount_amount)
                    shipping_fee = cart.get_shipping_fee()
                    order.shipping_fee = shipping_fee
                    order.total_amount = after_discount + shipping_fee
                    order.stock_deducted = True
                    order.save()

                    for item in cart_items:
                        prod = locked_products[item['product'].id]
                        qty = item['quantity']
                        OrderItem.objects.create(
                            order=order,
                            product=prod,
                            price=prod.price,
                            quantity=qty
                        )
                        prod.stock -= qty
                        if prod.stock == 0:
                            prod.available = False
                        prod.save()

                    OrderStatusLog.objects.create(
                        order=order,
                        status='PENDING',
                        changed_by=request.user.username if request.user.is_authenticated else 'Khách hàng',
                        note='Đơn hàng mới được tạo thành công.'
                    )

                    cart.clear()
                    logger.info("Order #DH%s created successfully (total=%s)", order.id, order.total_amount)
            except ValueError as exc:
                logger.warning("Order creation rejected: %s", exc)
                messages.error(request, str(exc))
                return redirect('cart:cart_detail')
            except Exception as exc:
                logger.exception("Unexpected error during order creation: %s", exc)
                messages.error(request, "Có lỗi xảy ra khi xử lý đơn hàng. Vui lòng thử lại.")
                return redirect('cart:cart_detail')

            recent_ids = request.session.get('recent_order_ids', [])
            recent_ids.append(order.id)
            request.session['recent_order_ids'] = recent_ids[-10:]

            return redirect('orders:order_success', order_token=order.access_token)
    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data['full_name'] = request.user.get_full_name() or request.user.username
            initial_data['email'] = request.user.email
        form = OrderCreateForm(initial=initial_data)

    coupon_apply_form = CouponApplyForm()
    return render(
        request,
        'orders/create.html',
        {
            'cart': cart,
            'form': form,
            'coupon_apply_form': coupon_apply_form,
        }
    )


def order_success(request, order_token):
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product', 'status_logs'),
        access_token=order_token
    )
    return render(
        request,
        'orders/success.html',
        {
            'order': order,
            'vietqr_url': order.vietqr_url,
        }
    )


def order_detail_and_lookup(request, order_token=None):
    if order_token is not None:
        return order_success(request, order_token=order_token)

    query_id = request.GET.get('q', '').strip()
    query_phone = request.GET.get('phone', '').strip()
    orders = []
    rate_limited = False

    if query_id or query_phone:
        ip = _get_client_ip(request)
        cache_key = f"order_track_rl_{ip}"
        attempts = cache.get(cache_key, 0)
        if attempts >= 15:
            rate_limited = True
            messages.error(request, "Bạn đã tra cứu quá nhiều lần. Vui lòng thử lại sau 1 phút.")
        else:
            cache.set(cache_key, attempts + 1, timeout=60)
            try:
                token_uuid = uuid.UUID(query_id)
                orders = list(
                    Order.objects.prefetch_related('items__product', 'status_logs')
                    .filter(access_token=token_uuid)
                )
            except ValueError:
                cleaned_id = re.sub(r'^(#|dh|wheystore\s*dh)\s*', '', query_id, flags=re.IGNORECASE).strip()
                norm_phone = normalize_vn_phone(query_phone)
                if cleaned_id.isdigit() and norm_phone:
                    orders = list(
                        Order.objects.prefetch_related('items__product', 'status_logs')
                        .filter(id=int(cleaned_id), phone=norm_phone)
                        .order_by('-created')
                    )
                elif query_id and not query_phone:
                    messages.warning(
                        request,
                        "Vui lòng nhập đầy đủ cả Mã đơn hàng và Số điện thoại đặt hàng để bảo mật thông tin."
                    )

    return render(
        request,
        'orders/track.html',
        {
            'query': query_id,
            'phone': query_phone,
            'orders': orders,
            'rate_limited': rate_limited,
        }
    )


def customer_register(request):
    if request.user.is_authenticated:
        return redirect('orders:my_orders')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Đăng ký tài khoản '{user.username}' thành công!")
            return redirect('shop:product_list')
    else:
        form = UserCreationForm()
    return render(request, 'orders/auth_register.html', {'form': form})


def customer_login(request):
    if request.user.is_authenticated:
        return redirect('orders:my_orders')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Chào mừng {user.username} quay trở lại WheyStore!")
            return redirect('orders:my_orders')
    else:
        form = AuthenticationForm()
    return render(request, 'orders/auth_login.html', {'form': form})


@require_POST
def customer_logout(request):
    logout(request)
    messages.info(request, "Bạn đã đăng xuất tài khoản.")
    return redirect('shop:product_list')


@login_required(login_url='/orders/accounts/login/')
def my_orders(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product', 'status_logs').order_by('-created')
    return render(request, 'orders/my_orders.html', {'orders': orders})
