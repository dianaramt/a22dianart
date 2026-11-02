from django.urls import path

from . import views

app_name = 'centros'

urlpatterns = [
    path('', views.portada, name='portada'),
    path('centro/<slug:slug>/', views.escaparate, name='escaparate'),
]
