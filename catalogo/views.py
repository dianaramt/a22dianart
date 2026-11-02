from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from centros.models import Centro
from reservas.models import Reserva

from .busca import filtro_busca
from .models import Exemplar


def exemplares_publicos():
    """Exemplares visibles: non retirados e de centros activos."""
    return (
        Exemplar.objects.select_related('centro')
        .exclude(estado=Exemplar.Estado.RETIRADO)
        .filter(centro__estado=Centro.Estado.ACTIVO)
    )


@require_GET
def buscar(request):
    consulta = request.GET.get('q', '').strip()[:100]
    paxina = None
    if consulta:
        resultados = exemplares_publicos().filter(filtro_busca(consulta)).order_by('titulo', 'centro__nome')
        paxina = Paginator(resultados, 24).get_page(request.GET.get('paxina'))
    return render(request, 'catalogo/buscar.html', {'consulta': consulta, 'paxina': paxina})


@require_GET
def detalle_exemplar(request, slug, pk):
    # O exemplar debe pertencer ao centro da URL
    exemplar = get_object_or_404(exemplares_publicos(), pk=pk, centro__slug=slug)
    # Se o lector xa o ten reservado, amosámoslle a súa reserva en vez do botón
    reserva_propia = None
    if request.user.is_authenticated:
        reserva_propia = exemplar.reservas.filter(lector=request.user, estado=Reserva.Estado.ACTIVA).first()
    return render(request, 'catalogo/detalle.html', {
        'exemplar': exemplar, 'centro': exemplar.centro, 'reserva_propia': reserva_propia,
    })
