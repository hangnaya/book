from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('login', views.log_in, name='login'),
    path('logout', views.log_out, name='logout'),
    path('home', views.home, name='home'),

    # address shipping
    path('add-address', views.add_address, name='add-address'),
    path('edit-address', views.edit_address, name='edit-address'),
    path('delete-address', views.delete_address, name='delete-address'),

    # coupon
    path('coupons', views.couponManager, name='coupons'),
    path('add_coupon', views.addCoupon, name='add_coupon'),
    path('edit_coupon', views.editCoupon, name='edit_coupon'),
    path('delete_coupon', views.deleteCoupon, name='delete_coupon'),

    # product
    path('products', views.productManager, name='products'),
    path('add_product', views.addProduct, name='add_product'),
    path('edit_product', views.editProduct, name='edit_product'),
    path('product-detail', views.getProductDetailAdmin, name='product_detail_admin'),
    path('delete_product', views.deleteProduct, name='delete_product'),

    # category
    path('categories', views.categoryManager, name='categories'),
    path('add_category', views.addCategory, name='add_category'),
    path('edit_category', views.editCategory, name='edit_category'),
    path('delete_category', views.deleteCategory, name='delete_category'),

    # category_post
    path('categories_post', views.categoryPostManager, name='categories_post'),
    path('add_category_post', views.addCategoryPost, name='add_category_post'),
    path('edit_category_post', views.editCategoryPost, name='edit_category_post'),
    path('delete_category_post', views.deleteCategoryPost, name='delete_category_post'),

    # category_post
    path('posts', views.postManager, name='posts'),
    path('add_post', views.addPost, name='add_post'),
    path('edit_post', views.editPost, name='edit_post'),
    path('delete_post', views.deletePost, name='delete_post'),
    # dashboard
    path('report', views.report, name='report'),

    path('ckeditor/', include('ckeditor_uploader.urls')),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)