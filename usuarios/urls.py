from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    path('entrar/', views.EntrarView.as_view(), name='entrar'),
    # LogoutView só acepta POST (o formulario está no menú)
    path('sair/', LogoutView.as_view(), name='sair'),
    path('rexistro/', views.rexistro, name='rexistro'),
    path('inicio/', views.inicio, name='inicio'),
]
