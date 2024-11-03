from django import forms
from .models import *
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['name', 'dob', 'gender', 'phone', 'email']

    def clean(self):
        cleaned_data = super().clean()
        phone = cleaned_data.get('phone')
        email = cleaned_data.get('email')

        # Kiểm tra phone: Số điện thoại phải là duy nhất ngoại trừ người dùng hiện tại
        if phone and User.objects.filter(phone=phone).exclude(id=self.instance.id).exists():
            self.add_error('phone', 'Số điện thoại đã được đăng ký.')

        # Kiểm tra email: Email phải là duy nhất ngoại trừ người dùng hiện tại
        if email and User.objects.filter(email=email).exclude(id=self.instance.id).exists():
            self.add_error('email', 'Email đã được đăng ký.')

        return cleaned_data

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = '__all__'

        widgets = {
            'code': forms.TextInput(),
            'discount': forms.TextInput(),
            'quantity': forms.TextInput(),
            'condition': forms.TextInput(),
            'start_date': forms.DateInput(),
            'end_date': forms.DateInput(),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code')
        coupon_id = self.instance.coupon_id  # Lấy ID của bản ghi hiện tại (nếu đang chỉnh sửa)
        
        # Kiểm tra nếu code đã tồn tại với các record khác, bỏ qua record hiện tại khi edit
        if Coupon.objects.filter(code=code).exclude(coupon_id=coupon_id).exists():
            raise forms.ValidationError("Tên mã đã tồn tại, vui lòng chọn tên khác.")
        
        return code

class ProductForm(forms.ModelForm):
    category = forms.ModelChoiceField(queryset=Category.objects.all())

    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'category', 'sale', 'page', 'age', 'author', 'publisher', 'translator', 'year_of_publish',
                  'size', 'weight']

        widgets = {
            'name': forms.TextInput(),
            'description': forms.TextInput(),
            'price': forms.TextInput(),
        }


class ProductSaleForm(forms.ModelForm):
    class Meta:
        model = ProductSale
        fields = ['price']

        widgets = {
            'price': forms.TextInput(),
        }


class ProductImageForm(forms.ModelForm):
    name = forms.FileField(widget=forms.ClearableFileInput(
        attrs={'multiple': True}))  # thêm thuộc tính multiple

    class Meta:
        model = ProductImage
        fields = ['name']

    def __init__(self, *args, **kwargs):
        # Tùy chọn này giúp trường 'name' không bắt buộc
        super().__init__(*args, **kwargs)
        self.fields['name'].required = False 


class AddressShippingForm(forms.ModelForm):
    class Meta:
        model = AddressShipping
        fields = ['receiver', 'phone', 'address']

        widgets = {
            'receiver': forms.TextInput(),
            'phone': forms.TextInput(),
            'address': forms.TextInput(),
        }


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        exclude = ['date', 'customer', 'status']


class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = OrderStatus
        fields = ['name', 'description']

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.date = timezone.now()
        if commit:
            instance.save()
        return instance


class ResponseForm(forms.Form):
    textfield = forms.CharField(label="Nhập vào phản hồi cho bình luận", 
                                 widget=forms.Textarea(attrs={'class': 'form-control', 'rows': '5', 'cols': '80'}))
    

    helper = FormHelper()
    helper.form_method = 'POST'
    helper.add_input(Submit('submit', 'Gửi phản hồi'))

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        category_id = self.instance.category_id  # Lấy ID của bản ghi hiện tại (nếu đang chỉnh sửa)
        
        # Kiểm tra nếu name đã tồn tại với các record khác, bỏ qua record hiện tại khi edit
        if Category.objects.filter(name=name).exclude(category_id=category_id).exists():
            raise forms.ValidationError("Tên danh mục đã tồn tại, vui lòng chọn tên khác.")
        
        return name

class CategoryPostForm(forms.ModelForm):
    class Meta:
        model = CategoryPost
        fields = ['name', 'description', 'is_active']

    def clean_is_active(self):
        # Lấy giá trị từ POST, mặc định là False nếu không tồn tại hoặc là '0'
        is_active = self.data.get('is_active', '0')
        if is_active == '0':
            return False
        return True
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        category_id = self.instance.category_id  # Lấy ID của bản ghi hiện tại (nếu đang chỉnh sửa)
        
        # Kiểm tra nếu name đã tồn tại với các record khác, bỏ qua record hiện tại khi edit
        if CategoryPost.objects.filter(name=name).exclude(category_id=category_id).exists():
            raise forms.ValidationError("Tên danh mục đã tồn tại, vui lòng chọn tên khác.")
        
        return name

class PostForm(forms.ModelForm):
    category = forms.ModelChoiceField(queryset=CategoryPost.objects.all())
    class Meta:
        model = Post
        fields = ['title', 'content', 'author_name', 'category', 'is_active']

    def clean_is_active(self):
        # Lấy giá trị từ POST, mặc định là False nếu không tồn tại hoặc là '0'
        is_active = self.data.get('is_active', '0')
        if is_active == '0':
            return False
        return True