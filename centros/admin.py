from django.contrib import admin

from .models import Centro


@admin.register(Centro)
class CentroAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'estado', 'creado_en']
    list_filter = ['tipo', 'estado']
    search_fields = ['nome', 'localizacion']
    prepopulated_fields = {'slug': ['nome']}
    filter_horizontal = ['administradores']
