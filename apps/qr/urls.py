from django.urls import path

from . import views

app_name = 'qr'
urlpatterns = [path('q/<str:codigo>', views.redirigir, name='redirigir')]
