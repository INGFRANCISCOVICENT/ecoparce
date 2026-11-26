from django.urls import path

from . import views_panel

app_name = 'panel_api'

urlpatterns = [
    path('calidad/', views_panel.tablero_calidad, name='calidad'),
    path('calidad/llaves/crear/', views_panel.crear_llave_panel, name='crear_llave'),
    path('calidad/llaves/<int:pk>/alternar/', views_panel.alternar_llave_panel, name='alternar_llave'),
]
