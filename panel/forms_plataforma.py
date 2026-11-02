from django import forms
from django.contrib.auth.password_validation import validate_password
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from bambi.forms import BootstrapMixin
from centros.models import Centro
from usuarios.models import Usuario


class CentroAltaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Centro
        fields = ['nome', 'tipo', 'slug', 'localizacion', 'descricion']
        widgets = {'descricion': forms.Textarea(attrs={'rows': 3})}
        help_texts = {'slug': _('Parte da URL do escaparate (/centro/<slug>/). Se o deixas baleiro, xérase a partir do nome.')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False

    def clean_slug(self):
        slug = self.cleaned_data.get('slug') or slugify(self.cleaned_data.get('nome', ''))
        if not slug:
            raise forms.ValidationError(_('Indica un slug válido.'))
        # Se xa existe, engade un número: biblioteca-lugo, biblioteca-lugo-2...
        base, n = slug, 2
        while Centro.objects.filter(slug=slug).exclude(pk=self.instance.pk).exists():
            slug = f'{base}-{n}'
            n += 1
        return slug


class AdministradorForm(BootstrapMixin, forms.Form):
    """Asigna un administrador a un centro: unha conta de administrador existente ou unha nova."""

    email = forms.EmailField(label=_('Correo do administrador'))
    nome_visible = forms.CharField(label=_('Nome visible'), max_length=100, required=False)
    contrasinal1 = forms.CharField(
        label=_('Contrasinal inicial'), required=False, widget=forms.PasswordInput(render_value=False),
        help_text=_('Só se a conta é nova. Comunícalla ao centro por unha canle segura.'),
    )
    contrasinal2 = forms.CharField(label=_('Repite o contrasinal'), required=False, widget=forms.PasswordInput)

    def __init__(self, *args, centro=None, **kwargs):
        self.centro = centro
        self.usuario_existente = None
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        existente = Usuario.objects.filter(email__iexact=email).first()
        if existente:
            # Non convertir lectores nin superusuarios en administradores sen querer
            if not existente.es_admin_centro:
                raise forms.ValidationError(_('Este correo pertence a unha conta que non é de administrador de centro.'))
            if self.centro and self.centro.administradores.filter(pk=existente.pk).exists():
                raise forms.ValidationError(_('Esta persoa xa administra o centro.'))
            self.usuario_existente = existente
        return email

    def clean(self):
        datos = super().clean()
        if self.usuario_existente or 'email' not in datos:
            return datos
        # Conta nova: o contrasinal é obrigatorio e debe cumprir as regras
        c1, c2 = datos.get('contrasinal1'), datos.get('contrasinal2')
        if not c1:
            self.add_error('contrasinal1', _('As contas novas necesitan un contrasinal inicial.'))
        elif c1 != c2:
            self.add_error('contrasinal2', _('Os contrasinais non coinciden.'))
        else:
            try:
                validate_password(c1, Usuario(email=datos['email']))
            except forms.ValidationError as erro:
                self.add_error('contrasinal1', erro)
        return datos

    def gardar(self, centro):
        usuario = self.usuario_existente
        if usuario is None:
            usuario = Usuario.objects.create_user(
                self.cleaned_data['email'],
                self.cleaned_data['contrasinal1'],
                nome_visible=self.cleaned_data['nome_visible'],
                rol=Usuario.Rol.ADMIN_CENTRO,
            )
        centro.administradores.add(usuario)
        return usuario
