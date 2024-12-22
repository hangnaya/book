from .models import Notification
from django.shortcuts import redirect
from django.urls import resolve

class MyMiddleWare:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        user = request.user
        if user.is_authenticated:
            # cart = Cart.objects.filter(customer=user).last()
            cart = request.session.get('cart', {})
            num_cart_item = len(cart)
            # if cart:   
            #     num_cart_item = cart.cartitem_set.count()
            notifications = Notification.objects.filter(customer=user).order_by('-create_at')[:5]
            response.set_cookie('notifications', notifications)
            response.set_cookie('num_cart_item', num_cart_item)
        return response
    
class CheckRoleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # List các URL cần kiểm tra quyền truy cập
        admin_urls = [
            'dashboard',
            'coupons', 'add_coupon', 'edit_coupon', 
            'products', 'add_product', 'edit_product', 'product_detail_admin',
            'categories', 'add_category', 'edit_category',
            'categories_post', 'add_category_post', 'edit_category_post',
            'posts', 'add_post', 'edit_post',
            'admin_orders', 'order_detail',
            'customers', 'view_profile',
        ]

        user_urls = [
            'home',
            'list-product',
            'product-detail',
            'cart',
            'check-out',
            'get_order',
            'order-detail',
            'list-product',
            'register',
            'order',
            'feedback',
            'list-feedback',
            'profile',
            'notification',
        ]

        try:
            resolved_url = resolve(request.path)
            current_view_name = resolved_url.url_name  # Tên view hiện tại
        except:
            current_view_name = None

        # Kiểm tra điều kiện nếu request.path nằm trong admin_urls
        if current_view_name in admin_urls:
            # Kiểm tra người dùng đã đăng nhập và có quyền is_superuser
            if not request.user.is_authenticated:
                return redirect('login-admin')
            elif not request.user.is_superuser:
                return redirect('home')
        elif current_view_name in user_urls:
            # Kiểm tra người dùng đã đăng nhập và có quyền is_superuser
            if request.user.is_authenticated and request.user.is_superuser:
                return redirect('dashboard')

        return self.get_response(request)
