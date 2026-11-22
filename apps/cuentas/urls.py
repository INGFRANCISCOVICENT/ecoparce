from django.urls import path

from . import views

app_name = 'cuentas'
urlpatterns = [
    # Visitante con cuenta de Google
    path('cuenta/', views.mi_cuenta, name='mi_cuenta'),
    path('cuenta/autorizacion/', views.autorizacion, name='autorizacion'),
    path('cuenta/comunicaciones/', views.comunicaciones, name='comunicaciones'),
    path('cuenta/mis-datos.json', views.exportar_datos, name='exportar'),
    path('cuenta/eliminar/', views.eliminar_cuenta, name='eliminar'),
    # Panel
    path('panel/ingresar/', views.ingresar, name='ingresar'),
    path('panel/usuarios/', views.usuarios, name='usuarios'),
    path('panel/usuarios/nuevo/', views.usuario_crear, name='usuario_crear'),
    path('panel/usuarios/<int:pk>/', views.usuario_editar, name='usuario_editar'),
    path('panel/auditoria/', views.auditoria, name='auditoria'),
]
