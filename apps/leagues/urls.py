from django.urls import path
from . import views

urlpatterns = [
    path('', views.LeagueListView.as_view(), name='league-list'),
    path('<slug:slug>/', views.LeagueDetailView.as_view(), name='league-detail'),
]
