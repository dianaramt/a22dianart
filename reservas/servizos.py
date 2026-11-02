"""Regras de negocio das reservas. As vistas chaman a estas funcións; non modifican estados directamente."""

from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from catalogo.models import Exemplar
from centros.models import Centro

from .models import Reserva


class ReservaErro(Exception):
    """Erro cunha mensaxe pensada para amosarlla á persoa usuaria."""


def crear_reserva(lector, exemplar_id):
    if not lector.is_active or not lector.es_lector:
        raise ReservaErro(_('Só as contas de lector poden reservar libros.'))
    # O bloqueo por fiabilidade comprobarase aquí (fase posterior)

    with transaction.atomic():
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
    reserva.estado = estado_reserva
    reserva.save(update_fields=['estado', 'actualizado_en'])
    Exemplar.objects.filter(pk=reserva.exemplar_id).update(estado=estado_exemplar)
    return reserva


def marcar_recollida(centro, reserva_id):
    with transaction.atomic():
        reserva = _reserva_do_centro(centro, reserva_id, Reserva.Estado.ACTIVA)
        # Biblioteca: o libro queda prestado ata a devolución. Libraría: vendeuse, sae do catálogo
        if centro.tipo == Centro.Tipo.BIBLIOTECA:
            estado_exemplar = Exemplar.Estado.PRESTADO
        else:
            estado_exemplar = Exemplar.Estado.RETIRADO
        return _pechar(reserva, Reserva.Estado.RECOLLIDA, estado_exemplar)


def marcar_non_recollida(centro, reserva_id):
    with transaction.atomic():
        reserva = _reserva_do_centro(centro, reserva_id, Reserva.Estado.ACTIVA)
        # A penalización de puntos aplicarase aquí (fase de fiabilidade)
        return _pechar(reserva, Reserva.Estado.NON_RECOLLIDA, Exemplar.Estado.DISPONIBLE)


def marcar_devolta(centro, reserva_id):
    if centro.tipo != Centro.Tipo.BIBLIOTECA:
        raise ReservaErro(_('Só as bibliotecas rexistran devolucións.'))
    with transaction.atomic():
        reserva = _reserva_do_centro(centro, reserva_id, Reserva.Estado.RECOLLIDA)
        return _pechar(reserva, Reserva.Estado.DEVOLTA, Exemplar.Estado.DISPONIBLE)
