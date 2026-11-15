from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('blog/', views.blog_list, name='blog_list'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('pages/lien-he/', views.contact_page, name='contact'),
    path('pages/<slug:page_slug>/', views.static_page, name='static_page'),
    path('bundle/<int:bundle_id>/add/', views.bundle_add_to_cart, name='bundle_add'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.wishlist_toggle, name='wishlist_toggle'),
    path('compare/', views.compare_view, name='compare'),
    path('compare/toggle/<int:product_id>/', views.compare_toggle, name='compare_toggle'),
    path('<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),
]
