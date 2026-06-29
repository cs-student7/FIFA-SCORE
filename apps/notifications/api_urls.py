from django.urls import path
from . import api_views

urlpatterns = [
    path('', api_views.NotificationListAPIView.as_view(), name='api-notification-list'),
    path('<int:pk>/read/', api_views.MarkReadAPIView.as_view(), name='api-notification-read'),
    path('mark-all-read/', api_views.MarkAllReadAPIView.as_view(), name='api-notification-read-all'),
]
