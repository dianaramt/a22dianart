from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from usuarios.views import cambiar_idioma

urlpatterns = [
    path('admin/', admin.site.urls),
    # Cambio de idioma (formulario do menú); tamén o garda na conta se hai sesión
    path('i18n/setlang/', cambiar_idioma, name='set_language'),
    path('conta/', include('usuarios.urls')),
    path('reservas/', include('reservas.urls')),
    path('panel/', include('panel.urls')),
    path('plataforma/', include('panel.urls_plataforma')),
    path('', include('centros.urls')),
    path('', include('catalogo.urls')),
]

# En desenvolvemento Django serve os ficheiros subidos (logos)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
