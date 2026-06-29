from django.conf import settings


def site_context(request):
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'GoalPulse'),
        'SITE_URL': getattr(settings, 'SITE_URL', ''),
        'LIVE_UPDATE_INTERVAL': getattr(settings, 'LIVE_UPDATE_INTERVAL', 15),
    }
