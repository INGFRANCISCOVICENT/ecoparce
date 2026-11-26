from django.urls import path

from . import views

app_name = 'api'

urlpatterns = [
    path('estado/', views.estado_api, name='estado'),
    path('openapi.json', views.openapi_spec, name='openapi'),
    path('oauth/token/', views.oauth_token, name='oauth_token'),
    path('oauth/revoke/', views.oauth_revoke, name='oauth_revoke'),
    path('oauth/introspect/', views.oauth_introspect, name='oauth_introspect'),
    path('oauth/userinfo/', views.oauth_userinfo, name='oauth_userinfo'),
    path('guias/', views.listar_guias, name='guias'),
    path('buscar/', views.buscar_residuos, name='buscar'),
    path('puntos/', views.listar_puntos, name='puntos'),
    path('escanear/', views.escanear_codigo, name='escanear_post'),
    path('escanear/<str:codigo>/', views.escanear_codigo, name='escanear_get'),
    path('sugerencias/', views.crear_sugerencia, name='sugerencias'),
    path('cuenta/resumen/', views.resumen_cuenta, name='cuenta_resumen'),
    path('gateway/logs/', views.logs_gateway, name='gateway_logs'),
]
