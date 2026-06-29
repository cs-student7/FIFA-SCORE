from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

admin.site.site_header = 'GoalPulse Admin'
admin.site.site_title = 'GoalPulse'
admin.site.index_title = 'Football Data Management'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('', include('apps.core.urls')),
    path('matches/', include('apps.matches.urls')),
    path('leagues/', include('apps.leagues.urls')),
    path('teams/', include('apps.teams.urls')),
    path('players/', include('apps.players.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('api/v1/', include('apps.core.api_urls')),
    path('api/v1/matches/', include('apps.matches.api_urls')),
    path('api/v1/leagues/', include('apps.leagues.api_urls')),
    path('api/v1/teams/', include('apps.teams.api_urls')),
    path('api/v1/players/', include('apps.players.api_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns


from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns += [
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]