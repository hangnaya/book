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

def getPost(request):
    categories = CategoryPost.objects.filter(is_active = 1)
    keyword = request.GET.get('keyword', '')
    posts = Post.objects.filter(title__icontains=keyword, is_active = 1).order_by('-post_id')
    category = request.GET.get('category', '')
    if category:
        posts = posts.filter(category__name=category)
    paginator = Paginator(posts, 12)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    context = {
        'categories': categories,
        'keyword': keyword,
        'page_obj': page_obj,
        'category': category,
    }
    return render(request, 'customer/list-post.html', context)

def postDetail(request, post_id):
    post = get_object_or_404(Post, post_id=post_id)
    post.views += 1
    post.save()
    other_posts = Post.objects.filter(category_id=post.category_id, is_active = 1).exclude(post_id=post.post_id)[:5]

    return render(request, 'customer/post-detail.html', {
        'post': post,
        'other_posts': other_posts,
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
        print(request.POST)
        form = PostForm(request.POST or None, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()
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
        # form = PostForm(request.POST, instance=post)

        # if form.is_valid():
        #     form.save()
        #     messages = "Cập nhật bài viết thành công"
        # else:
        #     error = 'Tên bài viết đã tồn tại'
        form = PostForm(request.POST, request.FILES, instance=post)

        if form.is_valid():
            new_post = form.save(commit=False)
            print(request.FILES)
            if 'image' in request.FILES:
                new_post.image = request.FILES['image']
            new_post.save()
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
    if post.image:  # Kiểm tra xem trường image có giá trị hay không
        image_path = post.image.path  # Lấy đường dẫn đến tệp ảnh
        if os.path.exists(image_path):
            os.remove(image_path) 
    post.delete()
    return JsonResponse({
        'success': True,
        'message': "bài viết đã được xóa thành công"
    })