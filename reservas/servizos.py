"""Regras de negocio das reservas. As vistas chaman a estas funcións; non modifican estados directamente."""

from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext as _

from catalogo.models import Exemplar
from centros.models import Centro
from usuarios.models import Usuario

from . import fiabilidade
from .models import EventoFiabilidade, Reserva


class ReservaErro(Exception):
    """Erro cunha mensaxe pensada para amosarlla á persoa usuaria."""


def crear_reserva(lector, exemplar_id):
    if not lector.is_active or not lector.es_lector:
        raise ReservaErro(_('Só as contas de lector poden reservar libros.'))

    with transaction.atomic():
        # Consultar a BD e non o obxecto da sesión: o bloqueo pode ser de hai uns segundos
        bloqueado_ata = Usuario.objects.filter(pk=lector.pk, bloqueado_ata__gt=timezone.now()).values_list(
            'bloqueado_ata', flat=True
        ).first()
        if bloqueado_ata:
            raise ReservaErro(
                _('A túa conta está bloqueada para reservar ata o %(data)s por non recoller reservas.')
                % {'data': date_format(timezone.localtime(bloqueado_ata), 'SHORT_DATETIME_FORMAT')}
            )

        # Actualización condicional: só cambia a reservado se segue dispoñible.
        # Se dúas persoas reservan á vez, só unha obtén 1 fila actualizada.
        actualizados = Exemplar.objects.filter(
            pk=exemplar_id,
            estado=Exemplar.Estado.DISPONIBLE,
            centro__estado=Centro.Estado.ACTIVO,
        ).update(estado=Exemplar.Estado.RESERVADO)
        if actualizados == 0:
            raise ReservaErro(_('Este libro xa non está dispoñible.'))

        exemplar = Exemplar.objects.select_related('centro').get(pk=exemplar_id)
        try:
            return Reserva.objects.create(
                lector=lector,
                exemplar=exemplar,
                vence_en=timezone.now() + timedelta(days=exemplar.centro.dias_reserva),
            )
        except IntegrityError:
            # Segunda barreira: a restrición da BD impide dúas reservas activas
            raise ReservaErro(_('Este libro xa non está dispoñible.')) from None


def cancelar_reserva(lector, reserva_id):
    with transaction.atomic():
        try:
            reserva = Reserva.objects.select_related('exemplar').get(
                pk=reserva_id, lector=lector, estado=Reserva.Estado.ACTIVA
            )
        except Reserva.DoesNotExist:
            raise ReservaErro(_('Non se atopou ningunha reserva activa para cancelar.')) from None

        if not reserva.pode_cancelarse:
            raise ReservaErro(
                _('Xa pasou o prazo de %(minutos)s minutos para cancelar. Se non vas recollela, avisa ao centro.')
                % {'minutos': settings.BAMBI_MINUTOS_CANCELACION}
            )

        reserva.estado = Reserva.Estado.CANCELADA
        reserva.save(update_fields=['estado', 'actualizado_en'])
        # Liberar o exemplar só se seguía reservado (o centro podería telo retirado)
        Exemplar.objects.filter(pk=reserva.exemplar_id, estado=Exemplar.Estado.RESERVADO).update(
            estado=Exemplar.Estado.DISPONIBLE
        )
        return reserva


# --- Accións do administrador do centro ---

def _reserva_do_centro(centro, reserva_id, estado):
    """Reserva no estado indicado e que pertence ao centro; se non, erro."""
    try:
        return Reserva.objects.select_related('exemplar__centro').get(
            pk=reserva_id, exemplar__centro=centro, estado=estado
        )
    except Reserva.DoesNotExist:
        raise ReservaErro(_('A reserva non existe ou xa foi atendida.')) from None


def _pechar(reserva, estado_reserva, estado_exemplar):
    # Actualización condicional: se a reserva cambiou entrementres (p. ex. caducou), non se toca
    cambiadas = Reserva.objects.filter(pk=reserva.pk, estado=reserva.estado).update(
        estado=estado_reserva, actualizado_en=timezone.now()
    )
    if not cambiadas:
        raise ReservaErro(_('A reserva non existe ou xa foi atendida.'))
    reserva.estado = estado_reserva
    Exemplar.objects.filter(pk=reserva.exemplar_id).update(estado=estado_exemplar)
    return reserva


def marcar_recollida(centro, reserva_id, actor=None):
    with transaction.atomic():
        reserva = _reserva_do_centro(centro, reserva_id, Reserva.Estado.ACTIVA)
        # Biblioteca: o libro queda prestado ata a devolución. Libraría: vendeuse, sae do catálogo
        if centro.tipo == Centro.Tipo.BIBLIOTECA:
            estado_exemplar = Exemplar.Estado.PRESTADO
        else:
            estado_exemplar = Exemplar.Estado.RETIRADO
        _pechar(reserva, Reserva.Estado.RECOLLIDA, estado_exemplar)
        fiabilidade.recompensar(reserva, actor)
        return reserva


def marcar_non_recollida(centro, reserva_id, actor=None):
    with transaction.atomic():
        reserva = _reserva_do_centro(centro, reserva_id, Reserva.Estado.ACTIVA)
        _pechar(reserva, Reserva.Estado.NON_RECOLLIDA, Exemplar.Estado.DISPONIBLE)
        fiabilidade.penalizar(reserva, EventoFiabilidade.Motivo.NON_RECOLLIDA, actor)
        return reserva


def marcar_devolta(centro, reserva_id, actor=None):
    if centro.tipo != Centro.Tipo.BIBLIOTECA:
        raise ReservaErro(_('Só as bibliotecas rexistran devolucións.'))
    with transaction.atomic():
        reserva = _reserva_do_centro(centro, reserva_id, Reserva.Estado.RECOLLIDA)
        return _pechar(reserva, Reserva.Estado.DEVOLTA, Exemplar.Estado.DISPONIBLE)


# --- Tarefa programada ---

def caducar_reservas():
    """Pecha as reservas activas con prazo vencido, libera o exemplar e penaliza ao lector.

    Devolve cantas reservas caducaron. Execútase co comando `manage.py caducar_reservas`.
    """
    agora = timezone.now()
    vencidas = list(
        Reserva.objects.filter(estado=Reserva.Estado.ACTIVA, vence_en__lt=agora).values_list('pk', flat=True)
    )
    total = 0
    for pk in vencidas:
        # Unha transacción por reserva: un erro nunha non desfai as demais
        with transaction.atomic():
            # Se o centro a marcou xusto agora, xa non está activa e sáltase
            if not Reserva.objects.filter(pk=pk, estado=Reserva.Estado.ACTIVA).update(
                estado=Reserva.Estado.CADUCADA, actualizado_en=agora
            ):
                continue
            reserva = Reserva.objects.get(pk=pk)
            # Liberar só se seguía reservado (o centro podería telo retirado)
            Exemplar.objects.filter(pk=reserva.exemplar_id, estado=Exemplar.Estado.RESERVADO).update(
                estado=Exemplar.Estado.DISPONIBLE
            )
            fiabilidade.penalizar(reserva, EventoFiabilidade.Motivo.CADUCADA)
            total += 1
    return total
