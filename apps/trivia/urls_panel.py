from django.urls import path

from . import views_panel as v

app_name = 'panel_trivia'
urlpatterns = [
    path('trivia/', v.lista, name='lista'),
    path('trivia/nueva/', v.editar, name='nueva'),
    path('trivia/<int:pk>/', v.editar, name='editar'),
    path('trivia/<int:pk>/activar/', v.activar, name='activar'),
]
