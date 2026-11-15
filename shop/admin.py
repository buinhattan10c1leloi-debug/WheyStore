from django.contrib import admin
from .models import Category, Product, Review


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'brand',
        'category',
        'price',
        'old_price',
        'servings',
        'protein_per_serving',
        'origin',
        'stock',
        'available',
    ]
    list_filter = ['available', 'brand', 'origin', 'category', 'created']
    list_editable = ['price', 'old_price', 'stock', 'available']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'brand', 'flavor', 'origin', 'description']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'product', 'rating', 'verified_purchase', 'created']
    list_filter = ['rating', 'verified_purchase', 'created', 'product']
    list_editable = ['verified_purchase']
    search_fields = ['user_name', 'comment', 'product__name']
