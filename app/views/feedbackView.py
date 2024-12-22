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

def handleFeedback(request):
    if request.method == 'GET':
        order_id = request.GET.get('order_id')
        order = Order.objects.get(pk=order_id)
        context = {
            'order': order
        }

    if request.method == 'POST':
        orderitem_id = request.POST.get('order_item_id')
        orderitem = OrderItem.objects.get(pk=orderitem_id)
        product = orderitem.product
        comment = request.POST.get('comment')
        rating = request.POST.get('rating')
        images = request.FILES.getlist('images')
        feedback = Feedback.objects.create(
            comment=comment,
            rating=rating,
            product=product,
            customer=request.user
        )
        feedback.save()
        for image in images:
            feedback_image = FeedbackImage(name=image, feedback=feedback)
            feedback_image.save()
        orderitem.feedback = feedback
        orderitem.save()

        order = orderitem.order
        context = {
            'order': order
        }

    return render(request, 'customer/feedback.html', context)


@login_required(login_url='/login')
def getFeedback(request):
    feedbacks = Feedback.objects.filter(customer=request.user).order_by('-date')
    paginator = Paginator(feedbacks, 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'feedbacks': page_obj.object_list
    }
    return render(request, 'customer/list-feedback.html', context)


@api_view(['GET'])
def getFeedbackByProduct(request):
    product_id = int(request.GET.get('product_id'))
    product = Product.objects.get(pk=product_id)
    feedbacks = Feedback.objects.filter(product=product).order_by('-date')
    paginator = PageNumberPagination()
    paginator.page_query_param = 'page'
    paginator.page_size = 5
    result_page = paginator.paginate_queryset(feedbacks, request)
    serializer = FeedbackSerializer(result_page, many=True, context={'request': request})

    respone = paginator.get_paginated_response(serializer.data)
    respone.data['current_page'] = paginator.page.number
    respone.data['total_page'] = paginator.page.paginator.num_pages
    return respone

@api_view(['POST'])
def ReactFeedbackByProduct(request):
    type = int(request.POST.get('type'))
    action = int(request.POST.get('action'))
    feedback_id = int(request.POST.get('feedback_id'))
    feedback = get_object_or_404(Feedback, feedback_id=feedback_id)

    if type == 1:
        if action == 1:
            feedback.like += 1
        elif action == 2:
            feedback.like -= 1
        elif action == 3:
            feedback.like += 1
            feedback.dislike -= 1
    elif type == 2:
        if action == 1:
            feedback.dislike += 1
        elif action == 2:
            feedback.dislike -= 1
        elif action == 3:
            feedback.dislike += 1
            feedback.like -= 1
    
    feedback.save()
    return JsonResponse({'status': 'true'})

@api_view(['POST'])
def ReadFeedback(request):
    feedback_id = int(request.POST.get('feedback_id'))
    feedback = get_object_or_404(Feedback, feedback_id=feedback_id)
    feedback.is_read = 1
    feedback.save()
    return JsonResponse({'status': 'true'})




def notification(request):
    notifications = Notification.objects.filter(customer=request.user).all().order_by('is_read', '-create_at')
    return render(request, 'customer/notification.html', {'notifications' : notifications})


