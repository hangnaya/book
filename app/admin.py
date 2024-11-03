from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register([User, Category, Product, ProductImage,
                    ProductDetail, ProductSale, Coupon, Notification, OrderStatus])


class OrderItemInline(admin.TabularInline):
    model = OrderItem


class OrderTrackingInline(admin.TabularInline):
    model = Tracking


class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline, OrderTrackingInline]


admin.site.register(Order, OrderAdmin)
