from django.urls import path

from . import views

app_name = 'estadisticas'
urlpatterns = [
    path('', views.resumen, name='resumen'),
    path('estadisticas/', views.detalle, name='detalle'),
    path('estadisticas/exportar.csv', views.exportar, name='exportar'),
]
