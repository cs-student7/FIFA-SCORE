from django.urls import path
from . import views

urlpatterns = [
    path('', views.TeamListView.as_view(), name='team-list'),
    path('<slug:slug>/', views.TeamDetailView.as_view(), name='team-detail'),
]
