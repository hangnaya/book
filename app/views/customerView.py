from django.shortcuts import render, get_object_or_404, redirect
from ..models import *
from django.db.models import Sum, Value, Case, When
from django.db.models.functions import Coalesce, Round
from django.db.models import Sum, Value, Count, Case, When
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from ..forms import *
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import date

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

def profile(request):
    user = request.user
    created_at = user.date_joined
    day_created = timezone.now() - created_at
    day_created = convert_diff(day_created) + ' trước'
    last_order = Order.objects.filter(customer=user).last()
    today = timezone.now()
    if last_order:
        day_last_order = timezone.now() - last_order.date
        day_last_order = convert_diff(day_last_order)
        day_last_order += ' trước'
    else:
        day_last_order = 'Chưa đặt hàng'
    orders = Order.objects.filter(customer=user)
    total_order = orders.count()
    total_order_new = orders.filter(status=1).count()
    total_order_confirmed = orders.filter(status=2).count()
    total_order_prepare = orders.filter(status=3).count()
    total_order_delivering = orders.filter(status=4).count()
    total_order_canceled = orders.filter(status=5).count()
    total_order_success = orders.filter(status=6).count()

    total_money = orders.aggregate(total_money=Sum('total', default=0))['total_money']
    total_money_success = orders.filter(status__name='Giao hàng thành công').aggregate(
                total_money=Sum('total'))['total_money']
    context = {
        'user': user,
        'day_created': day_created,
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
        'today': today,
        'messages': '',
        'error': '',
    }

    if request.method == 'POST':
        form = UserForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            context['messages']= 'Cập nhật thông tin thành công'
        else:
            context['error'] = form.errors
        context['form'] = form
        isAdmin = request.POST.get('isAdmin')
        if isAdmin:
            return render(request, 'admin_shop/customer/profile.html', context=context)
    return render(request, 'customer/profile.html', context)

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
        return redirect('/')
    return render(request, 'admin_shop/customer/profile.html', context=context)


def updateStatus(request):
    user_id = int(request.POST.get('user_id'))
    is_active = int(request.POST.get('is_active'))
    user = User.objects.get(id=user_id)
    user.is_active = is_active
    user.save()
    return JsonResponse({'status': 'true'})
