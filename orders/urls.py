from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('create/', views.order_create, name='order_create'),
    path('success/<uuid:order_token>/', views.order_detail_and_lookup, name='order_success'),
    path('track/', views.order_detail_and_lookup, name='order_track'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('accounts/register/', views.customer_register, name='customer_register'),
    path('accounts/login/', views.customer_login, name='customer_login'),
    path('accounts/logout/', views.customer_logout, name='customer_logout'),
    path('webhook/bank/', views.bank_payment_webhook, name='bank_webhook'),
]
