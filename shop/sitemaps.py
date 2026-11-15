from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Category, Product


class StaticViewSitemap(Sitemap):
    protocol = 'http'

    def items(self):
        return ['shop:product_list', 'orders:order_track']

    def location(self, item):
        return reverse(item)


class CategorySitemap(Sitemap):
    protocol = 'http'

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return obj.get_absolute_url()


class ProductSitemap(Sitemap):
    protocol = 'http'

    def items(self):
        return Product.objects.filter(available=True).order_by('-updated')

    def lastmod(self, obj):
        return obj.updated

    def location(self, obj):
        return obj.get_absolute_url()
