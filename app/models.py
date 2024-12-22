from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from ckeditor.fields import RichTextField

# Create your models here.
class User(AbstractUser):
    name = models.CharField(max_length=100, blank=False, null=False)
    avatar = models.ImageField(default='user/default.jpg', upload_to='user/')
    dob = models.DateField(blank=False, null=True)
    gender = models.CharField(max_length=50, blank=False, null=False)
    phone = models.CharField(max_length=20, blank=False, null=False)
    email = models.EmailField(max_length=50, blank=False, null=False)
    is_staff = models.IntegerField(default=0, blank=False, null=False)


class Category(models.Model):
    category_id = models.AutoField(primary_key=True, blank=False, null=False)
    name = models.CharField(max_length=100, blank=False, null=False, unique=True)
    parent_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    product_id = models.AutoField(primary_key=True, blank=False, null=False)
    name = models.CharField(max_length=100, blank=False, null=False)
    description = models.TextField(max_length=5000, blank=False, null=False)
    price = models.FloatField(blank=False, null=False)
    sale = models.FloatField(default=0.0, blank=False, null=False)
    time_created = models.DateTimeField(default=timezone.datetime.now(), blank=False, null=False)
    page = models.IntegerField(default=0, blank=False, null=False)
    age = models.IntegerField(default=0, blank=False, null=False)
    author = models.CharField(default="", max_length=100, blank=False, null=False)
    publisher = models.CharField(default="", max_length=100, blank=False, null=False)
    translator = models.CharField(default="", max_length=100, blank=False, null=False)
    year_of_publish = models.IntegerField(default=2024, blank=False, null=False)
    size = models.CharField(default="", max_length=20, blank=False, null=False)
    weight = models.FloatField(default=0.0, blank=False, null=False)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, blank=False, null=False)
    total_sold = models.IntegerField(default=0, blank=False, null=False)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    image_id = models.AutoField(primary_key=True, blank=False, null=False)
    name = models.ImageField(upload_to='product/')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=False, null=False)

    def __str__(self):
        return self.product.name


class ProductDetail(models.Model):
    detail_id = models.AutoField(primary_key=True, blank=False, null=False)
    type = models.IntegerField(default=0, blank=False, null=False)
    quantity = models.IntegerField(default=0, blank=False, null=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=False, null=False)

    def __str__(self):
        return f"{self.type} - {self.quantity}"


class ProductSale(models.Model):
    sale_id = models.AutoField(primary_key=True, blank=False, null=False)
    price = models.FloatField(default=0, blank=False, null=False)
    start_date = models.DateTimeField(default=timezone.datetime.now(), blank=False, null=False)
    end_date = models.DateTimeField(default=timezone.datetime.now(), blank=False, null=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=False, null=False)

    def __str__(self):
        return f'{self.product} - {self.price}'


class Feedback(models.Model):
    feedback_id = models.AutoField(primary_key=True, blank=False, null=False)
    comment     = models.CharField(max_length=255, blank=True, null=False)
    rating      = models.IntegerField(blank=False, null=False)
    date        = models.DateTimeField(default=timezone.datetime.now(), blank=False, null=False)
    like        = models.IntegerField(default=0, blank=False, null=False)
    dislike     = models.IntegerField(default=0, blank=False, null=False)
    customer    = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)
    product     = models.ForeignKey(Product, on_delete=models.CASCADE, blank=False, null=False)
    is_read     = models.IntegerField(default=0, blank=False, null=False)
    
    def __str__(self):
        return f"{self.product} - {self.customer}"


class FeedbackImage(models.Model):
    feedback_image_id = models.AutoField(primary_key=True, blank=False, null=False)
    name = models.ImageField(upload_to='feedback/')
    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE, null=False)

    def __str__(self):
        return self.name


class FeedbackRespone(models.Model):
    feedback_respone_id = models.AutoField(primary_key=True, blank=False, null=False)
    comment = models.CharField(max_length=255, blank=False, null=False)
    date = models.DateTimeField(default=timezone.datetime.now(), blank=False, null=False)
    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE, null=False)

    def __str__(self):
        return f"{self.feedback} - {self.feedback_respone_id}"


class AddressShipping(models.Model):
    address_shipping_id = models.AutoField(primary_key=True, blank=False, null=False)
    receiver = models.CharField(max_length=100, blank=False, null=False)
    phone = models.CharField(max_length=20, blank=False, null=False)
    address = models.CharField(max_length=255, blank=False, null=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)

    def __str__(self):
        return self.receiver


class OrderStatus(models.Model):
    order_status_id = models.AutoField(primary_key=True, blank=False, null=False)
    name = models.CharField(max_length=100, blank=False, null=False)
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name

class Order(models.Model):
    order_id = models.AutoField(primary_key=True, blank=False, null=False)
    date = models.DateTimeField(default=timezone.now, blank=False, null=False)
    discount = models.FloatField(default=0, blank=False, null=False)
    shipping = models.FloatField(default=0, blank=False, null=False)
    total = models.FloatField(blank=False, null=False)
    status = models.ForeignKey(OrderStatus, default=7, on_delete=models.CASCADE, blank=False, null=False)
    note = models.CharField(max_length=100, blank=True, null=False)
    payment_method = models.CharField(max_length=100, blank=False, null=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)
    receiver = models.CharField(max_length=100, blank=False, null=False)
    phone = models.CharField(max_length=20, blank=False, null=False)
    address = models.CharField(max_length=255, blank=False, null=False)
    order_code = models.CharField(max_length=8, default='')


class OrderItem(models.Model):
    order_item_id = models.AutoField(primary_key=True, blank=False, null=False)
    type = models.IntegerField(default=0, blank=False, null=False)
    quantity = models.IntegerField(default=1, blank=False, null=False)
    price = models.FloatField(blank=False, null=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, blank=False, null=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=False, null=False)
    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE, blank=True, null=True)


class Tracking(models.Model):
    track_id = models.AutoField(primary_key=True, blank=False, null=False)
    date = models.DateTimeField(default=timezone.datetime.now(), blank=False, null=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, blank=False, null=False)
    order_status = models.ForeignKey(OrderStatus, on_delete=models.CASCADE, blank=False, null=False)


# class Cart(models.Model):
#     cart_id = models.AutoField(primary_key=True, blank=False, null=False)
#     customer = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)


# class CartItem(models.Model):
#     cart_item_id = models.AutoField(primary_key=True, blank=False, null=False)
#     type = models.IntegerField(default=0, blank=False, null=False)
#     quantity = models.IntegerField(default=1, blank=False, null=False)
#     cart = models.ForeignKey(Cart, on_delete=models.CASCADE, blank=False, null=False)
#     product = models.ForeignKey(Product, on_delete=models.CASCADE, blank=False, null=False)


class Coupon(models.Model):
    coupon_id = models.AutoField(primary_key=True, blank=False, null=False)
    code = models.CharField(max_length=100, blank=False, null=False)
    discount = models.FloatField(default=0, blank=False, null=False)
    quantity = models.IntegerField(default=0, blank=False, null=False)
    condition = models.FloatField(default=1, blank=False, null=False)
    start_date = models.DateTimeField(default=timezone.datetime.now(), blank=False, null=False)
    end_date = models.DateTimeField(default=timezone.datetime.now(), blank=False, null=False)


class Notification(models.Model):
    notification_id = models.AutoField(primary_key=True, blank=False, null=False)
    content = models.CharField(max_length=255, blank=False, null=False)
    create_at = models.DateTimeField(default=timezone.datetime.now(), blank=False, null=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=True)
    is_read = models.IntegerField(default=0, blank=False, null=False)

class VoucherWallet(models.Model):
    voucher_wallet_id = models.AutoField(primary_key=True, blank=False, null=False)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, blank=False, null=True)

class CategoryPost(models.Model):
    category_id = models.AutoField(primary_key=True, blank=False, null=False)
    name = models.CharField(max_length=100, blank=False, null=False, unique=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Post(models.Model):
    post_id = models.AutoField(primary_key=True, blank=False, null=False)
    title = models.CharField(max_length=255, blank=False, null=False, unique=True)
    content = RichTextField()
    category = models.ForeignKey(CategoryPost, on_delete=models.CASCADE, blank=False, null=False)
    author_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    views = models.IntegerField(default=0)
    time_created = models.DateTimeField(default=timezone.datetime.now(), blank=False, null=False)
    image = models.ImageField(upload_to='post_images/', blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False, default=1)

    def __str__(self):
        return self.name