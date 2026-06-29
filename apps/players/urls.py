from django.urls import path
from . import views

urlpatterns = [
    path('', views.PlayerListView.as_view(), name='player-list'),
    path('<slug:slug>/', views.PlayerDetailView.as_view(), name='player-detail'),
]
