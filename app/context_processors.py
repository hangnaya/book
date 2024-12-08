from .models import *

def site_settings(request):
    categories = Category.objects.all()
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(customer=request.user).order_by('is_read', '-create_at')[:3]
        totalNotiUnread = Notification.objects.filter(customer=request.user, is_read = 0).count()
        notificationsAdmin = Feedback.objects.filter(is_read = 0).order_by('is_read', '-date')
        totalNotiUnreadAdmin = Feedback.objects.filter(is_read = 0).count()
    else:
        notifications = []
        totalNotiUnread = 0
        notificationsAdmin = []
        totalNotiUnreadAdmin = 0
    return {
        'categories': categories,
        'notificationsNewest': notifications,
        'totalNotiUnread': totalNotiUnread,
        'notificationsAdmin': notificationsAdmin,
        'totalNotiUnreadAdmin': totalNotiUnreadAdmin,
    }