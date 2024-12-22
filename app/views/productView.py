from django.shortcuts import render, get_object_or_404, redirect
from ..models import *
from django.db.models import Sum
from django.db.models import Sum
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login, logout
from ..serializers import ProductSerializer
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth.decorators import login_required
from ..forms import *
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
import os
from django.db.models import Avg


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


def listProduct(request):
    search = request.GET.get('search')
    category_id = request.GET.get('category')
    sub_category_id = request.GET.get('subcate')
    category_selected = None
    if category_id:
        category_parent = Category.objects.filter(category_id = category_id).first()
        categories = Category.objects.filter(parent_id = category_id)
    else:
        categories = Category.objects.all()
        category_parent = None

    category_ids = ','.join(str(category.category_id) for category in categories)

    if sub_category_id:
        category_selected =  categories.filter(category_id = sub_category_id).first()
    context = {
        'categoriesFilter': categories,
        'search': search,
        'selected_category_id': sub_category_id,
        'category_selected': category_selected,
        'category_parent': category_parent,
        'category_ids': category_ids,
    }
    return render(request, 'customer/list-product.html', context)


@api_view(['GET'])
def getListProduct(request):
    search = request.GET.get('search')

    category = request.GET.get('category')
    if category:
        category = [int(category) for category in category.split(',')]

    type = request.GET.get('type')
    if type:
        type = [type for type in type.split(',')]

    age = request.GET.get('age')
    if age:
        age = [age for age in age.split(',')]

    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    # rating = request.GET.get('rating')
    sort = request.GET.get('sort')

    products = Product.objects.annotate(
        quantity=Sum('productdetail__quantity')
    )

    if search is not None and search != '':
        products = products.filter(name__icontains=search)

    if category:
        categories = Category.objects.filter(category_id__in=category)
        products = products.filter(category__in=categories)

    if age and len(age) == 1:
        if age[0] == '1':
            products = products.filter(age__gte=18)
        elif age[0] == '2':
            products = products.filter(age__gte=15)
        elif age[0] == '3':
            products = products.filter(age__gte=11)
        elif age[0] == '4':
            products = products.filter(age__gte=5)

    if type and len(type) == 1:
        if type[0] == '0':
            products = products.filter(productdetail__type=0)
        elif type[0] == '1':
            products = products.filter(productdetail__type=1)

    if min_price:
        products = products.filter(
            Q(sale__gte=int(min_price), sale__gt=0) |
            Q(price__gte=int(min_price), sale=0)
        )

    if max_price:
        products = products.filter(
            Q(sale__lte=int(max_price), sale__gt=0) |
            Q(price__lte=int(max_price), sale=0)
        )
    # if min_price:
    #     products = products.filter(price__gte=int(min_price))

    # if max_price:
    #     products = products.filter(price__lte=int(max_price))

    # if rating:
    #     products = products.filter(rating__gte=rating)
                    
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'top_selling_products':
        products = products.order_by('-total_sold')
    elif sort == 'best_selling_product':
        now = timezone.now()
        products = (products.filter(
            orderitem__order__date__month=now.month,
            orderitem__order__date__year=now.year
        ).annotate(
            total_sold_month=Sum('orderitem__quantity')
        ).order_by('-total_sold_month'))
    elif sort == 'top_sale_products':
        products = products.order_by('-sale')

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

