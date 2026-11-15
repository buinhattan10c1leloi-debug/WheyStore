import uuid
from django.db import migrations, models


def populate_access_tokens(apps, schema_editor):
    Order = apps.get_model('orders', 'Order')
    for order in Order.objects.all():
        order.access_token = uuid.uuid4()
        order.save(update_fields=['access_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_coupon_order_discount_amount_order_discount_percent_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='access_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True, verbose_name='Mã truy cập bảo mật'),
        ),
        migrations.RunPython(populate_access_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='order',
            name='access_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='Mã truy cập bảo mật'),
        ),
        migrations.AddField(
            model_name='order',
            name='stock_deducted',
            field=models.BooleanField(default=True, verbose_name='Đã trừ tồn kho'),
        ),
    ]
