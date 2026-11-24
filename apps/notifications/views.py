from django.views.generic import TemplateView


class NotificationListView(TemplateView):
    template_name = 'notifications/list.html'
