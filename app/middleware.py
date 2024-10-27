from .models import Notification, Cart

class MyMiddleWare:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        user = request.user
        if user.is_authenticated:
            cart = Cart.objects.filter(customer=user).last()
            num_cart_item = 0
            if cart:   
                num_cart_item = cart.cartitem_set.count()
            notifications = Notification.objects.filter(customer=user).order_by('-create_at')[:5]
            response.set_cookie('notifications', notifications)
            response.set_cookie('num_cart_item', num_cart_item)
        return response