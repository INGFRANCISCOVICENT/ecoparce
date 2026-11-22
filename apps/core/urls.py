from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'core'
urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('privacidad/', views.privacidad, name='privacidad'),
    path('terminos/', views.terminos, name='terminos'),
    path('licencias/', views.licencias, name='licencias'),
    path('version.json', views.version_json, name='version_json'),
    path('panel/versiones/', views.panel_versiones, name='panel_versiones'),
    path('robots.txt', views.robots_txt, name='robots'),
    path('sitemap.xml', views.sitemap_xml, name='sitemap'),
    path('favicon.ico', RedirectView.as_view(url='/static/img/favicon-32.png', permanent=True)),
]
