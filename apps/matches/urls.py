from django.urls import path
from . import views

urlpatterns = [
    path('', views.MatchListView.as_view(), name='match-list'),
    path('center/<int:fixture_id>/', views.FixtureCenterView.as_view(), name='fixture-center'),
    path('<int:pk>/', views.MatchDetailView.as_view(), name='match-detail'),
]
