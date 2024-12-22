from django.shortcuts import render, get_object_or_404, redirect
from ..models import *
from django.db.models import Sum
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from ..forms import *
from datetime import datetime
from django.utils import timezone
import csv
from django.http import HttpResponse
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


def recommend_products(user_id, num_recommendations=5):
    # Lấy dữ liệu feedback
    feedbacks = Feedback.objects.all()
    data = {}

    # Lấy ra mảng các user và lần lượt từng sản phẩm với đánh giá của user đó
    for feedback in feedbacks:
        user = feedback.customer.id
        product = feedback.product.product_id
        rating = feedback.rating

        if user not in data:
            data[user] = {}
        if product in data[user]:
            current_total_rating, current_count = data[user][product]
            new_total_rating = current_total_rating + rating
            new_count = current_count + 1
            data[user][product] = (new_total_rating, new_count)
        else:
            data[user][product] = (rating, 1)

    # Tính trung bình đánh giá cho từng user / từng sản phẩm
    for user, products in data.items():
        for product, (total_rating, num_ratings) in products.items():
            average_rating = total_rating / num_ratings
            data[user][product] = average_rating

    if not data:  # Nếu không có feedback nào thì lấy ngẫu nhiên product
        return Product.objects.all()[:num_recommendations]
    
    # Xây dựng ma trận user-product, Fill NaN với 0 nếu không có đánh giá
    ratings_df = pd.DataFrame(data).T.fillna(0)

    print("              ")

    # Kiểm tra nếu user chưa có lịch sử đánh giá => Gợi ý các sản phẩm có nhiều lượt rating nhất
    if user_id not in ratings_df.index:
        popular_products = (
            Feedback.objects.values('product')
            .annotate(total_ratings=models.Count('rating'))
            .order_by('-total_ratings')
        )
        product_ids = [p['product'] for p in popular_products[:num_recommendations]]
        return Product.objects.filter(product_id__in=product_ids)

    # Tính toán độ tương đồng giữa người dùng, lấy ra người dùng có độ tương đồng cao nhất
    user_similarity = cosine_similarity(ratings_df)
    user_similarity_df = pd.DataFrame(user_similarity, index=ratings_df.index, columns=ratings_df.index)

    
    # Gợi ý sản phẩm dựa trên sự tương đồng mua sắm giữa các user
    def recommend_for_user(user_id, ratings_df, user_similarity_df):
        # Sort list user có độ tương đồng giảm dần (ngoại trừ chính user đó)
        similar_users = user_similarity_df[user_id].sort_values(ascending=False).drop(user_id)

        print(similar_users)   
        
        # Tìm sản phẩm user chưa mua
        user_ratings = ratings_df.loc[user_id] # lấy ra các sản phẩm sort theo rating của user
        products_bought = user_ratings[user_ratings > 0].index # Lấy ra id sản phẩm đã mua có rating > 0
        recommendations = {}

        # Tính toán lấy ra các sản phẩm chưa mua và độ tương đồng tương ứng
        for other_user, similarity in similar_users.items():
            other_user_ratings = ratings_df.loc[other_user]
            for product, rating in other_user_ratings.items():
                if product not in products_bought and rating > 0:
                    if product not in recommendations:
                        recommendations[product] = 0
                    recommendations[product] += similarity * rating

        # Sắp xếp các sản phẩm theo thứ tự độ tương đồng giảm dần
        sorted_recommendations = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)
        # Kết quả: danh sách các sản phẩm (chưa được mua), mà các user khác có độ tương đồng cao đã từng mua và có rating cao
        return [product for product, score in sorted_recommendations[:num_recommendations]]

    recommended_product_ids = recommend_for_user(user_id, ratings_df, user_similarity_df)
    print("recommended_product_ids: ", recommended_product_ids)
    recommended_products = Product.objects.filter(product_id__in=recommended_product_ids)
    return recommended_products


def home(request):
    now = timezone.now()

    products = Product.objects.distinct()

    top_selling_products = products.order_by('-total_sold')[:10]

    top_sale_products = products.filter(sale__gt=0).order_by('-sale')[:10]

    hot_selling_product = (products.filter(orderitem__order__date__month=now.month,
                                           orderitem__order__date__year=now.year)
                           .annotate(total_sold_month=Sum('orderitem__quantity'))
                           .order_by('-total_sold_month')
                           )[:10]
    
    if request.user.id:
        recommended_products = recommend_products(request.user.id)
    else:
        recommended_products = None

    context = {
        'top_selling_products': top_selling_products,
        'top_sale_products': top_sale_products,
        'hot_selling_products': hot_selling_product,
        'range': range(10),
        'recommended_products': recommended_products,
    }

    return render(request, 'customer/home.html', context)

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
            if userCheck.is_superuser:
                return render(request, 'customer/login.html', {
                    'error': 'Tên đăng nhập hoặc mật khẩu không đúng'
                })
        except User.DoesNotExist:
            return render(request, 'customer/login.html', {
                'error': 'Tên đăng nhập hoặc mật khẩu không đúng'
            })

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            return render(request, 'customer/login.html', {'error': 'Tên đăng nhập hoặc mật khẩu không đúng'})

def log_in_admin(request):
    if request.method == 'GET':
        return render(request, 'admin_shop/login.html')
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        try:
            userCheck = User.objects.get(username=username)
            if not userCheck.is_active:
                return render(request, 'admin_shop/login.html', {
                    'error': 'Tài khoản của bạn đã bị khóa. Vui lòng liên hệ với quản trị viên.'
                })
            if not userCheck.is_superuser:
                return render(request, 'admin_shop/login.html', {
                    'error': 'Tên đăng nhập hoặc mật khẩu không đúng'
                })
        except User.DoesNotExist:
            return render(request, 'admin_shop/login.html', {
                'error': 'Tên đăng nhập hoặc mật khẩu không đúng'
            })

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/dashboard')
        else:
            return render(request, 'admin_shop/login.html', {'error': 'Tên đăng nhập hoặc mật khẩu không đúng'})


def log_out(request):
    logout(request)
    return redirect('/')

def log_out_admin(request):
    logout(request)
    return redirect('/login-admin')

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

@login_required(login_url='/login')
def report(request):
    columns = []
    valuesRevenue = []
    valuesCount = []
    columnsTopCustomer = []
    valuesTopCustomer = []
    columnsTopProduct = []
    valuesTopProduct = []
    type_report = request.GET.get('type_report', '1')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    startDate = start_date
    endDate = end_date
    if start_date == '':
        start_date = timezone.datetime(2020, 1, 1)
    if end_date == '':
        end_date = timezone.datetime(2050, 12, 31)

    # Báo cáo doanh thu, đơn hàng theo tháng
    report_name1 = 'Báo cáo doanh thu theo tháng (VNĐ)'
    report_name2 = 'Báo cáo tổng đơn hàng theo tháng (Đơn)'
    report = Order.objects.filter(date__gte=start_date, date__lte=end_date).exclude(status_id=5).annotate(
        month=TruncMonth('date')).values('month').annotate(revenue=Sum('total')).values(
        'month', 'revenue').order_by('month')
    for record in report:
        record['month'] = record['month'].strftime('%m %Y').split()
        record['month'] = record['month'][0] + '/' + record['month'][1]
        columns.append(record['month'])
        valuesRevenue.append(int(record['revenue']))

    reportCount = Order.objects.filter(date__gte=start_date, date__lte=end_date).exclude(status_id=5).annotate(
        month=TruncMonth('date')).values('month').annotate(order_total=Count('order_id')).values(
        'month', 'order_total').order_by('month')
    for record2 in reportCount:
        valuesCount.append(record2['order_total'])

    
    # Báo cáo top khách hàng mua nhiều
    report_name_top_customer = 'Báo cáo top 5 khách hàng chi tiêu nhiều nhất'
    reportTopCustomer = (
        Order.objects.filter(date__gte=start_date, date__lte=end_date).exclude(status_id=5)
        .select_related('customer')
        .values('customer__id', 'customer__name', 'customer__username')
        .annotate(total=Sum('total'))
        .order_by('-total')[:5]
    )

    for record3 in reportTopCustomer:
        columnsTopCustomer.append(record3['customer__name'] + " (" + record3['customer__username'] + ")")
        valuesTopCustomer.append(record3['total'])

    # Báo cáo top khách hàng mua nhiều
    report_name_top_product = 'Báo cáo top 5 sản phẩm bán chạy nhất'
    reportTopProduct = (
        OrderItem.objects.filter(order__date__gte=start_date, order__date__lte=end_date).exclude(order__status_id=5)
        .values('product__name')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('-total_quantity')[:5]
    )

    for record4 in reportTopProduct:
        columnsTopProduct.append(record4['product__name'])
        valuesTopProduct.append(record4['total_quantity'])

    return render(request, 'admin_shop/report.html',
        {   
            'report_name1': report_name1,
            'report_name2': report_name2,
            'columns': columns, 
            'valuesRevenue': valuesRevenue,
            'valuesCount': valuesCount,
            'report_name_top_customer': report_name_top_customer,
            'columnsTopCustomer': columnsTopCustomer,
            'valuesTopCustomer': valuesTopCustomer,
            'report_name_top_product': report_name_top_product,
            'columnsTopProduct': columnsTopProduct,
            'valuesTopProduct': valuesTopProduct,
            'type_report': type_report,
            'startDate': startDate,
            'endDate': endDate,
        }
    )


def export_orders(request):
    start_date = request.GET.get('startDate')
    end_date = request.GET.get('endDate')

    filename = "Bao_cao_doanh_thu.csv"
    if start_date and end_date:
        filename = f"Bao_cao_doanh_thu_tu_ngay_{start_date}_den_{end_date}.csv"
    elif start_date:
        filename = f"Bao_cao_doanh_thu_tu_ngay_{start_date}.csv"
    elif end_date:
        filename = f"Bao_cao_doanh_thu_den_ngay_{end_date}.csv"

    orders = Order.objects.all().order_by('order_id')
    if start_date and end_date:
        orders = orders.filter(date__gte=start_date, date__lte=end_date)

    orders = orders.values(
        'order_id', 'date', 'discount', 'shipping', 'total',
        'status__name', 'payment_method', 'receiver', 'phone', 'address'
    )

    # Tạo file CSV như trước
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(['Mã đơn hàng', 'Ngày đặt hàng', 'Tổng tiền',
                     'Trạng thái', 'Phương thức thanh toán', 'Khách hàng', 'Số điện thoại', 'Địa chỉ'])

    for order in orders:
        formatted_date = order['date'].strftime("%H:%M:%S %d/%m/%Y") if isinstance(order['date'], datetime) else order['date']
        formatted_total = f"{order['total']:,.0f} VNĐ".replace(',', '.')
        writer.writerow([
            order['order_id'], formatted_date, formatted_total, order['status__name'],
            order['payment_method'], order['receiver'], order['phone'], order['address']
        ])

    return response