from django.urls import path

from . import views_panel as v

app_name = 'panel_contenidos'
urlpatterns = [
    path('contenidos/', v.lista, name='lista'),
    path('contenidos/<str:tipo>/nuevo/', v.editar, name='nuevo'),
    path('contenidos/<str:tipo>/<int:pk>/', v.editar, name='editar'),
    path('contenidos/<str:tipo>/<int:pk>/<str:accion>/', v.accion, name='accion'),
    path('revision/', v.revision, name='revision'),
    path('puntos/', v.puntos, name='puntos'),
    path('puntos/nuevo/', v.punto_editar, name='punto_nuevo'),
    path('puntos/<int:pk>/', v.punto_editar, name='punto_editar'),
]
