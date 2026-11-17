from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UsuarioManager(BaseUserManager):
    """Xestor para crear usuarios identificados polo correo en lugar do username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_('O correo é obrigatorio'))
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('rol', Usuario.Rol.SUPERUSUARIO)
        if not extra_fields['is_staff'] or not extra_fields['is_superuser']:
            raise ValueError(_('Un superusuario debe ter is_staff e is_superuser'))
        return self._create_user(email, password, **extra_fields)


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        LECTOR = 'lector', _('Lector')
        ADMIN_CENTRO = 'admin_centro', _('Administrador de centro')
        SUPERUSUARIO = 'superusuario', _('Superusuario')

    # Inicio de sesión co correo: eliminamos o username de AbstractUser
    username = None
    email = models.EmailField(_('correo electrónico'), unique=True)
    nome_visible = models.CharField(_('nome visible'), max_length=100, blank=True)
    rol = models.CharField(_('rol'), max_length=20, choices=Rol.choices, default=Rol.LECTOR)
    idioma = models.CharField(
        _('idioma'), max_length=5, choices=settings.LANGUAGES, default=settings.LANGUAGE_CODE
    )
    # Fiabilidade do lector (o historial de cambios está en reservas.EventoFiabilidade)
    puntos_penalizacion = models.PositiveSmallIntegerField(_('puntos de penalización'), default=0)
    bloqueado_ata = models.DateTimeField(_('bloqueado ata'), null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UsuarioManager()

    class Meta:
        verbose_name = _('usuario')
        verbose_name_plural = _('usuarios')

    def __str__(self):
        return self.nome_visible or self.email

    @property
    def es_lector(self):
        return self.rol == self.Rol.LECTOR

    @property
    def es_admin_centro(self):
        return self.rol == self.Rol.ADMIN_CENTRO

    @property
    def es_superusuario(self):
        return self.rol == self.Rol.SUPERUSUARIO

    @property
    def esta_bloqueado(self):
        return self.bloqueado_ata is not None and self.bloqueado_ata > timezone.now()
