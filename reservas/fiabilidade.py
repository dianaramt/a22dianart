"""Regras de fiabilidade: puntos de penalización e bloqueo temporal dos lectores.

Estas funcións chámanse desde servizos.py dentro dunha transacción, xusto cando
se pecha unha reserva. Cada cambio queda rexistrado en EventoFiabilidade.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from usuarios.models import Usuario

from .models import EventoFiabilidade, Reserva


def penalizar(reserva, motivo, actor=None):
    """Reserva non recollida ou caducada: suma puntos e bloquea se se chega ao límite."""
    _axustar(reserva, settings.BAMBI_PUNTOS_NON_RECOLLIDA, motivo, actor)


def recompensar(reserva, actor=None):
    """Reserva recollida: resta puntos, se o lector ten algún."""
    _axustar(reserva, -settings.BAMBI_PUNTOS_RECOLLIDA, EventoFiabilidade.Motivo.RECOLLIDA, actor)


def _axustar(reserva, cambio, motivo, actor):
    # Bloquear a fila do lector evita perder puntos se se pechan dúas reservas á vez
    lector = Usuario.objects.select_for_update().get(pk=reserva.lector_id)
    if cambio < 0:
        cambio = -min(-cambio, lector.puntos_penalizacion)  # os puntos nunca baixan de 0
    if cambio == 0:
        return

    lector.puntos_penalizacion += cambio
    Reserva.objects.filter(pk=reserva.pk).update(puntos_aplicados=cambio)
    EventoFiabilidade.objects.create(lector=lector, reserva=reserva, cambio=cambio, motivo=motivo, actor=actor)

    if lector.puntos_penalizacion >= settings.BAMBI_PUNTOS_BLOQUEO:
        # Se xa estaba bloqueado, o novo bloqueo empeza cando remate o anterior
        inicio = max(timezone.now(), lector.bloqueado_ata or timezone.now())
        lector.bloqueado_ata = inicio + timedelta(days=settings.BAMBI_DIAS_BLOQUEO)
        EventoFiabilidade.objects.create(
            lector=lector, reserva=reserva, cambio=-lector.puntos_penalizacion,
            motivo=EventoFiabilidade.Motivo.BLOQUEO, actor=actor,
        )
        lector.puntos_penalizacion = 0

    lector.save(update_fields=['puntos_penalizacion', 'bloqueado_ata'])
