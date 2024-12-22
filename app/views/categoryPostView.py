from django.shortcuts import render, get_object_or_404, redirect
from ..models import *
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from ..forms import *
from django.core.paginator import Paginator

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
