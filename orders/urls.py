from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('create/', views.order_create, name='order_create'),
    path('success/<int:order_id>/', views.order_detail_and_lookup, name='order_success'),
    path('track/', views.order_detail_and_lookup, name='order_track'),
]
