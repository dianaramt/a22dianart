from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    # UserAdmin espera un campo username; adaptámolo ao correo
    ordering = ['email']
    list_display = ['email', 'nome_visible', 'rol', 'is_active']
    list_filter = ['rol', 'is_active', 'is_staff']
    search_fields = ['email', 'nome_visible']
    fieldsets = [
        (None, {'fields': ['email', 'password']}),
        (_('Datos persoais'), {'fields': ['nome_visible', 'first_name', 'last_name', 'idioma']}),
        (_('Fiabilidade'), {'fields': ['puntos_penalizacion', 'bloqueado_ata']}),
        (_('Rol e permisos'), {'fields': ['rol', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions']}),
        (_('Datas'), {'fields': ['last_login', 'date_joined']}),
    ]
    add_fieldsets = [
        (None, {'classes': ['wide'], 'fields': ['email', 'rol', 'password1', 'password2']}),
    ]
