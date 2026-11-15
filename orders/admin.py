from django.contrib import admin
from .models import Order, OrderItem, Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_percent', 'active', 'created']
    list_filter = ['active', 'created']
    list_editable = ['discount_percent', 'active']
    search_fields = ['code']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0
    readonly_fields = ['get_item_cost']

    @admin.display(description='Thành tiền')
    def get_item_cost(self, obj):
        if obj.id:
            return f"{obj.get_cost():,.0f} VNĐ"
        return "-"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'full_name',
        'phone',
        'city',
        'payment_method',
        'status',
        'coupon',
        'discount_amount',
        'total_amount',
        'created',
    ]
    list_filter = ['status', 'payment_method', 'created', 'updated']
    list_editable = ['status']
    search_fields = ['id', 'full_name', 'phone', 'email', 'address']
    readonly_fields = ['created', 'updated']
    inlines = [OrderItemInline]
