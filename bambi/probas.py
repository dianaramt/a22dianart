"""Utilidades comúns para os tests de todas as apps."""

from catalogo.models import Exemplar
from centros.models import Centro
from usuarios.models import Usuario

CONTRASINAL = 'Bambi-Proba-2026!'


def crear_centro(slug='centro-proba', tipo=Centro.Tipo.BIBLIOTECA, estado=Centro.Estado.ACTIVO, **datos):
    datos.setdefault('nome', slug.replace('-', ' ').title())
    return Centro.objects.create(slug=slug, tipo=tipo, estado=estado, **datos)


def crear_exemplar(centro, titulo='Follas novas', autoria='Rosalía de Castro', **datos):
    return Exemplar.objects.create(centro=centro, titulo=titulo, autoria=autoria, **datos)


def crear_lector(email='lector@proba.test', **datos):
    return Usuario.objects.create_user(email, CONTRASINAL, **datos)


def crear_admin(centro=None, email='admin@proba.test'):
    admin = Usuario.objects.create_user(email, CONTRASINAL, rol=Usuario.Rol.ADMIN_CENTRO)
    if centro:
        centro.administradores.add(admin)
    return admin


def crear_superusuario(email='super@proba.test'):
    return Usuario.objects.create_superuser(email, CONTRASINAL)
