from django.shortcuts import render, get_object_or_404, redirect
from ..models import *
from django.db.models import F, FloatField, ExpressionWrapper, Sum, Value, CharField, Case, When
from django.db.models.functions import Coalesce, Round
from django.db.models import F, FloatField, ExpressionWrapper, Sum, Value, CharField, Count, Case, When
from django.db.models.functions import Coalesce, Round, TruncMonth
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from ..serializers import ProductSerializer, FeedbackSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from django.views.decorators.csrf import csrf_exempt
import locale
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from ..forms import *
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
import paypalrestsdk
from django.conf import settings
from django.db import transaction
import hashlib
import hmac
import urllib.parse
from app.vnpay import vnpay
import random
import csv
from django.http import HttpResponse
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

def getCoupon(request):
    coupons = Coupon.objects.filter(start_date__lte=timezone.now(), end_date__gte=timezone.now()).order_by(
        '-start_date')
    paginator = Paginator(coupons, 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'coupons': page_obj.object_list
    }
    return render(request, 'customer/list-coupon.html', context)

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
