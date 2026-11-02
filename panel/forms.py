from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _

from bambi.forms import BootstrapMixin
from catalogo.models import Exemplar
from centros.models import Centro
from reservas.models import Reserva


class ExemplarForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Exemplar
        fields = ['titulo', 'autoria', 'isbn', 'descricion', 'estado']
        widgets = {'descricion': forms.Textarea(attrs={'rows': 4})}
        help_texts = {'isbn': _('Opcional. 10 ou 13 díxitos, con ou sen guións.')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        estado = self.fields['estado']
        if self.ten_reserva_aberta():
            # O estado xestiónase desde as reservas mentres haxa unha aberta
            estado.disabled = True
            estado.help_text = _('Este exemplar ten unha reserva ou préstamo en curso; o estado cámbiase desde Reservas.')
        else:
            # «Reservado» só o pon o sistema ao reservar un lector
            estado.choices = [c for c in Exemplar.Estado.choices if c[0] != Exemplar.Estado.RESERVADO]
            estado.help_text = _('«Prestado» permite rexistrar un préstamo feito no mostrador, sen reserva.')

    def ten_reserva_aberta(self):
        if not self.instance.pk:
            return False
        # Reservado, ou prestado a través dunha reserva recollida (pendente de devolución)
        return self.instance.estado == Exemplar.Estado.RESERVADO or (
            self.instance.estado == Exemplar.Estado.PRESTADO
            and self.instance.reservas.filter(estado=Reserva.Estado.RECOLLIDA).exists()
        )

    def clean_isbn(self):
        isbn = self.cleaned_data['isbn'].replace('-', '').replace(' ', '').upper()
        if not isbn:
            return isbn
        valido = (len(isbn) == 13 and isbn.isdigit()) or (
            len(isbn) == 10 and isbn[:9].isdigit() and (isbn[9].isdigit() or isbn[9] == 'X')
        )
        if not valido:
            raise forms.ValidationError(_('O ISBN debe ter 10 ou 13 díxitos.'))
        return isbn


class EscaparateForm(BootstrapMixin, forms.ModelForm):
    """Datos que o propio centro pode cambiar. Tipo, slug e estado só os cambia o superusuario."""

    class Meta:
        model = Centro
        fields = ['nome', 'descricion', 'localizacion', 'logo', 'cor_principal', 'cor_secundaria', 'tipografia', 'dias_reserva']
        widgets = {
            'descricion': forms.Textarea(attrs={'rows': 5}),
            'cor_principal': forms.TextInput(attrs={'type': 'color', 'class': 'form-control-color'}),
            'cor_secundaria': forms.TextInput(attrs={'type': 'color', 'class': 'form-control-color'}),
            'logo': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }
        help_texts = {
            'cor_principal': _('Úsase no menú e nos botóns: escolle unha cor escura para que o texto branco se lea ben.'),
            'dias_reserva': _('Días que ten o lector para recoller unha reserva (entre 1 e 30).'),
        }

    def clean_dias_reserva(self):
        dias = self.cleaned_data['dias_reserva']
        if not 1 <= dias <= 30:
            raise forms.ValidationError(_('Indica un valor entre 1 e 30 días.'))
        return dias

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        # Só comprobar ficheiros novos (non o que xa estaba gardado)
        if isinstance(logo, UploadedFile) and logo.size > 2 * 1024 * 1024:
            raise forms.ValidationError(_('O logo non pode ocupar máis de 2 MB.'))
        return logo
