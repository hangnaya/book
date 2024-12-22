from django.shortcuts import render, get_object_or_404, redirect
from ..models import *
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from ..forms import *
from django.core.paginator import Paginator

@login_required(login_url='/login')
def categoryManager(request):
    keyword = request.GET.get('keyword', '')
    categories = Category.objects.filter(name__icontains=keyword)
    paginator = Paginator(categories, 15)

    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin_shop/category/index.html', {'page_obj': page_obj})

@login_required(login_url='/login')
def addCategory(request):
    messages = '' 
    error = ''
    categories = Category.objects.all()
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
                  {'categories':categories, 'form': form, 'error': error, 'messages' : messages})

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
