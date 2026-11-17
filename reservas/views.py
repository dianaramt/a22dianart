from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from catalogo.views import exemplares_publicos

from .models import Reserva
from .servizos import ReservaErro, cancelar_reserva, crear_reserva


@login_required
@require_http_methods(['GET', 'POST'])
def reservar(request, pk):
    exemplar = get_object_or_404(exemplares_publicos(), pk=pk)

    if request.method == 'POST':
        try:
            reserva = crear_reserva(request.user, exemplar.pk)
        except ReservaErro as erro:
            messages.error(request, str(erro))
            return redirect('catalogo:detalle', exemplar.centro.slug, exemplar.pk)
        messages.success(request, _('Reserva feita.'))
        # Redirixir tras o POST evita reservar de novo ao recargar a páxina
        return redirect('reservas:detalle', reserva.pk)

    # GET: páxina de confirmación co resumo antes de reservar
    return render(request, 'reservas/confirmar.html', {
        'exemplar': exemplar, 'centro': exemplar.centro, 'minutos_cancelacion': settings.BAMBI_MINUTOS_CANCELACION,
    })


@login_required
@require_GET
def detalle(request, pk):
    # Filtrar por lector: ninguén pode ver reservas alleas cambiando o número da URL
    reserva = get_object_or_404(Reserva.objects.select_related('exemplar__centro'), pk=pk, lector=request.user)
    return render(request, 'reservas/detalle.html', {'reserva': reserva, 'centro': reserva.centro})


@login_required
@require_POST
def cancelar(request, pk):
    try:
        cancelar_reserva(request.user, pk)
        messages.success(request, _('Reserva cancelada.'))
    except ReservaErro as erro:
        messages.error(request, str(erro))
    return redirect('reservas:area_persoal')


@login_required
@require_GET
def area_persoal(request):
    # Cada lector só ve as súas propias reservas
    reservas = Reserva.objects.filter(lector=request.user).select_related('exemplar__centro')
    activas = [r for r in reservas if r.estado == Reserva.Estado.ACTIVA]
    historial = [r for r in reservas if r.estado != Reserva.Estado.ACTIVA]
    return render(request, 'reservas/area_persoal.html', {
        'activas': activas,
        'historial': historial,
        'eventos': request.user.eventos_fiabilidade.select_related('reserva__exemplar')[:10],
        'puntos_bloqueo': settings.BAMBI_PUNTOS_BLOQUEO,
        'dias_bloqueo': settings.BAMBI_DIAS_BLOQUEO,
    })
