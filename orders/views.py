import re
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.db.models import Q
from cart.cart import Cart
from cart.forms import CouponApplyForm
from .models import Order, OrderItem
from .forms import OrderCreateForm


def order_create(request):
    cart = Cart(request)
    if len(cart) == 0:
        return redirect('shop:product_list')

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                if cart.coupon:
                    order.coupon = cart.coupon
                    order.discount_percent = cart.coupon.discount_percent
                    order.discount_amount = cart.get_discount()
                order.total_amount = cart.get_total_price_after_discount()
                order.save()

                for item in cart:
                    product = item['product']
                    qty = item['quantity']
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        price=item['price'],
                        quantity=qty
                    )
                    # Trừ số lượng tồn kho (stock) của Product
                    if product.stock >= qty:
                        product.stock -= qty
                    else:
                        product.stock = 0

                    if product.stock == 0:
                        product.available = False
                    product.save()

                # Xóa sạch giỏ hàng và mã giảm giá sau khi đặt thành công
                cart.clear()

            return redirect('orders:order_success', order_id=order.id)
    else:
        form = OrderCreateForm()

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


def order_success(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), id=order_id)
    vietqr_url = (
        f"https://img.vietqr.io/image/MB-0123456789-compact2.png"
        f"?amount={int(order.total_amount)}&addInfo=WHEYSTORE%20DH{order.id}&accountName=WHEYSTORE"
    )
    return render(
        request,
        'orders/success.html',
        {
            'order': order,
            'vietqr_url': vietqr_url,
        }
    )


def order_detail_and_lookup(request, order_id=None):
    """
    Hỗ trợ cả xem chi tiết xác nhận đơn hàng (nếu có order_id)
    và trang tra cứu đơn hàng theo Số điện thoại hoặc Mã đơn hàng (#ID).
    """
    if order_id is not None:
        return order_success(request, order_id=order_id)

    query = request.GET.get('q', '').strip()
    orders = []

    if query:
        cleaned_id_match = re.sub(r'^(#|dh|wheystore\s*dh)\s*', '', query, flags=re.IGNORECASE).strip()
        q_filter = Q(phone__icontains=query)
        if cleaned_id_match.isdigit():
            q_filter |= Q(id=int(cleaned_id_match))
        orders = Order.objects.prefetch_related('items__product').filter(q_filter).order_by('-created')

    return render(
        request,
        'orders/track.html',
        {
            'query': query,
            'orders': orders,
        }
    )
