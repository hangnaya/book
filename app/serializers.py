from rest_framework import serializers
from .models import *
from django.db.models import Avg
        
class ProductDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductDetail
        fields = ('detail_id', 'color', 'size', 'quantity')
        
class ProductSaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSale
        fields = ('price', 'start_date', 'end_date')


class ProductSerializer(serializers.ModelSerializer):
    # productdetail_set = ProductDetailSerializer(many=True, read_only=True)
    images = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ('product_id', 'name', 'sale', 'price', 'images', 'total_sold', 'rating') 

    def get_curr_price(self, obj):
        now = timezone.now()
        productsale = obj.productsale_set.filter(start_date__lte=now, end_date__gte=now).first()
        return obj.price if productsale is None else productsale.price
    
    def get_rating(self, obj):
        average_rating = Feedback.objects.filter(product=obj).aggregate(Avg('rating'))['rating__avg']
        return average_rating if average_rating is not None else 0
    
    def get_images(self, obj):
        return [image.name.url for image in obj.productimage_set.all()]

class FeedbackResponseSerializer(serializers.ModelSerializer):
    date = serializers.DateTimeField(format="%H:%M %d/%m/%Y")

    class Meta:
        model = FeedbackRespone
        fields = ('comment', 'date')

class FeedbackSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_image = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    date = serializers.DateTimeField(format="%H:%M %d/%m/%Y", required=False)
    responses = serializers.SerializerMethodField()
    class Meta:
        model = Feedback
        fields = ('feedback_id', 'user_name', 'user_image', 'comment', 'rating', 'date', 'images', 'like', 'dislike', 'responses')

    def get_user_name(self, obj):
        return obj.customer.name
    
    def get_user_image(self, obj):
        if obj.customer.avatar:
            return obj.customer.avatar.url

    def get_images(self, obj):
        return [image.name.url for image in obj.feedbackimage_set.all()]
    
    def get_responses(self, obj):
        responses = FeedbackRespone.objects.filter(feedback=obj)
        return FeedbackResponseSerializer(responses, many=True).data