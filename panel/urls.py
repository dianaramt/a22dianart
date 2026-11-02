from django.urls import path

from . import views

app_name = 'panel'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('<slug:slug>/', views.resumo, name='resumo'),
    path('<slug:slug>/catalogo/', views.catalogo, name='catalogo'),
    path('<slug:slug>/catalogo/novo/', views.exemplar_novo, name='exemplar_novo'),
    path('<slug:slug>/catalogo/<int:pk>/', views.exemplar_editar, name='exemplar_editar'),
    path('<slug:slug>/reservas/', views.reservas, name='reservas'),
    path('<slug:slug>/reservas/<int:pk>/<str:accion>/', views.accion_reserva, name='accion_reserva'),
    path('<slug:slug>/escaparate/', views.escaparate, name='escaparate'),
]
