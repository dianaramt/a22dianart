from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.views.i18n import set_language

from .forms import LoginForm, RexistroForm


def url_inicio(usuario):
    """Páxina á que vai cada rol tras iniciar sesión."""
    if usuario.es_lector:
        return reverse('reservas:area_persoal')
    if usuario.es_admin_centro:
        return reverse('panel:inicio')
    if usuario.es_superusuario:
        return reverse('plataforma:inicio')
    return reverse('centros:portada')


def url_seguinte(request):
    """O parámetro ?next só se usa se apunta a este mesmo sitio (evita redireccións abertas)."""
    seguinte = request.POST.get('next') or request.GET.get('next')
    if seguinte and url_has_allowed_host_and_scheme(seguinte, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return seguinte
    return None


def gardar_cookie_idioma(resposta, idioma):
    resposta.set_cookie(
        settings.LANGUAGE_COOKIE_NAME, idioma,
        max_age=settings.LANGUAGE_COOKIE_AGE, samesite=settings.LANGUAGE_COOKIE_SAMESITE,
        secure=settings.LANGUAGE_COOKIE_SECURE, httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
    )


class EntrarView(LoginView):
    template_name = 'usuarios/entrar.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        # Ao entrar, a interface pasa ao idioma gardado na conta
        resposta = super().form_valid(form)
        gardar_cookie_idioma(resposta, form.get_user().idioma)
        return resposta


@require_POST
def cambiar_idioma(request):
    """Como a vista set_language de Django, pero ademais garda o idioma na conta."""
    resposta = set_language(request)
    idioma = request.POST.get('language')
    if request.user.is_authenticated and idioma in dict(settings.LANGUAGES) and request.user.idioma != idioma:
        request.user.idioma = idioma
        request.user.save(update_fields=['idioma'])
    return resposta


@require_http_methods(['GET', 'POST'])
def rexistro(request):
    if request.user.is_authenticated:
        return redirect(url_inicio(request.user))

    form = RexistroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save(commit=False)
        usuario.idioma = request.LANGUAGE_CODE
        usuario.save()
        login(request, usuario)
        messages.success(request, _('Conta creada. Benvido/a a Bambi!'))
        return redirect(url_seguinte(request) or url_inicio(usuario))

    return render(request, 'usuarios/rexistro.html', {'form': form, 'next': url_seguinte(request)})


@require_GET
@login_required
def inicio(request):
    return redirect(url_inicio(request.user))
