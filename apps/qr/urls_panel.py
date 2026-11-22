from django.urls import path

from . import views_panel as v

app_name = 'panel_qr'
urlpatterns = [
    path('qr/', v.lista, name='lista'),
    path('qr/<int:pk>/imagen.<str:formato>', v.imagen, name='imagen'),
    path('qr/<int:pk>/activar/', v.activar, name='activar'),
    path('qr/instituciones/', v.instituciones, name='instituciones'),
]
