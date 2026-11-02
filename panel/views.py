from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from catalogo.busca import filtro_busca
from catalogo.models import Exemplar
from centros.models import Centro
from reservas import servizos
from reservas.models import Reserva

from .forms import EscaparateForm, ExemplarForm
from .permisos import admin_do_centro


@login_required
@require_GET
def inicio(request):
    """Se a persoa administra un só centro, vai directa ao seu panel."""
    if not request.user.es_admin_centro:
        raise Http404
    centros = request.user.centros_administrados.exclude(estado=Centro.Estado.DESACTIVADO)
    if len(centros) == 1:
        return redirect('panel:resumo', centros[0].slug)
    return render(request, 'panel/inicio.html', {'centros': centros})


@admin_do_centro
@require_GET
def resumo(request, centro):
    exemplares = centro.exemplares.exclude(estado=Exemplar.Estado.RETIRADO)
    reservas_activas = Reserva.objects.filter(exemplar__centro=centro, estado=Reserva.Estado.ACTIVA)
    contexto = {
        'centro': centro,
        'total_exemplares': exemplares.count(),
        'total_disponibles': exemplares.filter(estado=Exemplar.Estado.DISPONIBLE).count(),
        'total_prestados': exemplares.filter(estado=Exemplar.Estado.PRESTADO).count(),
        'total_reservas': reservas_activas.count(),
        'total_vencidas': reservas_activas.filter(vence_en__lt=timezone.now()).count(),
    }
    return render(request, 'panel/resumo.html', contexto)


# --- Catálogo ---

@admin_do_centro
@require_GET
def catalogo(request, centro):
    exemplares = centro.exemplares.all()
    consulta = request.GET.get('q', '').strip()[:100]
    estado = request.GET.get('estado', '')
    if consulta:
        exemplares = exemplares.filter(filtro_busca(consulta))
    if estado in Exemplar.Estado.values:
        exemplares = exemplares.filter(estado=estado)
    paxina = Paginator(exemplares, 25).get_page(request.GET.get('paxina'))
    return render(request, 'panel/catalogo.html', {
        'centro': centro, 'paxina': paxina, 'consulta': consulta, 'estado': estado,
        'estados': Exemplar.Estado.choices,
    })


@admin_do_centro
@require_http_methods(['GET', 'POST'])
def exemplar_novo(request, centro):
    form = ExemplarForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        exemplar = form.save(commit=False)
        # O centro sempre é o do panel, nunca un que veña do formulario
        exemplar.centro = centro
        exemplar.save()
        messages.success(request, _('Libro engadido ao catálogo.'))
        if 'gardar_e_outro' in request.POST:
            return redirect('panel:exemplar_novo', centro.slug)
        return redirect('panel:catalogo', centro.slug)
    return render(request, 'panel/exemplar_form.html', {'centro': centro, 'form': form})


@admin_do_centro
@require_http_methods(['GET', 'POST'])
def exemplar_editar(request, centro, pk):
    exemplar = get_object_or_404(centro.exemplares, pk=pk)
    estado_orixinal = exemplar.estado
    form = ExemplarForm(request.POST or None, instance=exemplar)
    if request.method == 'POST' and form.is_valid():
        exemplar = form.save(commit=False)
        estado_novo = exemplar.estado
        # Gardamos os datos sen tocar o estado...
        exemplar.estado = estado_orixinal
        exemplar.save(update_fields=['titulo', 'autoria', 'isbn', 'descricion', 'texto_busca'])
        # ...e o estado só se segue igual ca cando se abriu o formulario (un lector podería telo reservado)
        if estado_novo != estado_orixinal:
            cambiados = Exemplar.objects.filter(pk=exemplar.pk, estado=estado_orixinal).update(estado=estado_novo)
            if not cambiados:
                messages.warning(request, _('Gardáronse os datos, pero o estado non: cambiou mentres editabas (quizais alguén o reservou).'))
                return redirect('panel:catalogo', centro.slug)
        messages.success(request, _('Libro actualizado.'))
        return redirect('panel:catalogo', centro.slug)
    return render(request, 'panel/exemplar_form.html', {'centro': centro, 'form': form, 'exemplar': exemplar})


# --- Reservas ---

@admin_do_centro
@require_GET
def reservas(request, centro):
    do_centro = Reserva.objects.filter(exemplar__centro=centro).select_related('exemplar', 'lector')
    contexto = {
        'centro': centro,
        'activas': do_centro.filter(estado=Reserva.Estado.ACTIVA).order_by('vence_en'),
        'agora': timezone.now(),
        'recentes': do_centro.exclude(estado=Reserva.Estado.ACTIVA).order_by('-actualizado_en')[:20],
    }
    if centro.tipo == Centro.Tipo.BIBLIOTECA:
        contexto['prestamos'] = do_centro.filter(estado=Reserva.Estado.RECOLLIDA).order_by('actualizado_en')
    return render(request, 'panel/reservas.html', contexto)


# gettext_lazy: as mensaxes tradúcense en cada petición, non ao cargar o módulo
ACCIONS_RESERVA = {
    'recollida': (servizos.marcar_recollida, gettext_lazy('Reserva marcada como recollida.')),
    'non_recollida': (servizos.marcar_non_recollida, gettext_lazy('Reserva marcada como non recollida. O libro volve estar dispoñible.')),
    'devolta': (servizos.marcar_devolta, gettext_lazy('Devolución rexistrada. O libro volve estar dispoñible.')),
}


@admin_do_centro
@require_POST
def accion_reserva(request, centro, pk, accion):
    if accion not in ACCIONS_RESERVA:
        raise Http404
    funcion, mensaxe = ACCIONS_RESERVA[accion]
    try:
        funcion(centro, pk)
        messages.success(request, mensaxe)
    except servizos.ReservaErro as erro:
        messages.error(request, str(erro))
    return redirect('panel:reservas', centro.slug)


# --- Escaparate ---

@admin_do_centro
@require_http_methods(['GET', 'POST'])
def escaparate(request, centro):
    form = EscaparateForm(request.POST or None, request.FILES or None, instance=centro)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, _('Escaparate actualizado.'))
        return redirect('panel:escaparate', centro.slug)
    return render(request, 'panel/escaparate.html', {'centro': centro, 'form': form})
