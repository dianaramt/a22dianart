from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from centros.models import Centro
from centros.visitas import resumo_visitas
from reservas.models import Reserva
from usuarios.models import Usuario

from .forms_plataforma import AdministradorForm, CentroAltaForm
from .permisos import superusuario_plataforma


@superusuario_plataforma
@require_GET
def inicio(request):
    estado = request.GET.get('estado', Centro.Estado.PENDENTE)
    if estado not in Centro.Estado.values:
        estado = Centro.Estado.PENDENTE
    centros = (
        Centro.objects.filter(estado=estado)
        .annotate(num_admins=Count('administradores', distinct=True), num_exemplares=Count('exemplares', distinct=True))
        .order_by('-creado_en')
    )
    totais = Centro.objects.aggregate(**{e: Count('pk', filter=Q(estado=e)) for e in Centro.Estado.values})
    return render(request, 'panel/plataforma/inicio.html', {
        'centros': centros,
        'estado': estado,
        'pestanas': [(valor, nome, totais[valor]) for valor, nome in Centro.Estado.choices],
        'total_lectores': Usuario.objects.filter(rol=Usuario.Rol.LECTOR).count(),
    })


@superusuario_plataforma
@require_http_methods(['GET', 'POST'])
def centro_novo(request):
    form = CentroAltaForm(request.POST or None, prefix='centro')
    form_admin = AdministradorForm(request.POST or None, prefix='admin')
    if request.method == 'POST' and form.is_valid() and form_admin.is_valid():
        # Centro e administrador créanse xuntos ou non se crea ningún
        with transaction.atomic():
            centro = form.save()  # nace en estado pendente
            form_admin.gardar(centro)
        messages.success(request, _('Centro creado. Revisa os datos e actívao cando estea listo.'))
        return redirect('plataforma:centro', centro.pk)
    return render(request, 'panel/plataforma/centro_novo.html', {'form': form, 'form_admin': form_admin})


@superusuario_plataforma
@require_http_methods(['GET', 'POST'])
def centro_detalle(request, pk):
    centro = get_object_or_404(Centro, pk=pk)
    form_admin = AdministradorForm(request.POST or None, centro=centro, prefix='admin')
    if request.method == 'POST' and form_admin.is_valid():
        usuario = form_admin.gardar(centro)
        messages.success(request, _('%(usuario)s xa pode xestionar o centro.') % {'usuario': usuario})
        return redirect('plataforma:centro', centro.pk)
    return render(request, 'panel/plataforma/centro_detalle.html', {
        'centro': centro,
        'administradores': centro.administradores.order_by('email'),
        'form_admin': form_admin,
        'reservas_activas': Reserva.objects.filter(exemplar__centro=centro, estado=Reserva.Estado.ACTIVA).count(),
        'num_exemplares': centro.exemplares.count(),
        'visitas': resumo_visitas(centro),
    })


@superusuario_plataforma
@require_POST
def centro_estado(request, pk, estado):
    centro = get_object_or_404(Centro, pk=pk)
    if estado not in Centro.Estado.values:
        raise Http404
    if estado == Centro.Estado.ACTIVO and not centro.administradores.exists():
        messages.error(request, _('Asigna polo menos un administrador antes de activar o centro.'))
    else:
        centro.estado = estado
        centro.save(update_fields=['estado'])
        messages.success(request, _('Estado do centro: %(estado)s.') % {'estado': centro.get_estado_display()})
    return redirect('plataforma:centro', centro.pk)


@superusuario_plataforma
@require_POST
def quitar_admin(request, pk, usuario_pk):
    centro = get_object_or_404(Centro, pk=pk)
    usuario = get_object_or_404(centro.administradores, pk=usuario_pk)
    if centro.esta_activo and centro.administradores.count() == 1:
        messages.error(request, _('Un centro activo debe ter polo menos un administrador.'))
    else:
        # Quítase a relación; a conta segue existindo por se administra outros centros
        centro.administradores.remove(usuario)
        messages.success(request, _('%(usuario)s xa non administra este centro.') % {'usuario': usuario})
    return redirect('plataforma:centro', centro.pk)
