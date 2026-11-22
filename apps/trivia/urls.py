from django.urls import path

from . import views

app_name = 'trivia'
urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('nueva/', views.nueva, name='nueva'),
    path('jugar/', views.jugar, name='jugar'),
    path('resultado/', views.resultado, name='resultado'),
]
