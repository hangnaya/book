from django.shortcuts import render, get_object_or_404, redirect
from ..models import *
from django.db.models import F, FloatField, ExpressionWrapper, Sum, Case, When
from django.db.models.functions import Coalesce, Round
from django.db.models import F, FloatField, ExpressionWrapper, Sum, Case, When
from django.db.models.functions import Round
from django.core.paginator import Paginator
from django.http import JsonResponse
from rest_framework.decorators import api_view
import locale
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from ..forms import *
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime
from django.utils import timezone
from django.db.models import Avg
from django.contrib import messages
import paypalrestsdk
from django.conf import settings
from django.db import transaction
import hashlib
import hmac
from app.vnpay import vnpay
import random
import string

paypalrestsdk.configure({
    'mode': settings.PAYPAL_MODE,
    'client_id': settings.PAYPAL_CLIENT_ID,
    'client_secret': settings.PAYPAL_CLIENT_SECRET,
})

def generate_unique_order_code(length=8):
    characters = string.ascii_uppercase + string.digits  # Chữ hoa và số
    while True:
        code = ''.join(random.choices(characters, k=length))
        if not Order.objects.filter(order_code=code).exists():  # Kiểm tra trùng lặp
            return code

def convert_vnd_to_usd(vnd_amount):
    exchange_rate = 25274
    usd_amount = vnd_amount / exchange_rate
    return round(usd_amount, 2)

def get_cart(request):
    return request.session.get('cart', {})

@login_required(login_url='/login')
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def add_to_cart(request):
    if request.method == 'GET':
        cart = get_cart(request)
        cart_count = len(cart)

        # cart = Cart.objects.filter(customer=request.user).last()
        # if not cart:
        #     cart = Cart.objects.create(customer=request.user)
        # cartitems = CartItem.objects.filter(cart=cart)
        # cartitems = cartitems.annotate(
        #     price=Case(
        #         When(product__sale__gt=0, then=F('product__sale')),
        #         default=F('product__price'),
        #         output_field=FloatField()
        #     ),
        #     total_price=Round(ExpressionWrapper(F('price') * F('quantity'), output_field=FloatField())
        #                       )).distinct()
        voucher_wallet = VoucherWallet.objects.filter(customer=request.user).first()
        if voucher_wallet:
            voucher_wallet = VoucherWallet.objects.create(customer=request.user)
            voucher_wallet.save()

        coupons = Coupon.objects.filter(start_date__lte=timezone.now(),
                                         end_date__gte=timezone.now()).order_by('discount') 

        # context = {
        #     'cart': cart,
        #     'cartitems': cartitems,
        #     'voucher_wallet': voucher_wallet,
        #     'coupons': coupons
        # }
        context = {
            'cart': cart,
            'cart_count': cart_count,
            'voucher_wallet': voucher_wallet,
            'coupons': coupons
        }
        return render(request, 'customer/order/cart.html', context=context)

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        product = get_object_or_404(Product, pk=product_id)

        type = request.POST.get('type')
        quantity = request.POST.get('quantity')
        quantity = int(quantity)
        product_detail = ProductDetail.objects.filter(product=product, type=type).first()

        cart = get_cart(request)
        price = product.sale if product.sale > 0 else product.price
        cart_key = f"{product_id}_{type}"

        if cart_key in cart:
            if cart[cart_key]['quantity'] + quantity > product_detail.quantity:
                return JsonResponse({'status': 'error',
                                    'message': 'Số lượng sản phẩm không đủ, trong giỏ hàng đã có ' + str(
                                        cart[cart_key]['quantity']) + ' sản phẩm'})
            # Nếu sản phẩm đã có trong giỏ hàng, tăng số lượng
            cart[cart_key]['quantity'] += quantity
            cart[cart_key]['total_price'] = cart[cart_key]['quantity'] * price
        else:
            first_image = product.productimage_set.first()  # Lấy hình ảnh đầu tiên
            first_image_url = first_image.name.url if first_image else None
            
            # Nếu sản phẩm chưa có trong giỏ hàng, thêm mới
            cart[cart_key] = {
                'product_id': product_id,
                'type': type,
                'quantity': quantity,
                'price': price,
                'name': product.name,
                'image': first_image_url,
                'total_price': quantity * price,
            }

        request.session['cart'] = cart
        request.session.modified = True
        num_cart_item = len(cart)

        # cart = Cart.objects.filter(customer=request.user).last()
        # if not cart:
        #     cart = Cart.objects.create(customer=request.user)
        # cart_item = CartItem.objects.filter(cart=cart, product=product, type=type).first()
        
        # if cart_item:
        #     if cart_item.quantity + quantity > product_detail.quantity:
        #         return JsonResponse({'status': 'error',
        #                              'message': 'Số lượng sản phẩm không đủ, trong giỏ hàng đã có ' + str(
        #                                  cart_item.quantity) + ' sản phẩm'})
        #     else:
        #         cart_item.quantity = cart_item.quantity + quantity
        # else:
        #     cart_item = CartItem.objects.create(cart=cart, product=product, type=type, quantity=quantity)
        # cart_item.save()
        # num_cart_item = cart.cartitem_set.count()

        return JsonResponse(
            {'status': 'success', 'message': 'Thêm vào giỏ hàng thành công', 'num_cart_item': num_cart_item})

def edit_cart_item(request):
    cart_item_id = request.POST.get('cart_item_id')
    quantity = request.POST.get('quantity')

    cart = request.session.get('cart', {})
    if str(cart_item_id) in cart:
        product_detail = ProductDetail.objects.filter(product=cart[str(cart_item_id)]['product_id'], type=cart[str(cart_item_id)]['type']).first()
        if int(quantity) > product_detail.quantity:
            return JsonResponse({'status': 'error', 'message': 'Số lượng sản phẩm không đủ'})
        if int(quantity) == 0:
            del cart[str(cart_item_id)]
        else:
            cart[str(cart_item_id)]['quantity'] = int(quantity)
            cart[str(cart_item_id)]['total_price'] = int(quantity) * int(cart[str(cart_item_id)]['price'])
        request.session['cart'] = cart
        request.session.modified = True
    # cart_item = CartItem.objects.get(pk=cart_item_id)
    # product_detail = ProductDetail.objects.filter(product=cart_item.product, type=cart_item.type).first()
    # if int(quantity) > product_detail.quantity:
    #     return JsonResponse({'status': 'error', 'message': 'Số lượng sản phẩm không đủ'})
    # cart_item.quantity = int(quantity)
    # cart_item.save()
    # if int(quantity) == 0:
    #     cart_item.delete()
    return JsonResponse({'status': 'success', 'message': 'Cập nhật thành công'})


def delete_cart_item(request):
    cart_item_id = request.POST.get('cart_item_id')
    cart = request.session.get('cart', {})
    if str(cart_item_id) in cart:
        del cart[str(cart_item_id)]
        request.session['cart'] = cart
        request.session.modified = True

    # cart_item = CartItem.objects.get(pk=cart_item_id)
    # cart_item.delete()
    return JsonResponse({'success': 'Xóa thành công'})

@login_required(login_url='/login')
def orderManager(request):
    states = OrderStatus.objects.all()
    keyword = request.GET.get('keyword', '')
    orders = Order.objects.filter(customer__username__icontains=keyword).select_related('customer', 'status').order_by('-order_id')
    status = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    print(status)
    if status:
        orders = orders.filter(status__name=status)
    if start_date == '' and end_date == '':
        orders = orders.all()
    elif end_date == '':
        orders = orders.filter(date__gte=start_date)
    elif start_date == '':
        orders = orders.filter(date__lte=end_date)
    else:
        orders = orders.filter(Q(date__gte=start_date) & Q(date__lte=end_date))

    paginator = Paginator(orders, 15)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin_shop/order/orders.html', {'page_obj': page_obj, 'states': states})


@login_required(login_url='/login')
def getOrderDetail(request):
    order_id = int(request.GET.get("order_id"))
    order = Order.objects.filter(order_id=order_id).select_related('customer', 'status').first()
    # price_order = order.total - order.discount - order.shipping
    order_items = OrderItem.objects.filter(order_id=order_id).annotate(
        curr_price=Case(When(product__sale__gte=0, then=F('product__sale')),
                         default=F('product__price')),
        total=F('curr_price') * F('quantity')).distinct()
    price_order = order_items.aggregate(total_sum=Sum('total'))['total_sum']
    if request.method == "POST":
        status = int(request.POST.get('status'))
        if order.status.order_status_id != status and status != 7:
            status = OrderStatus.objects.get(order_status_id=status)
            order.status = status
            order.save()
            tracking = Tracking(order=order, order_status=status)
            tracking.save()
            if status.order_status_id == 2:
                status_text = f"Đơn hàng #{order.order_id} đã được người bán xác nhận"
            elif status.order_status_id == 3:
                status_text = f"Đơn hàng #{order.order_id} đã được giao cho đơn vị vận chuyển"
            elif status.order_status_id == 4:
                status_text = f"Đơn hàng #{order.order_id} đang được giao đến quý khách"
            elif status.order_status_id == 5:
                status_text = f"Đơn hàng #{order.order_id} đã được hủy thành công"
                for item in order_items:
                    product_detail = ProductDetail.objects.filter(product=item.product, type=item.type).first()
                    product_detail.quantity += item.quantity
                    product_detail.save()
            else:
                status_text = f"Đơn hàng #{order.order_id} đã được giao thành công"
            notification = Notification.objects.create(
                content=status_text,
                create_at=timezone.now(),
                customer=order.customer
            )
        else:
            pass
    if order.status.order_status_id == 1:
        status_ids = [1, 2, 5]
    elif order.status.order_status_id == 2:
        status_ids = [2, 3, 5]
    elif order.status.order_status_id == 3:
        status_ids = [3, 4]
    elif order.status.order_status_id == 4:
        status_ids = [4, 5, 6]
    elif order.status.order_status_id == 5:
        status_ids = [5]
    elif order.status.order_status_id == 7:
        status_ids = [7]
    else:
        status_ids = [6]
    states = OrderStatus.objects.filter(order_status_id__in=status_ids).order_by("order_status_id")
    return render(request, 'admin_shop/order/order-detail.html',
                  {'order': order, 'order_items': order_items, 'states': states, 'price_order': price_order, })


def create_payment(request):
    if request.method == "POST":
        total = int(request.POST.get('total'))
        total_usd = convert_vnd_to_usd(total)
        order_id = request.POST.get('order_id')

        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": f"http://127.0.0.1:8000/payment-success?order_id={order_id}",
                "cancel_url": "http://127.0.0.1:8000/payment-cancel/"
            },
            "transactions": [{
                "amount": {
                    "total": total_usd,
                    "currency": "USD"
                },
                "description": "Thanh toán đơn hàng"
            }]
        })

        if payment.create():
            approval_url = next(link['href'] for link in payment.links if link['rel'] == 'approval_url')
            return JsonResponse({'approval_url': approval_url})
        else:
            return JsonResponse({'error': payment.error}, status=500)

def payment_success(request):
    payment_id = request.GET.get('paymentId')
    payer_id = request.GET.get('PayerID')
    order_id = int(request.GET.get('order_id'))
    order = get_object_or_404(Order, pk=order_id)
    status = OrderStatus.objects.get(name='Chờ xác nhận')
    order.status = status
    order.save()

    payment = paypalrestsdk.Payment.find(payment_id)

    if payment.execute({"payer_id": payer_id}):
        messages.success(request, f"Thanh toán đơn hàng #{order_id} thành công")
        return redirect('/get-order')
    else:
        messages.success(request, f"Thanh toán đơn hàng #{order_id} thất bại")
        return redirect('/get-order')

def payment_cancel(request):
    messages.success(request, 'Đơn hàng chưa được thanh toán')
    return redirect('/get-order')

def payment_return(request):
    inputData = request.GET
    if inputData:
        vnp = vnpay()
        vnp.responseData = inputData.dict()
        order_id = int(request.GET.get('order_id'))
        order = get_object_or_404(Order, pk=order_id)
        order_id = inputData['vnp_TxnRef']
        vnp_ResponseCode = inputData['vnp_ResponseCode']

        if vnp.validate_response(settings.VNPAY_HASH_SECRET):
            if vnp_ResponseCode == "00":
                status = OrderStatus.objects.get(name='Chờ xác nhận')
                order.status = status
                order.save()
                messages.success(request, f"Thanh toán đơn hàng #{order_id} thành công")
            else:
                messages.success(request, f"Thanh toán đơn hàng #{order_id} thất bại")
        else:
            messages.success(request, 'Đơn hàng chưa được thanh toán')
        return redirect('/get-order')
    else:
        messages.success(request, 'Đơn hàng chưa được thanh toán')
        return redirect('/get-order')

def payment_vnpay(request):
    if request.method == "GET":
        total = int(request.GET.get('total'))
        order_id = int(request.GET.get('order_id'))
        random_number = random.randint(100, 100000)
        new_order_id = order_id + random_number
        language = request.GET.get('language')
        ipaddr = get_client_ip(request)
        # Build URL Payment
        vnp = vnpay()
        vnp.requestData['vnp_Version'] = '2.1.0'
        vnp.requestData['vnp_Command'] = 'pay'
        vnp.requestData['vnp_TmnCode'] = settings.VNPAY_TMN_CODE
        vnp.requestData['vnp_Amount'] = total * 100
        vnp.requestData['vnp_CurrCode'] = 'VND'
        vnp.requestData['vnp_TxnRef'] = new_order_id
        vnp.requestData['vnp_OrderInfo'] = 'Thanh toán đơn hàng'
        vnp.requestData['vnp_OrderType'] = 'other'
        # Check language, default: vn
        if language and language != '':
            vnp.requestData['vnp_Locale'] = language
        else:
            vnp.requestData['vnp_Locale'] = 'vn'
        # Check bank_code, if bank_code is empty, customer will be selected bank on VNPAY
        # if bank_code and bank_code != "":
        #     vnp.requestData['vnp_BankCode'] = bank_code

        vnp.requestData['vnp_CreateDate'] = datetime.now().strftime('%Y%m%d%H%M%S')  # 20150410063022
        vnp.requestData['vnp_IpAddr'] = ipaddr
        vnp.requestData['vnp_ReturnUrl'] = f"{settings.VNPAY_RETURN_URL}?order_id={order_id}"
        vnpay_payment_url = vnp.get_payment_url(settings.VNPAY_URL, settings.VNPAY_HASH_SECRET)
        print(vnpay_payment_url)
        return redirect(vnpay_payment_url)

def hmacsha512(key, data):
    byteKey = key.encode('utf-8')
    byteData = data.encode('utf-8')
    return hmac.new(byteKey, byteData, hashlib.sha512).hexdigest()

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def checkout(request):
    if request.method == 'GET':
        return render(request, 'customer/order/checkout.html')

    cart_items = request.POST.getlist('cart_item')
    cart_items = [cart_item.strip() for cart_item in cart_items]
    total = request.POST.get('total_money')
    coupon = request.POST.get('coupon')
    discount = request.POST.get('discount')

    cart = request.session.get('cart', {})
    cart_items = {str(pid): cart[str(pid)] for pid in cart_items if str(pid) in cart}
    # cart_items = CartItem.objects.filter(pk__in=cart_items).annotate(
    #     price=Case(
    #         When(product__sale__gt=0, then=F('product__sale')),
    #         default=F('product__price'),
    #         output_field=FloatField()
    #     ),
    # ).distinct()
    locale.setlocale(locale.LC_ALL, 'vi_VN.UTF-8')
    total = locale.format_string('%dđ', int(total), grouping=True).replace(',', '.')
    coupons = Coupon.objects.filter(start_date__lte=timezone.now(), end_date__gte=timezone.now()).order_by('discount')
    context = {
        'cart_items': cart_items,
        'total': total,
        'coupon': coupon,
        'discount': discount,
        'coupons': coupons
    }
    return render(request, 'customer/order/checkout.html', context)


def buy_now(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        product = Product.objects.filter(pk=product_id).annotate(
            curr_price=Case(When(sale__gte=0, then=F('sale')),
                default=F('price')),
            rating=Avg('feedback__rating'),
        ).first()

        type = request.POST.get('type')
        quantity = request.POST.get('quantity')
        quantity = int(quantity)

        product_detail = ProductDetail.objects.filter(product=product, type=type).first()
        if quantity > product_detail.quantity:
            return JsonResponse({'status': 'error', 'message': 'Số lượng sản phẩm không đủ'})
        total = product.curr_price * quantity
        locale.setlocale(locale.LC_ALL, 'vi_VN.UTF-8')
        total = locale.format_string('%dđ', int(total), grouping=True).replace(',', '.')
        coupons = Coupon.objects.filter(start_date__lte=timezone.now(), end_date__gte=timezone.now()).order_by('discount')

        context = {
            'product': product,
            'type': type,
            'quantity': quantity,
            'total': total,
            'coupons': coupons
        }
        return render(request, 'customer/order/checkout.html', context)
    else:
       return redirect('home') 


def add_address(request):
    if request.method == 'POST':
        user = request.user
        form = AddressShippingForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'status': 'error', 'message': 'Thông tin không hợp lệ'})
        receiver = form.cleaned_data['receiver']
        phone = form.cleaned_data['phone']
        address = form.cleaned_data['address']
        address_shipping = AddressShipping(receiver=receiver, phone=phone, address=address, customer=user)
        address_shipping.save()
        data = {
            'status': 'success',
            'result': {
                'id': address_shipping.address_shipping_id,
                'receiver': receiver,
                'phone': phone,
                'address': address
            }
        }
        return JsonResponse(data)

def edit_address(request):
    if request.method == 'POST':
        user = request.user
        address_shipping_id = request.POST.get('address_shipping_id')
        address = get_object_or_404(AddressShipping, address_shipping_id=address_shipping_id)
        form = AddressShippingForm(request.POST, instance=address)
        if not form.is_valid():
            return JsonResponse({'status': 'error', 'message': 'Thông tin không hợp lệ'})
        receiver = form.cleaned_data['receiver']
        phone = form.cleaned_data['phone']
        address = form.cleaned_data['address']
        form.save()
        data = {
            'status': 'success',
            'result': {
                'id': address_shipping_id,
                'receiver': receiver,
                'phone': phone,
                'address': address
            }
        }
        return JsonResponse(data)

def delete_address(request):
    if request.method == 'POST':
        address_shipping_id = int(request.POST.get('address_shipping_id'))
        address = AddressShipping.objects.get(address_shipping_id=address_shipping_id)
        address.delete()
        return JsonResponse({
            'success': True,
            'id': address_shipping_id,
            'message': "Địa chỉ giao hàng đã được xóa thành công"
        })
    
def order(request):
    if request.method == 'POST':
        coupon = request.POST.get('coupon')
        discount = request.POST.get('discount')
        cart_items = request.POST.getlist('cart_item')
        cart = request.session.get('cart', {})  # Lấy giỏ hàng từ session
        # Lọc sản phẩm trong giỏ hàng theo danh sách ID
        cart_items = {str(pid): cart[str(pid)] for pid in cart_items if str(pid) in cart}

        # cart_items = CartItem.objects.filter(pk__in=cart_items)
        order_form = OrderForm(request.POST)
        product_id = request.POST.get('product_id')
        type = request.POST.get('type')
        quantity = request.POST.get('quantity')
        total_vnd = int(request.POST.get('total'))
        total_usd = convert_vnd_to_usd(total_vnd)
        if quantity:
            quantity = int(request.POST.get('quantity'))

        if order_form.is_valid():
            try:
                with transaction.atomic():
                    order = order_form.save(commit=False)
                    order.customer = request.user
                    order.order_code = generate_unique_order_code()
                    payment_method = order.payment_method
                    is_paypal = False
                    is_vnpay = False
                    status = OrderStatus.objects.get(name='Chờ xác nhận')

                    if payment_method == 'Tiền mặt':
                        order.status = status
                        order.save()
                        messages.success(request, 'Đặt hàng thành công')
                    elif payment_method == 'Paypal':
                        status2 = OrderStatus.objects.get(name='Chờ thanh toán')
                        order.status = status2
                        order.save()
                        payment = paypalrestsdk.Payment({
                            "intent": "sale",
                            "payer": {
                                "payment_method": "paypal"
                            },
                            "redirect_urls": {
                                "return_url": f"http://127.0.0.1:8000/payment-success?order_id={order.order_id}",
                                "cancel_url": "http://127.0.0.1:8000/payment-cancel/"
                            },
                            "transactions": [{
                                "amount": {
                                    "total": total_usd,
                                    "currency": "USD"
                                },
                                "description": "Thanh toán đơn hàng"
                            }]
                        })

                        if payment.create():
                            # status = OrderStatus.objects.get(name='Chờ thanh toán')
                            # order.status = status
                            # order.save()
                            is_paypal = True
                            
                        else:
                            context = {
                                'cart_items': cart_items,
                                'coupon': coupon,
                                'discount': discount,
                                'order_form': order_form,
                                'error': payment.error
                            }
                            return render(request, 'customer/order/checkout.html', context)
                    elif payment_method == 'VNpay':
                        status2 = OrderStatus.objects.get(name='Chờ thanh toán')
                        order.status = status2
                        order.save()
                        language = request.POST.get('language')
                        ipaddr = get_client_ip(request)
                        # Build URL Payment
                        vnp = vnpay()
                        vnp.requestData['vnp_Version'] = '2.1.0'
                        vnp.requestData['vnp_Command'] = 'pay'
                        vnp.requestData['vnp_TmnCode'] = settings.VNPAY_TMN_CODE
                        vnp.requestData['vnp_Amount'] = total_vnd * 100
                        vnp.requestData['vnp_CurrCode'] = 'VND'
                        vnp.requestData['vnp_TxnRef'] = order.order_id
                        vnp.requestData['vnp_OrderInfo'] = 'Thanh toán đơn hàng'
                        vnp.requestData['vnp_OrderType'] = 'other'
                        # Check language, default: vn
                        if language and language != '':
                            vnp.requestData['vnp_Locale'] = language
                        else:
                            vnp.requestData['vnp_Locale'] = 'vn'
                        # Check bank_code, if bank_code is empty, customer will be selected bank on VNPAY
                        # if bank_code and bank_code != "":
                        #     vnp.requestData['vnp_BankCode'] = bank_code

                        vnp.requestData['vnp_CreateDate'] = datetime.now().strftime('%Y%m%d%H%M%S')  # 20150410063022
                        vnp.requestData['vnp_IpAddr'] = ipaddr
                        vnp.requestData['vnp_ReturnUrl'] = f"{settings.VNPAY_RETURN_URL}?order_id={order.order_id}"
                        vnpay_payment_url = vnp.get_payment_url(settings.VNPAY_URL, settings.VNPAY_HASH_SECRET)
                        is_vnpay = True

                    tracking = Tracking.objects.create(order_status=status, order=order)
                    tracking.save()
                    coupon = Coupon.objects.filter(code=coupon).order_by('-start_date').first()

                    notification = Notification.objects.create(
                        content=f"Đơn hàng #{order.order_id} đã được đặt hàng thành công",
                        create_at=timezone.now(),
                        customer=request.user
                    )

                    if coupon:
                        coupon.quantity -= 1
                        coupon.save()
                    for cart_id, cart_item in cart_items.items():
                        product = Product.objects.filter(pk=cart_item['product_id']).first()
                        order_item = OrderItem.objects.create(
                            type=cart_item['type'],
                            quantity=cart_item['quantity'],
                            price=cart_item['price'],
                            order=order,
                            product=product
                        )
                        order_item.save()
                        product.total_sold += cart_item['quantity']
                        product.save()

                        product_detail = ProductDetail.objects.filter(product=product, type=cart_item['type']).first()
                        if product_detail.quantity < cart_item['quantity']:
                            raise ValidationError('Số lượng sản phẩm "' + product_detail.product.name + '" trong kho không đủ, vui lòng chọn lại số lượng')
                        product_detail.quantity -= cart_item['quantity']
                        product_detail.save()

                        del cart[str(cart_id)]
                        request.session['cart'] = cart
                        request.session.modified = True
                        # cart_item.delete()
                    if product_id:
                        product = Product.objects.filter(pk=product_id).annotate(
                            curr_price=Case(
                                When(sale__gte=0, then=F('sale')),
                                default=F('price'),
                                output_field=FloatField()
                            ),
                        ).first()
                        product_detail = ProductDetail.objects.filter(product=product, type=type).first()
                        if product_detail.quantity < quantity:
                            raise ValidationError('Số lượng sản phẩm "' + product_detail.product.name + '" trong kho không đủ, vui lòng chọn lại số lượng')
                        product_detail.quantity -= quantity
                        product_detail.save()

                        product.total_sold += quantity
                        product.save()
                        order_item = OrderItem.objects.create(
                            type=type,
                            quantity=quantity,
                            price=product.curr_price,
                            order=order,
                            product=product
                        )
                        order_item.save()
                    
                    if is_paypal == True:
                        for link in payment.links:
                                if link.rel == "approval_url":
                                    approval_url = str(link.href)
                                    return redirect(approval_url)
                    elif is_vnpay == True:
                        return redirect(vnpay_payment_url)
                    else:
                        return redirect('/get-order')
            except ValidationError as e:
                # Bắt lỗi và hiển thị thông báo
                messages.error(request, str(e))
                context = {
                    'cart_items': cart_items,
                    'coupon': coupon,
                    'discount': discount,
                    'order_form': order_form,
                }
                return render(request, 'customer/order/checkout.html', context)
        else:
            context = {
                'cart_items': cart_items,
                'coupon': coupon,
                'discount': discount,
                'order_form': order_form,
            }
            return render(request, 'customer/order/checkout.html', context)
    return redirect('home')


@login_required(login_url='/login')
def get_order(request):
    keyword = request.GET.get('keyword', '')
    status_choice = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    orders = Order.objects.filter(customer=request.user).order_by('-order_id')
    if keyword:
        orders = orders.filter(order_id__icontains=keyword)
    if status_choice:
        orders = orders.filter(status__name=status_choice)
    if start_date:
        orders = orders.filter(date__gte=start_date)
    if end_date:
        orders = orders.filter(date__lte=end_date)

    paginator = Paginator(orders, 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    status = OrderStatus.objects.all()

    context = {
        'page_obj': page_obj,
        'orders' : page_obj.object_list,
        'states': status,
        'messages': messages.get_messages(request)
    }
    return render(request, 'customer/orders.html', context)


def get_order_detail(request):
    order_id = int(request.GET.get('order_id'))
    order = get_object_or_404(Order, pk=order_id)
    order_tracking = Tracking.objects.filter(order=order).order_by('date')

    Notification.objects.filter(
        customer=request.user,
        content__icontains=f"#{order_id}"
    ).update(is_read=1)

    context = {
        'order': order,
        'order_tracking': order_tracking
    }
    return render(request, 'customer/order_detail.html', context)


def cancel_order(request):
    order_id = request.GET.get('order_id')
    order = Order.objects.get(pk=order_id)
    order.status = OrderStatus.objects.get(name='Hủy đơn')
    order_item = order.orderitem_set.all()
    for item in order_item:
        product_detail = ProductDetail.objects.filter(product=item.product, type=item.type).first()
        product_detail.quantity += item.quantity
        product_detail.save()
    order.save()
    context = {
        'order': order,
    }
    return render(request, 'customer/order_detail.html', context)
