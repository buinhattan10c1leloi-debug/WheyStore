from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from shop.models import Product
from orders.models import Coupon
from .cart import Cart
from .forms import CartAddProductForm, CouponApplyForm


def _get_safe_next_url(request, default_url_name='cart:cart_detail'):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return default_url_name


def _is_ajax(request):
    return (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('Accept', '')
    )


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    is_ajax = _is_ajax(request)

    if not product.available or product.stock <= 0:
        err = f"Sản phẩm '{product.name}' hiện đã hết hàng hoặc ngừng kinh doanh."
        if is_ajax:
            return JsonResponse({'ok': False, 'message': err}, status=400)
        messages.error(request, err)
        return redirect('shop:product_list')

    form = CartAddProductForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        ok, err_msg = cart.add(
            product=product,
            quantity=cd['quantity'],
            override_quantity=cd['override']
        )
        if not ok and err_msg:
            if is_ajax:
                return JsonResponse({'ok': False, 'message': err_msg}, status=400)
            messages.error(request, err_msg)
        elif is_ajax:
            total_val = int(cart.get_total_price_after_discount())
            return JsonResponse({
                'ok': True,
                'message': f"Đã thêm '{product.name}' vào giỏ hàng!",
                'cart_count': len(cart),
                'cart_total': total_val,
                'cart_total_formatted': f"{total_val:,}".replace(",", ".") + "đ",
            })
    else:
        err = "Số lượng sản phẩm không hợp lệ."
        if is_ajax:
            return JsonResponse({'ok': False, 'message': err}, status=400)
        messages.error(request, err)
    return redirect('cart:cart_detail')


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('cart:cart_detail')


@require_POST
def coupon_apply(request):
    form = CouponApplyForm(request.POST)
    next_url = _get_safe_next_url(request, 'cart:cart_detail')
    cart = Cart(request)
    if form.is_valid():
        code = form.cleaned_data['code'].strip()
        try:
            coupon = Coupon.objects.get(code__iexact=code)
            ok, err_msg = coupon.validate_for_order(cart.get_total_price())
            if ok:
                request.session['coupon_id'] = coupon.id
                messages.success(
                    request,
                    f"Đã áp dụng mã giảm giá '{coupon.code}' (-{coupon.discount_percent}%) thành công!"
                )
            else:
                request.session['coupon_id'] = None
                messages.error(request, err_msg)
        except Coupon.DoesNotExist:
            request.session['coupon_id'] = None
            messages.error(request, f"Mã giảm giá '{code}' không tồn tại hoặc đã hết hạn.")
    return redirect(next_url)


@require_POST
def coupon_remove(request):
    next_url = _get_safe_next_url(request, 'cart:cart_detail')
    if 'coupon_id' in request.session:
        del request.session['coupon_id']
        messages.info(request, "Đã gỡ bỏ mã giảm giá.")
    return redirect(next_url)


def cart_detail(request):
    cart = Cart(request)
    items = list(cart)
    if cart.removed_items:
        messages.warning(
            request,
            "Một số sản phẩm trong giỏ đã ngừng kinh doanh hoặc hết hàng nên đã được tự động gỡ bỏ."
        )
    for item in items:
        item['update_quantity_form'] = CartAddProductForm(
            initial={'quantity': item['quantity'], 'override': True}
        )
    coupon_apply_form = CouponApplyForm()
    return render(
        request,
        'cart/detail.html',
        {
            'cart': cart,
            'coupon_apply_form': coupon_apply_form,
        }
    )
