from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from catalogo.models import Exemplar


class Reserva(models.Model):
    class Estado(models.TextChoices):
        ACTIVA = 'activa', _('Activa')
        CANCELADA = 'cancelada', _('Cancelada')
        RECOLLIDA = 'recollida', _('Recollida')
        NON_RECOLLIDA = 'non_recollida', _('Non recollida')
        CADUCADA = 'caducada', _('Caducada')
        DEVOLTA = 'devolta', _('Devolta')

    lector = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reservas', verbose_name=_('lector')
    )
    exemplar = models.ForeignKey(Exemplar, on_delete=models.PROTECT, related_name='reservas', verbose_name=_('exemplar'))
    estado = models.CharField(_('estado'), max_length=20, choices=Estado.choices, default=Estado.ACTIVA)
    creado_en = models.DateTimeField(_('creado en'), auto_now_add=True)
    vence_en = models.DateTimeField(_('vence en'))
    actualizado_en = models.DateTimeField(_('actualizado en'), auto_now=True)
    # Para o sistema de fiabilidade (fase posterior)
    puntos_aplicados = models.SmallIntegerField(_('puntos aplicados'), default=0)

    class Meta:
        verbose_name = _('reserva')
        verbose_name_plural = _('reservas')
        ordering = ['-creado_en']
        constraints = [
            # Un exemplar non pode ter dúas reservas activas á vez
            models.UniqueConstraint(
                fields=['exemplar'],
                condition=Q(estado='activa'),
                name='unha_reserva_activa_por_exemplar',
            ),
        ]

    def __str__(self):
        return f'{self.exemplar.titulo} - {self.lector} ({self.get_estado_display()})'

    @property
    def centro(self):
        return self.exemplar.centro

    @property
    def cancelable_ata(self):
        """Momento ata o que o lector pode cancelar a reserva."""
        return self.creado_en + timedelta(minutes=settings.BAMBI_MINUTOS_CANCELACION)

    @property
    def pode_cancelarse(self):
        return self.estado == self.Estado.ACTIVA and timezone.now() <= self.cancelable_ata
