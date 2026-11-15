import json
import logging
import urllib.request
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger('orders')


def _send_html_email(subject, to_email, template_name, context):
    if not to_email:
        return False
    try:
        html_body = render_to_string(template_name, context)
        text_body = strip_tags(html_body)
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@wheystore.vn'),
            to=[to_email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=True)
        return True
    except Exception as exc:
        logger.warning("Email delivery error to %s: %s", to_email, exc)
        return False


def send_order_confirmation_email(order):
    if not order.email:
        return False
    return _send_html_email(
        subject=f"[WheyStore] Xác nhận đơn hàng #DH{order.id}",
        to_email=order.email,
        template_name='orders/emails/order_confirmation.html',
        context={'order': order},
    )


def send_order_status_email(order):
    if not order.email:
        return False
    return _send_html_email(
        subject=f"[WheyStore] Cập nhật trạng thái đơn #DH{order.id}: {order.get_status_display()}",
        to_email=order.email,
        template_name='orders/emails/order_status_update.html',
        context={'order': order},
    )


def _send_telegram_message(text):
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({'chat_id': chat_id, 'text': text}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=3)
        return True
    except Exception as exc:
        logger.warning("Telegram notification error: %s", exc)
        return False


def notify_shop_owner_new_order(order):
    if not getattr(settings, 'NOTIFY_OWNER_ENABLED', True):
        return
    owner_email = getattr(settings, 'OWNER_NOTIFY_EMAIL', '')
    summary = (
        f"Đơn hàng mới #DH{order.id} từ {order.full_name} ({order.phone}) - "
        f"Tổng: {int(order.total_amount):,}đ ({order.get_payment_method_display()})."
    )
    if owner_email:
        _send_html_email(
            subject=f"[WheyStore Admin] Đơn hàng mới #DH{order.id}",
            to_email=owner_email,
            template_name='orders/emails/order_confirmation.html',
            context={'order': order},
        )
    _send_telegram_message(summary)


def notify_shop_owner_low_stock(product):
    if not getattr(settings, 'NOTIFY_OWNER_ENABLED', True) or product.stock > 5:
        return
    owner_email = getattr(settings, 'OWNER_NOTIFY_EMAIL', '')
    msg_text = f"Cảnh báo tồn kho thấp: '{product.name}' chỉ còn {product.stock} hộp."
    if owner_email:
        try:
            msg = EmailMultiAlternatives(
                subject=f"[WheyStore Admin] Sắp hết hàng: {product.name}",
                body=msg_text,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@wheystore.vn'),
                to=[owner_email],
            )
            msg.send(fail_silently=True)
        except Exception:
            pass
    _send_telegram_message(msg_text)
