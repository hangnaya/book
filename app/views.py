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
