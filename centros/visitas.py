"""Contador de visitas agregadas por centro e día."""

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import F, Sum
from django.utils import timezone

from .models import Visita


def debe_contar(request, centro):
    """Só conta a entrada ao escaparate: nin paxinación, nin buscas, nin o propio persoal do centro."""
    if request.GET.get('paxina') or request.GET.get('q'):
        return False
    usuario = request.user
    if usuario.is_authenticated and (
        usuario.is_superuser or centro.administradores.filter(pk=usuario.pk).exists()
    ):
        return False
    return True


def rexistrar_visita(centro):
    hoxe = timezone.localdate()
    # Incremento na propia BD (F) para non perder visitas simultáneas
    if Visita.objects.filter(centro=centro, dia=hoxe).update(total=F('total') + 1):
        return
    try:
        with transaction.atomic():
            Visita.objects.create(centro=centro, dia=hoxe, total=1)
    except IntegrityError:
        # Outra petición creou a fila do día xusto antes
        Visita.objects.filter(centro=centro, dia=hoxe).update(total=F('total') + 1)


def resumo_visitas(centro, dias_grafica=14):
    """Totais de hoxe, 7 e 30 días e a serie diaria dos últimos `dias_grafica` días (con ceros)."""
    hoxe = timezone.localdate()
    visitas = centro.visitas.all()

    def desde(dias):
        return visitas.filter(dia__gt=hoxe - timedelta(days=dias)).aggregate(s=Sum('total'))['s'] or 0

    por_dia = dict(visitas.filter(dia__gt=hoxe - timedelta(days=dias_grafica)).values_list('dia', 'total'))
    serie = [(dia, por_dia.get(dia, 0)) for dia in (hoxe - timedelta(days=n) for n in range(dias_grafica - 1, -1, -1))]
    maximo = max((total for _, total in serie), default=0)
    return {
        'hoxe': por_dia.get(hoxe, 0),
        'semana': desde(7),
        'mes': desde(30),
        'total': visitas.aggregate(s=Sum('total'))['s'] or 0,
        # Porcentaxe de cada día respecto ao máximo, para debuxar barras con CSS
        'serie': [(dia, total, round(total * 100 / maximo) if maximo else 0) for dia, total in serie],
    }
