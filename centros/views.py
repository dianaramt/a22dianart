from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from catalogo.busca import filtro_busca
from catalogo.models import Exemplar

from .models import Centro


@require_GET
def portada(request):
    # Só os centros activados polo superusuario son públicos
    centros = Centro.objects.filter(estado=Centro.Estado.ACTIVO)
    return render(request, 'centros/portada.html', {'centros': centros})


@require_GET
def escaparate(request, slug):
    centro = get_object_or_404(Centro, slug=slug, estado=Centro.Estado.ACTIVO)
    exemplares = centro.exemplares.exclude(estado=Exemplar.Estado.RETIRADO)
    consulta = request.GET.get('q', '').strip()[:100]
    if consulta:
        exemplares = exemplares.filter(filtro_busca(consulta))
    paxina = Paginator(exemplares, 24).get_page(request.GET.get('paxina'))
    return render(request, 'centros/escaparate.html', {'centro': centro, 'paxina': paxina, 'consulta': consulta})
