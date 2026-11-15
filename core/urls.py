from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from shop import views as shop_views
from shop.sitemaps import StaticViewSitemap, CategorySitemap, ProductSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'categories': CategorySitemap,
    'products': ProductSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('robots.txt', shop_views.robots_txt, name='robots_txt'),
    path(
        'sitemap.xml',
        sitemap,
        {'sitemaps': sitemaps},
        name='django.contrib.sitemaps.views.sitemap'
    ),
    path('dashboard/', shop_views.admin_dashboard, name='dashboard'),
    path('dashboard/login/', shop_views.dashboard_login, name='dashboard_login'),
    path('dashboard/logout/', shop_views.dashboard_logout, name='dashboard_logout'),
    path(
        'dashboard/order/<int:order_id>/status/',
        shop_views.dashboard_update_order_status,
        name='dashboard_update_order_status'
    ),
    path(
        'dashboard/product/<int:product_id>/restock/',
        shop_views.dashboard_quick_restock,
        name='dashboard_quick_restock'
    ),
    path('cart/', include('cart.urls', namespace='cart')),
    path('orders/', include('orders.urls', namespace='orders')),
    path('', include('shop.urls', namespace='shop')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
