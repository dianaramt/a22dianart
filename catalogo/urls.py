from django.urls import path

from . import views

app_name = 'catalogo'

urlpatterns = [
    path('buscar/', views.buscar, name='buscar'),
    path('centro/<slug:slug>/libro/<int:pk>/', views.detalle_exemplar, name='detalle'),
]
