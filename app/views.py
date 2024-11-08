from django.shortcuts import render, get_object_or_404, redirect
from .models import *
from django.db.models import F, FloatField, ExpressionWrapper, Sum, Value, CharField, Case, When
from django.db.models.functions import Coalesce, Round
from django.db.models import F, FloatField, ExpressionWrapper, Sum, Value, CharField, Count, Case, When
from django.db.models.functions import Coalesce, Round, TruncMonth
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from .serializers import ProductSerializer, FeedbackSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import locale
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from .forms import *
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms import formset_factory
from datetime import datetime
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import date
import os
from datetime import timedelta
import logging
from django.db.models import Avg
from django.contrib import messages

def convert_diff(diff):
    days_in_month = 30
    days_in_year = 365
    if diff.days < 1:
        return f'{abs(int(diff.total_seconds() // 3600))} giờ'

    if diff.days < days_in_month:
        return f"{diff.days} ngày"

    elif diff.days < days_in_year:
        months = diff.days // days_in_month
        return f"{months} tháng"

    else:
        years = diff.days // days_in_year
        return f"{years} năm"


def log_in(request):
    if request.method == 'GET':
        return render(request, 'customer/login.html')
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        try:
            userCheck = User.objects.get(username=username)
            if not userCheck.is_active:
                return render(request, 'customer/login.html', {
                    'error': 'Tài khoản của bạn đã bị khóa. Vui lòng liên hệ với quản trị viên.'
                })
        except User.DoesNotExist:
            return render(request, 'customer/login.html', {
                'error': 'Tên đăng nhập hoặc mật khẩu không đúng'
            })

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.is_superuser:
                return redirect('/admin_orders')
            return redirect('/home')
        else:
            return render(request, 'customer/login.html', {'error': 'Tên đăng nhập hoặc mật khẩu không đúng'})


def log_out(request):
    logout(request)
    return redirect('/home')


def register(request):
    message = ''
    error = ''
    if request.method == 'GET':
        return render(request, 'customer/home.html')
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        repassword = request.POST.get('repassword')
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        if password != repassword:
            error = 'Mật khẩu không khớp nhau'
        else:
            if User.objects.filter(username=username).exists():
                error = 'Tài khoản đã được sử dụng'
            elif User.objects.filter(email=email).exists():
                error = 'Email đã được sử dụng'
            elif User.objects.filter(phone=phone).exists():
                error = 'Số điện thoại đã được sử dụng'
            else:
                user = User(username=username, phone = phone, email = email, name = name)
                user.set_password(password)
                user.save()
                message = 'Đăng ký tài khoản thành công'
        return render(request, 'customer/login.html', {'messages': message, 'error': error})


def home(request):
    now = timezone.now()

    products = Product.objects.distinct()

    top_selling_products = products.order_by('-total_sold')[:10]

    top_sale_products = products.order_by('-sale')[:10]

    hot_selling_product = (products.filter(orderitem__order__date__month=now.month,
                                           orderitem__order__date__year=now.year)
                           .annotate(total_sold_month=Sum('orderitem__quantity'))
                           .order_by('-total_sold_month')
                           )[:10]

    print(top_selling_products)
    context = {
        'top_selling_products': top_selling_products,
        'top_sale_products': top_sale_products,
        'hot_selling_products': hot_selling_product,
        'range': range(10)
    }

    return render(request, 'customer/home.html', context)


def listProduct(request):
    categories = Category.objects.all()
    search = request.GET.get('search')

    context = {
        'categories': categories,
        'search': search
    }
    return render(request, 'customer/list-product.html', context)


@api_view(['GET'])
def getListProduct(request):
    search = request.GET.get('search')

    category = request.GET.get('category')
    if category:
        category = [int(category) for category in category.split(',')]

    status = request.GET.get('status')
    if status:
        status = [status for status in status.split(',')]

    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    # rating = request.GET.get('rating')
    sort = request.GET.get('sort')
    top_sale_products = request.GET.get('top_sale_products')
    top_selling_products = request.GET.get('top_selling_products')
    best_selling_product = request.GET.get('best_selling_product')

    products = Product.objects.annotate(
        quantity=Sum('productdetail__quantity')
    )
    print(products)
    if search is not None and search != '':
        products = products.filter(name__icontains=search)

    if category:
        categories = Category.objects.filter(category_id__in=category)
        products = products.filter(category__in=categories)

    if status and len(status) == 1:
        if status[0] == 'instock':
            products = products.filter(quantity__gt=0)
        elif status[0] == 'outstock':
            products = products.filter(quantity=0)

    if min_price:
        products = products.filter(price__gte=int(min_price))

    if max_price:
        products = products.filter(price__lte=int(max_price))

    # if rating:
    #     products = products.filter(rating__gte=rating)

    if top_sale_products:
        products = products.order_by('-sale')

    if top_selling_products:
        products = products.order_by('-total_sold')

    if best_selling_product:
        now = timezone.now()
        products = (products.filter(
            orderitem__order__date__month=now.month,
            orderitem__order__date__year=now.year
        ).annotate(
            total_sold_month=Sum('orderitem__quantity')
        ).order_by('-total_sold_month'))
                    
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')

    paginator = PageNumberPagination()
    paginator.page_query_param = 'page'
    paginator.page_size = 20
    result_page = paginator.paginate_queryset(products, request)
    serializer = ProductSerializer(result_page, many=True, context={'request': request})

    respone = paginator.get_paginated_response(serializer.data)
    respone.data['current_page'] = paginator.page.number
    respone.data['total_page'] = paginator.page.paginator.num_pages
    return respone


def getProductDetail(request, product_id):
    product = Product.objects.filter(pk=product_id).annotate(
        quantity=Sum('productdetail__quantity'),
        rating=Avg('feedback__rating')
    ).first()
    product.rating = product.rating if product.rating is not None else 0

    sales = product.productsale_set.filter(start_date__lte=timezone.now(), end_date__gte=timezone.now()).first()
    feedbacks = Feedback.objects.filter(product=product).order_by('-date')
    num_feedbacks = feedbacks.count()
    feedback_paginator = Paginator(feedbacks, 5)
    feedback_page = request.GET.get('page')
    feedbacks = feedback_paginator.get_page(feedback_page)

    related_products = (Product.objects
                        .filter(category=product.category)
                        .exclude(pk=product.pk)
                        )[:10].all()

    context = {
        'product': product,
        'sales': sales,
        'num_feedbacks': num_feedbacks,
        'feedbacks': feedbacks,
        'related_products': related_products
    }
    return render(request, 'customer/product_detail.html', context)


@login_required(login_url='/login')
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def add_to_cart(request):
    if request.method == 'GET':
        cart = Cart.objects.filter(customer=request.user).last()
        if not cart:
            cart = Cart.objects.create(customer=request.user)
        cartitems = CartItem.objects.filter(cart=cart)
        cartitems = cartitems.annotate(
            price=Case(
                When(product__sale__gte=0, then=F('product__sale')),
                default=F('product__price'),
                output_field=FloatField()
            ),
            total_price=Round(ExpressionWrapper(F('price') * F('quantity'), output_field=FloatField())
                              )).distinct()
        voucher_wallet = VoucherWallet.objects.filter(customer=request.user).first()
        if voucher_wallet:
            voucher_wallet = VoucherWallet.objects.create(customer=request.user)
            voucher_wallet.save()

        coupons = Coupon.objects.filter(start_date__lte=timezone.now(),
                                         end_date__gte=timezone.now()).order_by('discount') 

        context = {
            'cart': cart,
            'cartitems': cartitems,
            'voucher_wallet': voucher_wallet,
            'coupons': coupons
        }
        return render(request, 'customer/order/cart.html', context=context)

    if request.method == 'POST':
        id = request.POST.get('product_id')
        product = get_object_or_404(Product, pk=id)

        type = request.POST.get('type')
        quantity = request.POST.get('quantity')
        quantity = int(quantity)
        cart = Cart.objects.filter(customer=request.user).last()
        if not cart:
            cart = Cart.objects.create(customer=request.user)

        cart_item = CartItem.objects.filter(cart=cart, product=product, type=type).first()
        product_detail = ProductDetail.objects.filter(product=product, type=type).first()
        if cart_item:
            if cart_item.quantity + quantity > product_detail.quantity:
                return JsonResponse({'status': 'error',
                                     'message': 'Số lượng sản phẩm không đủ, trong giỏ hàng đã có ' + str(
                                         cart_item.quantity) + ' sản phẩm'})
            else:
                cart_item.quantity = cart_item.quantity + quantity
        else:
            cart_item = CartItem.objects.create(cart=cart, product=product, type=type, quantity=quantity)
        cart_item.save()
        num_cart_item = cart.cartitem_set.count()
        return JsonResponse(
            {'status': 'success', 'message': 'Thêm vào giỏ hàng thành công', 'num_cart_item': num_cart_item})

def edit_cart_item(request):
    cart_item_id = request.POST.get('cart_item_id')
    quantity = request.POST.get('quantity')
    cart_item = CartItem.objects.get(pk=cart_item_id)
    product_detail = ProductDetail.objects.filter(product=cart_item.product, type=cart_item.type).first()
    if int(quantity) > product_detail.quantity:
        return JsonResponse({'status': 'error', 'message': 'Số lượng sản phẩm không đủ'})
    cart_item.quantity = int(quantity)
    cart_item.save()
    if int(quantity) == 0:
        cart_item.delete()
    return JsonResponse({'status': 'success', 'message': 'Cập nhật thành công'})


def delete_cart_item(request):
    cart_item_id = request.POST.get('cart_item_id')
    cart_item = CartItem.objects.get(pk=cart_item_id)
    cart_item.delete()
    return JsonResponse({'success': 'Xóa thành công'})


@api_view(['GET'])
def check_coupon(request):
    coupon_code = request.GET.get('coupon')
    coupon = Coupon.objects.filter(code=coupon_code).order_by('-start_date').first()
    if not coupon:
        return JsonResponse({'status': 'error', 'message': 'Mã giảm giá không hợp lệ'})

    now = timezone.now()
    if now < coupon.start_date or now > coupon.end_date:
        return JsonResponse({'status': 'error', 'message': 'Mã giảm giá đã hết hạn'})

    total_money = request.GET.get('total_money')
    total_money = float(total_money)
    if total_money < coupon.condition:
        locale.setlocale(locale.LC_ALL, 'vi_VN.UTF-8')
        condition = locale.format_string('%dđ', int(coupon.condition), grouping=True).replace(',', '.')
        return JsonResponse(
            {'status': 'error', 'message': 'Chưa đủ điều kiện đơn hàng tối thiếu. Đơn hàng tối thiểu là ' + condition})

    return JsonResponse({'status': 'success', 'discount': coupon.discount, 'condition': coupon.condition})


def checkout(request):
    if request.method == 'GET':
        return render(request, 'customer/order/checkout.html')

    cart_items = request.POST.getlist('cart_item')
    cart_items = [int(cart_item) for cart_item in cart_items]

    total = request.POST.get('total_money')
    coupon = request.POST.get('coupon')
    discount = request.POST.get('discount')

    cart_items = CartItem.objects.filter(pk__in=cart_items).annotate(
        price=Case(
            When(product__sale__gte=0, then=F('product__sale')),
            default=F('product__price'),
            output_field=FloatField()
        ),
    ).distinct()
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



def updateStatus(request):
    user_id = int(request.POST.get('user_id'))
    is_active = int(request.POST.get('is_active'))
    user = User.objects.get(id=user_id)
    user.is_active = is_active
    user.save()
    return JsonResponse({'status': 'true'})

@login_required(login_url='/login')
def addProduct(request):
    messages = '' 
    error = ''
    years = list(range(2025, 1899, -1))
    product_form = ProductForm(request.POST or None)
    product_sale_form = ProductSaleForm(request.POST or None)
    types = request.POST.getlist('type')
    quantities = request.POST.getlist('quantity')
    product_image_form = ProductImageForm(request.POST, request.FILES)
    if product_form.is_valid() and product_sale_form.is_valid() and product_image_form.is_valid():
        product = product_form.save()
        # product_sale = ProductSale(price=product_sale_form.cleaned_data['price'], product=product)
        # product_sale.save()
        for i in range(len(types)):
            product_detail = ProductDetail(type=types[i], quantity=quantities[i], product=product)
            product_detail.save()
            images = request.FILES.getlist('name')
            for image in images:
                product_image = ProductImage(name=image, product=product)
                product_image.save()
        messages = "Thêm sản phẩm thành công"
    else:
        if request.method == 'POST':
            error = 'Bạn cần nhập đầy đủ thông tin'
        else:
            error = ''
    return render(request, 'admin_shop/product/add-product.html',
                  {'product_form': product_form, 'product_sale_form': product_sale_form, 'years': years,
                   'product_image_form': product_image_form, 'error': error, 'messages' : messages})

@login_required(login_url='/login')
def editProduct(request):
    messages = '' 
    error = ''
    categories = Category.objects.all()
    years = list(range(2025, 1899, -1))
    if request.method == "POST":
        print(request.FILES)
        product_id = request.POST.get('product_id')

        # Lấy sản phẩm để cập nhật
        product = get_object_or_404(Product, product_id=product_id)
        
        # Khởi tạo form với dữ liệu POST
        product_form = ProductForm(request.POST, instance=product)
        product_sale_form = ProductSaleForm(request.POST)
        types = request.POST.getlist('type')
        quantities = request.POST.getlist('quantity')

        # Kiểm tra nếu có file
        if request.FILES:
            product_image_form = ProductImageForm(request.POST, request.FILES)
        else:
            product_image_form = ProductImageForm(request.POST)  # Không có file

        if product_form.is_valid() and product_sale_form.is_valid() and product_image_form.is_valid():
            product = product_form.save()  # Cập nhật thông tin sản phẩm
            # product_sale = ProductSale(price=product_sale_form.cleaned_data['price'], product=product)
            # product_sale.save()

            # Cập nhật chi tiết sản phẩm
            ProductDetail.objects.filter(product=product).delete()
            for i in range(len(types)):
                product_detail = ProductDetail(type=types[i], quantity=quantities[i], product=product)
                product_detail.save()

            if request.FILES:
                ProductImage.objects.filter(product=product).delete()
            images = request.FILES.getlist('product_images')
            for image in images:
                product_image = ProductImage(name=image, product=product)
                product_image.save()
            imagesOld = request.FILES.getlist('product_images_old')
            for image in imagesOld:
                product_image = ProductImage(name=image, product=product)
                product_image.save()

            messages = "Cập nhật sản phẩm thành công"
        else:
            error = 'Bạn cần nhập đầy đủ thông tin'
            print("Product Form Errors:", product_form.errors)
            print("Product Sale Form Errors:", product_sale_form.errors)
            print("Product Image Form Errors:", product_image_form.errors)
    else:
        product_id = int(request.GET.get('product_id'))
    product_form = Product.objects.get(product_id=product_id)
    product_detail = ProductDetail.objects.filter(product=product_form).all()
    images = ProductImage.objects.filter(product_id=product_id).values('name')

    return render(request, 'admin_shop/product/edit-product.html', {
        'product_form': product_form,
        'error': error,
        'messages': messages,
        'categories': categories,
        'product_detail': product_detail,
        'years': years
    })


@login_required(login_url='/login')
def addCoupon(request):
    error = ''
    messages = '' 
    if request.method == "POST":
        coupon_form = CouponForm(request.POST)
        if coupon_form.is_valid():
            coupon_form.save()
            coupon_form = Coupon()
            messages = "Thêm mã giảm giá thành công"
        else:
            error = 'Mã giảm giá đã tồn tại trong hệ thống'
    else:
        coupon_form = CouponForm()
    return render(request, 'admin_shop/coupon/add-coupon.html', {'coupon_form': coupon_form, 'error': error, 'messages': messages})

@login_required(login_url='/login')
def editCoupon(request):
    messages = '' 
    error = ''
    if request.method == "POST":
        coupon_id = request.POST.get('coupon_id')
        print(coupon_id)
        coupon = get_object_or_404(Coupon, coupon_id=coupon_id)
        form = CouponForm(request.POST, instance=coupon)

        if form.is_valid():
            form.save()
            messages = "Cập nhật mã giảm giá thành công"
        else:
            error = 'Mã giảm giá đã tồn tại trong hệ thống'
    else:
        coupon_id = int(request.GET.get('coupon_id'))
    form = Coupon.objects.get(coupon_id=coupon_id)
    start_date = form.start_date
    end_date = form.end_date
    form.start_date = start_date.strftime('%Y-%m-%d')
    form.end_date = end_date.strftime('%Y-%m-%d')

    return render(request, 'admin_shop/coupon/edit.html',
        {'form': form, 'error': error, 'messages' : messages})

@login_required(login_url='/login')
def deleteCoupon(request):
    coupon_id = int(request.GET.get('coupon_id'))
    coupon = Coupon.objects.get(coupon_id=coupon_id)
    coupon.delete()
    return JsonResponse({
        'success': True,
        'message': "Danh mục đã được xóa thành công"
    })


@login_required(login_url='/login')
def couponManager(request):
    keyword = request.GET.get('keyword', '')
    coupons = Coupon.objects.filter(code__icontains=keyword).order_by('-coupon_id')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    if start_date == '' and end_date == '':
        coupons = coupons.all()
    elif end_date == '':
        coupons = coupons.filter(start_date__gte=start_date)
    elif start_date == '':
        coupons = coupons.filter(end_date__lte=end_date)
    else:
        coupons = coupons.filter(Q(start_date__gte=start_date) & Q(end_date__lte=end_date))

    paginator = Paginator(coupons, 15)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin_shop/coupon/coupons.html', {'page_obj': page_obj})


@login_required(login_url='/login')
def productManager(request):
    categories = Category.objects.all()
    if request.method == "POST":
        keyword = request.POST.get('keyword', '')
        products = Product.objects.filter(name__icontains=keyword).annotate(
            total_quantity=Sum('productdetail__quantity')).order_by('-product_id')
        category = request.POST.get('category')
        status = request.POST.get('status')
        if category:
            products = products.filter(category__name=category)
        if status:
            if status == 'Còn hàng':
                products = products.filter(total_quantity__gt=0)
            else:
                products = products.filter(total_quantity=0)
    else:
        keyword = request.GET.get('keyword', '')
        products = Product.objects.filter(name__icontains=keyword).annotate(
            total_quantity=Sum('productdetail__quantity')).order_by('-product_id')
        category = request.GET.get('category')
        status = request.GET.get('status')
        if category:
            products = products.filter(category__name=category)
        if status:
            if status == 'Còn hàng':
                products = products.filter(total_quantity__gt=0)
            else:
                products = products.filter(total_quantity=0)
    paginator = Paginator(products, 15)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin_shop/product/products.html', {'page_obj': page_obj, 'categories': categories})


@login_required(login_url='/login')
def getProductDetailAdmin(request):
    if request.method == "POST":
        feedback_id = int(request.GET.get('feedback_id'))
        response_form = ResponseForm(request.POST)
        if response_form.is_valid():
            text = response_form.cleaned_data.get("textfield")
            response = FeedbackRespone(comment=text, feedback_id=feedback_id)
            response.save()

    product_id = int(request.GET.get('product_id'))
    product = Product.objects.filter(pk=product_id).annotate(
        # curr_price=Case(
        #     When(productsale__start_date__lte=timezone.now(),
        #          productsale__end_date__gte=timezone.now(),
        #          then=F('productsale__price')),
        #     default=F('price'),
        #     output_field=FloatField()
        # ),
    ).first()

    feedback = Feedback.objects.filter(product=product).order_by('-date')
    feedback_paginator = Paginator(feedback, 5)
    feedback_page = request.GET.get('page')
    page_obj = feedback_paginator.get_page(feedback_page)
    feedbacks = page_obj.object_list
    response_form = ResponseForm()
    context = {
        'product': product,
        'feedbacks': feedbacks,
        'page_obj': page_obj,
        'response_form': response_form
    }
    return render(request, 'admin_shop/product/product-detail.html', context)


@login_required(login_url='/login')
def customerManager(request):
    keyword = request.GET.get('keyword', '')
    customers = User.objects.filter(name__icontains=keyword, is_superuser=0).annotate(
        total_orders=Count('order', filter=Q(order__status_id=6)),
        total_orders_canceled=Count('order', filter=Q(order__status_id=5)),
        total_amount=Coalesce(Sum('order__total', filter=Q(order__status_id=6)), Value(0.0)),
        type_customer=Case(
            When(total_amount__gte=20000000, then=Value('VIP3')),
            When(total_amount__gte=10000000, then=Value('VIP2')),
            When(total_amount__gte=5000000, then=Value('VIP1')),
            When(total_orders_canceled__gte=1, then=Value('BLACKLIST')),
            default=Value('Thường')
        )
    )

    type_customer = request.GET.get('type_customer', 'Tất cả')
    if type_customer != 'Tất cả':
        customers = customers.filter(type_customer=type_customer)

    paginator = Paginator(customers, 15)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin_shop/customer/customers.html', {'page_obj': page_obj})


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
        if order.status.order_status_id != status:
            status = OrderStatus.objects.get(order_status_id=status)
            order.status = status
            order.save()
            tracking = Tracking(order=order, order_status=status)
            tracking.save()
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
    else:
        status_ids = [6]
    states = OrderStatus.objects.filter(order_status_id__in=status_ids).order_by("order_status_id")
    return render(request, 'admin_shop/order/order-detail.html',
                  {'order': order, 'order_items': order_items, 'states': states, 'price_order': price_order, })


@login_required(login_url='/login')
def report(request):
    if request.method == "POST":
        columns = []
        values = []
        type_report = request.POST.get('type_report', 1)
        start_date = request.POST.get('start_date', '')
        end_date = request.POST.get('end_date', '')
        if start_date == '':
            start_date = timezone.datetime(2020, 1, 1)
        if end_date == '':
            end_date = timezone.datetime(2050, 12, 31)
        if type_report == '1':
            report = Order.objects.filter(date__gte=start_date, date__lte=end_date).annotate(
                month=TruncMonth('date')).values('month').annotate(revenue=Sum('total')).values(
                'month', 'revenue').order_by('month')
            for record in report:
                record['month'] = record['month'].strftime('%m %Y').split()
                record['month'] = 'Tháng ' + record['month'][0] + ' năm ' + record['month'][1]
                columns.append(record['month'])
                values.append(int(record['revenue']))
            report_name = 'Báo cáo doanh thu theo tháng'
        elif type_report == '2':
            report = Order.objects.filter(date__gte=start_date, date__lte=end_date, status_id=7).annotate(
                month=TruncMonth('date')).values('month').annotate(order_total=Count('order_id')).values(
                'month', 'order_total').order_by('month')
            for record in report:
                record['month'] = record['month'].strftime('%m %Y').split()
                record['month'] = 'Tháng ' + record['month'][0] + ' năm ' + record['month'][1]
                columns.append(record['month'])
                values.append(record['order_total'])
            report_name = 'Báo cáo đơn hàng'
        else:
            report = Order.objects.filter(date__gte=start_date, date__lte=end_date, status_id=7).select_related(
                'customer').values('customer__name').annotate(total=Sum('total')).order_by('total')
            for record in report:
                columns.append(record['customer__name'])
                values.append(record['total'])
            report_name = 'Báo cáo khách hàng'
        return render(request, 'admin_shop/report.html',
                      {'values': values, 'columns': columns, 'report_name': report_name})
    else:
        return render(request, 'admin_shop/report.html')


@login_required(login_url='/login')
def deleteProduct(request):
    product_id = int(request.GET.get('product_id'))
    product = Product.objects.get(product_id=product_id)
    images = ProductImage.objects.filter(product=product).values('name')
    for image in images:
        if os.path.exists(f"app/media/{image['name']}"):
            os.remove(f"app/media/{image['name']}")
    product.delete()
    products = Product.objects.all()
    categories = Category.objects.all()

    paginator = Paginator(products, 15)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    return redirect('/products', {'page_obj': page_obj, 'categories': categories})


@login_required(login_url='/login')
def viewProfile(request):
    user_id = int(request.GET.get('user_id'))
    if request.user.is_superuser == 1:
        user = User.objects.get(id=user_id)
        diff = date.today() - user.date_joined.date()
        time = convert_diff(diff)

        if user.is_superuser != 1:
            day_last_order = 0

            last_order = Order.objects.filter(customer=user).last()
            if last_order: 
                day_last_order = timezone.now() - last_order.date
                day_last_order = convert_diff(day_last_order)

            orders = Order.objects.filter(customer=user)
            total_order = orders.count()
            total_order_new = orders.filter(status=1).count()
            total_order_confirmed = orders.filter(status=2).count()
            total_order_prepare = orders.filter(status=3).count()
            total_order_delivering = orders.filter(status=4).count()
            total_order_canceled = orders.filter(status=5).count()
            total_order_success = orders.filter(status=6).count()

            total_money = orders.aggregate(
                total_money=Sum('total'))['total_money']
            total_money_success = orders.filter(status__name='Giao hàng thành công').aggregate(
                total_money=Sum('total'))['total_money']
            context = {
                'user': user,
                'day_last_order': day_last_order,
                'total_order': total_order,
                'total_order_new': total_order_new,
                'total_order_confirmed': total_order_confirmed,
                'total_order_preparing': total_order_prepare,
                'total_order_delivering': total_order_delivering,
                'total_order_canceled': total_order_canceled,
                'total_order_success': total_order_success,
                'total_money': total_money,
                'total_money_success': total_money_success,
                'time': time
            }
        else:
            context = {
                'user': user,
                'time': time
            }
    else:
        return redirect('/home')
    return render(request, 'admin_shop/customer/profile.html', context=context)

@login_required(login_url='/login')
def categoryManager(request):
    keyword = request.GET.get('keyword', '')
    categories = Category.objects.filter(name__icontains=keyword)
    paginator = Paginator(categories, 15)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    print(page_obj.__dict__)
    return render(request, 'admin_shop/category/index.html', {'page_obj': page_obj})

@login_required(login_url='/login')
def addCategory(request):
    messages = '' 
    error = ''
    if request.method == 'POST':
        form = CategoryForm(request.POST or None)
        if form.is_valid():
            form.save()
            messages = "Thêm danh mục thành công"
        else:
            if request.method == 'POST':
                error = 'Tên danh mục đã tồn tại'
            else:
                error = ''
    else:
        form = CategoryForm()
    return render(request, 'admin_shop/category/add.html',
                  {'form': form, 'error': error, 'messages' : messages})

@login_required(login_url='/login')
def editCategory(request):
    messages = '' 
    error = ''
    if request.method == "POST":
        category_id = request.POST.get('category_id')
        category = get_object_or_404(Category, category_id=category_id)
        print(category_id, category.__dict__)
        form = CategoryForm(request.POST, instance=category)

        if form.is_valid():
            form.save()
            messages = "Cập nhật danh mục thành công"
        else:
            error = 'Tên danh mục đã tồn tại'
    else:
        category_id = int(request.GET.get('category_id'))
    form = Category.objects.get(category_id=category_id)

    return render(request, 'admin_shop/category/edit.html',
        {'form': form, 'error': error, 'messages' : messages})

@login_required(login_url='/login')
def deleteCategory(request):
    category_id = int(request.GET.get('category_id'))
    category = Category.objects.get(category_id=category_id)
    if Product.objects.filter(category_id=category_id).exists():
        return JsonResponse({
            'success': False,
            'message': "Danh mục không thể xóa do đã có sản phẩm"
        })
    else:
        category.delete()
        categories = Category.objects.all()
        paginator = Paginator(categories, 15)

        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)
        return JsonResponse({
            'success': True,
            'message': "Danh mục đã được xóa thành công"
        })

# CategoryPost
@login_required(login_url='/login')
def categoryPostManager(request):
    keyword = request.GET.get('keyword', '')
    categories = CategoryPost.objects.filter(name__icontains=keyword)
    paginator = Paginator(categories, 15)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    print(page_obj.__dict__)
    return render(request, 'admin_shop/category_post/index.html', {'page_obj': page_obj})

@login_required(login_url='/login')
def addCategoryPost(request):
    messages = '' 
    error = ''
    if request.method == 'POST':
        form = CategoryPostForm(request.POST or None)
        if form.is_valid():
            form.save()
            messages = "Thêm danh mục thành công"
        else:
            if request.method == 'POST':
                error = 'Tên danh mục đã tồn tại'
            else:
                error = ''
    else:
        form = CategoryPostForm()
    return render(request, 'admin_shop/category_post/add.html',
                  {'form': form, 'error': error, 'messages' : messages})

@login_required(login_url='/login')
def editCategoryPost(request):
    messages = '' 
    error = ''
    if request.method == "POST":
        category_id = request.POST.get('category_id')
        category = get_object_or_404(CategoryPost, category_id=category_id)
        print(category_id, category.__dict__)
        form = CategoryPostForm(request.POST, instance=category)

        if form.is_valid():
            form.save()
            messages = "Cập nhật danh mục thành công"
        else:
            error = 'Tên danh mục đã tồn tại'
    else:
        category_id = int(request.GET.get('category_id'))
    form = CategoryPost.objects.get(category_id=category_id)

    return render(request, 'admin_shop/category_post/edit.html',
        {'form': form, 'error': error, 'messages' : messages})

@login_required(login_url='/login')
def deleteCategoryPost(request):
    category_id = int(request.GET.get('category_id'))
    category = CategoryPost.objects.get(category_id=category_id)
    if Post.objects.filter(category_id=category_id).exists():
        return JsonResponse({
            'success': False,
            'message': "Danh mục không thể xóa do đã có bài viết"
        })
    else:
        category.delete()
        categories = CategoryPost.objects.all()
        paginator = Paginator(categories, 15)

        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)
        return JsonResponse({
            'success': True,
            'message': "Danh mục đã được xóa thành công"
        })

# Post
@login_required(login_url='/login')
def postManager(request):
    categories = CategoryPost.objects.all()
    if request.method == "POST":
        keyword = request.POST.get('keyword', '')
        posts = Post.objects.filter(title__icontains=keyword).order_by('-post_id')
        category = request.POST.get('category')
        if category:
            posts = posts.filter(category__name=category)
    else:
        keyword = request.GET.get('keyword', '')
        posts = Post.objects.filter(title__icontains=keyword).order_by('-post_id')
        category = request.GET.get('category')
        if category:
            posts = posts.filter(category__name=category)
    paginator = Paginator(posts, 15)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin_shop/post/index.html', {'page_obj': page_obj, 'categories': categories})


@login_required(login_url='/login')
def addPost(request):
    messages = '' 
    error = ''
    categories = CategoryPost.objects.filter(is_active = 1)
    if request.method == 'POST':
        form = PostForm(request.POST or None)
        if form.is_valid():
            form.save()
            messages = "Thêm bài viết thành công"
        else:
            if request.method == 'POST':
                error = form.errors
            else:
                error = ''
    else:
        form = PostForm()
    return render(request, 'admin_shop/post/add.html', {
        'form': form,
        'error': error,
        'messages': messages,
        'categories': categories,
    })

@login_required(login_url='/login')
def editPost(request):
    messages = '' 
    error = ''
    categories = CategoryPost.objects.filter(is_active = 1)
    if request.method == "POST":
        post_id = request.POST.get('post_id')
        post = get_object_or_404(Post, post_id=post_id)
        print(post_id, post.__dict__)
        form = PostForm(request.POST, instance=post)

        if form.is_valid():
            form.save()
            messages = "Cập nhật bài viết thành công"
        else:
            error = 'Tên bài viết đã tồn tại'
    else:
        post_id = int(request.GET.get('post_id'))
    form = Post.objects.get(post_id=post_id)

    return render(request, 'admin_shop/post/edit.html', {
        'form': form,
        'error': error,
        'messages': messages,
        'categories': categories,
    })

@login_required(login_url='/login')
def deletePost(request):
    post_id = int(request.GET.get('post_id'))
    post = Post.objects.get(post_id=post_id)
    post.delete()
    return JsonResponse({
        'success': True,
        'message': "bài viết đã được xóa thành công"
    })