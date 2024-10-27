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

