from django.urls import path

from . import views

app_name = 'reservas'

urlpatterns = [
    path('', views.area_persoal, name='area_persoal'),
    path('reservar/<int:pk>/', views.reservar, name='reservar'),
    path('<int:pk>/', views.detalle, name='detalle'),
    path('<int:pk>/cancelar/', views.cancelar, name='cancelar'),
]
