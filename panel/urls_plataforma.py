from django.urls import path

from . import views_plataforma as views

app_name = 'plataforma'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('centros/novo/', views.centro_novo, name='centro_novo'),
    path('centros/<int:pk>/', views.centro_detalle, name='centro'),
    path('centros/<int:pk>/estado/<str:estado>/', views.centro_estado, name='centro_estado'),
    path('centros/<int:pk>/admins/<int:usuario_pk>/quitar/', views.quitar_admin, name='quitar_admin'),
]
