from django.urls import path
from . import api_views

urlpatterns = [
    path('search/', api_views.GlobalSearchAPIView.as_view(), name='api-search'),
]
