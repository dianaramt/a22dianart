from django.db import models
from django.utils.translation import gettext_lazy as _

from centros.models import Centro

from .busca import normalizar


class Exemplar(models.Model):
    """Unha copia física dun libro nun centro. Tres copias = tres exemplares."""

    class Estado(models.TextChoices):
        DISPONIBLE = 'disponible', _('Dispoñible')
        RESERVADO = 'reservado', _('Reservado')
        PRESTADO = 'prestado', _('Prestado')
        # Non se borra para conservar o historial de reservas
        RETIRADO = 'retirado', _('Retirado')

    centro = models.ForeignKey(Centro, on_delete=models.CASCADE, related_name='exemplares', verbose_name=_('centro'))
    titulo = models.CharField(_('título'), max_length=255)
    autoria = models.CharField(_('autoría'), max_length=255)
    # Opcional e non único: varios exemplares (ou centros) poden compartir ISBN
    isbn = models.CharField(_('ISBN'), max_length=17, blank=True)
    descricion = models.TextField(_('descrición'), blank=True)
    estado = models.CharField(_('estado'), max_length=20, choices=Estado.choices, default=Estado.DISPONIBLE)
    creado_en = models.DateTimeField(_('creado en'), auto_now_add=True)
    # Título, autoría e ISBN normalizados (ver busca.py); calcúlase ao gardar
    texto_busca = models.TextField(editable=False, default='')

    class Meta:
        verbose_name = _('exemplar')
        verbose_name_plural = _('exemplares')
        ordering = ['titulo']
        indexes = [models.Index(fields=['centro', 'estado'])]

    def __str__(self):
        return f'{self.titulo} ({self.centro})'

    def save(self, *args, **kwargs):
        # O ISBN gárdase sen guións nin espazos para que sexa uniforme
        self.isbn = self.isbn.replace('-', '').replace(' ', '').upper()
        self.texto_busca = normalizar(f'{self.titulo} {self.autoria} {self.isbn}')
        super().save(*args, **kwargs)

    @property
    def esta_disponible(self):
        return self.estado == self.Estado.DISPONIBLE
