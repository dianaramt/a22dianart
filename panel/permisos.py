from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import Http404

from centros.models import Centro


def admin_do_centro(vista):
    """Carga o centro do slug da URL e comproba que a persoa usuaria o administra.

    A vista recibe o centro en lugar do slug. Toda consulta do panel debe partir dese centro:
    así un administrador nunca pode ver nin tocar datos doutro centro.
    """

    @login_required
    @wraps(vista)
    def envolta(request, slug, *args, **kwargs):
        if not request.user.es_admin_centro:
            raise Http404
        centro = request.user.centros_administrados.filter(slug=slug).first()
        if centro is None or centro.estado == Centro.Estado.DESACTIVADO:
            raise Http404
        return vista(request, centro, *args, **kwargs)

    return envolta


def superusuario_plataforma(vista):
    """Só para o rol superusuario (panel da plataforma)."""

    @login_required
    @wraps(vista)
    def envolta(request, *args, **kwargs):
        if not request.user.es_superusuario:
            raise Http404
        return vista(request, *args, **kwargs)

    return envolta
