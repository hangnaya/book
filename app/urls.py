from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('login', views.log_in, name='login'),
    path('login-admin', views.log_in_admin, name='login-admin'),
    path('logout', views.log_out, name='logout'),
    path('logout-admin', views.log_out_admin, name='logout-admin'),
    path('', views.home, name='home'),
    path('list-product', views.listProduct, name='list-product'),
    path('product/<int:product_id>', views.getProductDetail, name='product-detail'),
    path('cart', views.add_to_cart, name='cart'),
    path('edit-cart-item', views.edit_cart_item, name='edit-cart-item'),
    path('delete-cart-item', views.delete_cart_item, name='delete-cart-item'),
    path('check-coupon', views.check_coupon, name='check-coupon'),
    path('checkout', views.checkout, name='check-out'),
    path('buynow', views.buy_now, name='buy-now'),
    path('get-order', views.get_order, name='get_order'),
    path('order-detail', views.get_order_detail, name='order-detail'),
    path('cancel-order', views.cancel_order, name='cancel-order'),
    # API
    path('filter-product', views.getListProduct, name='list-product'),
    path('register', views.register, name='register'),
    path('order', views.order, name='order'),

    # feedback
    path('feedback', views.handleFeedback, name='feedback'),
    path('list-feedback', views.getFeedback, name='list-feedback'),
    path('get-feedback', views.getFeedbackByProduct, name='get-feedback'),
    path('react-feedback', views.ReactFeedbackByProduct, name='react-feedback'),
    path('read-feedback', views.ReadFeedback, name='read-feedback'),

    path('list-coupon', views.getCoupon, name='list-coupon'),
    path('list-post', views.getPost, name='list-post'),
    path('post/<int:post_id>', views.postDetail, name='post-detail'),
    path('profile', views.profile, name='profile'),
    path('notification', views.notification, name='notification'),

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

    # post
    path('posts', views.postManager, name='posts'),
    path('add_post', views.addPost, name='add_post'),
    path('edit_post', views.editPost, name='edit_post'),
    path('delete_post', views.deletePost, name='delete_post'),

    # order
    path('admin_orders', views.orderManager, name='admin_orders'),
    path('order_detail', views.getOrderDetail, name='order_detail'),

    # customer
    path('customers', views.customerManager, name='customers'),
    path('view_profile', views.viewProfile, name='view_profile'),
    path('update_status', views.updateStatus, name='update_status'),

    # dashboard
    path('dashboard', views.report, name='dashboard'),
    path('export-orders/', views.export_orders, name='export_orders'),

    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('oauth/', include('social_django.urls', namespace='social')),

    path('create-payment/', views.create_payment, name='create_payment'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-cancel/', views.payment_cancel, name='payment_cancel'),

    path('vnpay_return/', views.payment_return, name='vnpay_return'),
    path('payment-vnpay', views.payment_vnpay, name='payment-vnpay'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)