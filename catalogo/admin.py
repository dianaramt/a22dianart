from django.contrib import admin

from .models import Exemplar


@admin.register(Exemplar)
class ExemplarAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'autoria', 'isbn', 'centro', 'estado']
    list_filter = ['estado', 'centro']
    search_fields = ['titulo', 'autoria', 'isbn']
