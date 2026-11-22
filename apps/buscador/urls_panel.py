from django.urls import path

from . import views_panel as v

app_name = 'panel_buscador'
urlpatterns = [
    path('sugerencias/', v.sugerencias, name='sugerencias'),
    path('sugerencias/<int:pk>/atender/', v.atender, name='atender'),
]
