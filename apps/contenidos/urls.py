from django.urls import path

from . import views

app_name = 'contenidos'
urlpatterns = [
    path('guias/', views.guias, name='guias'),
    path('guias/<slug:slug>/', views.guia, name='guia'),
    path('manejo/', views.manejo, name='manejo'),
    path('puntos/', views.puntos, name='puntos'),
    path('puntos/datos.json', views.puntos_datos, name='puntos_datos'),
]
