from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Centro(models.Model):
    class Tipo(models.TextChoices):
        LIBRARIA = 'libraria', _('Libraría')
        BIBLIOTECA = 'biblioteca', _('Biblioteca')

    class Estado(models.TextChoices):
        PENDENTE = 'pendente', _('Pendente')
        ACTIVO = 'activo', _('Activo')
        DESACTIVADO = 'desactivado', _('Desactivado')

    class Tipografia(models.TextChoices):
        SANS = 'sans', _('Sen serifa')
        SERIF = 'serif', _('Con serifa')
        MONO = 'mono', _('Monoespazada')

    nome = models.CharField(_('nome'), max_length=150)
    tipo = models.CharField(_('tipo'), max_length=20, choices=Tipo.choices)
    # Identificador para a URL pública do escaparate: /centro/<slug>/
    slug = models.SlugField(_('slug'), max_length=150, unique=True)
    descricion = models.TextField(_('descrición'), blank=True)
    localizacion = models.CharField(_('localización'), max_length=255, blank=True)
    estado = models.CharField(_('estado'), max_length=20, choices=Estado.choices, default=Estado.PENDENTE)

    # Personalización do escaparate
    logo = models.ImageField(_('logo'), upload_to='logos/', blank=True)
    cor_principal = models.CharField(_('cor principal'), max_length=7, default='#2f5d50')
    cor_secundaria = models.CharField(_('cor secundaria'), max_length=7, default='#f4efe6')
    tipografia = models.CharField(_('tipografía'), max_length=10, choices=Tipografia.choices, default=Tipografia.SANS)

    # Días que ten o lector para recoller unha reserva
    dias_reserva = models.PositiveSmallIntegerField(_('días para recoller'), default=3)

    # Táboa intermedia USUARIO_CENTRO: un centro pode ter varios administradores
    administradores = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='centros_administrados',
        blank=True,
        verbose_name=_('administradores'),
    )

    creado_en = models.DateTimeField(_('creado en'), auto_now_add=True)

    class Meta:
        verbose_name = _('centro')
        verbose_name_plural = _('centros')
        ordering = ['nome']

    def __str__(self):
        return self.nome

    @property
    def esta_activo(self):
        return self.estado == self.Estado.ACTIVO
