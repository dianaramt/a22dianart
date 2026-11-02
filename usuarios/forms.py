from django import forms
from django.contrib.auth.forms import AuthenticationForm, BaseUserCreationForm
from django.utils.translation import gettext_lazy as _

from bambi.forms import BootstrapMixin

from .models import Usuario


class LoginForm(BootstrapMixin, AuthenticationForm):
    def clean_username(self):
        # Os correos gárdanse en minúsculas
        return self.cleaned_data['username'].strip().lower()


class RexistroForm(BootstrapMixin, BaseUserCreationForm):
    """Alta de lectores. O rol non se pide: sempre é lector."""

    class Meta:
        model = Usuario
        fields = ['email', 'nome_visible']
        help_texts = {'nome_visible': _('Nome co que te verá o centro ao recoller a reserva.')}

    def clean_email(self):
        # Evita contas duplicadas que só se diferencian en maiúsculas
        email = self.cleaned_data['email'].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_('Xa existe unha conta con este correo.'))
        return email

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.rol = Usuario.Rol.LECTOR
        if commit:
            usuario.save()
        return usuario
