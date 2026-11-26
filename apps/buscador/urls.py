from django.urls import path

from . import views

app_name = 'buscador'
urlpatterns = [
    path('buscar/', views.buscar, name='buscar'),
    path('buscar/autocompletar/', views.autocompletar, name='autocompletar'),
    path('sugerencias/', views.sugerir, name='sugerir'),
    path('escanear/', views.escanear, name='escanear'),
    path('escanear/foto/', views.analizar_foto_vista, name='analizar_foto'),
    path('escanear/producto/<str:codigo>/', views.producto, name='producto'),
    path('asistente/consultar/', views.asistente_consultar, name='asistente_consultar'),
]
