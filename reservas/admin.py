from django.contrib import admin

from .models import EventoFiabilidade, Reserva


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ['exemplar', 'lector', 'estado', 'creado_en', 'vence_en']
    list_filter = ['estado', 'exemplar__centro']
    search_fields = ['exemplar__titulo', 'lector__email']
    raw_id_fields = ['exemplar', 'lector']


@admin.register(EventoFiabilidade)
class EventoFiabilidadeAdmin(admin.ModelAdmin):
    list_display = ['lector', 'cambio', 'motivo', 'creado_en', 'actor']
    list_filter = ['motivo']
    search_fields = ['lector__email']
    raw_id_fields = ['lector', 'reserva', 'actor']
