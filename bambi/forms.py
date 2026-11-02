from django import forms


class BootstrapMixin:
    """Engade as clases de Bootstrap aos widgets e marca os campos con erros."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect)):
                clase = 'form-check-input'
            elif isinstance(widget, forms.Select):
                clase = 'form-select'
            else:
                clase = 'form-control'
            widget.attrs['class'] = f'{widget.attrs.get("class", "")} {clase}'.strip()

    def full_clean(self):
        # Non consultar self.errors en __init__: validaría o formulario antes de que
        # as subclases axusten os seus campos. Márcanse os erros despois de validar.
        super().full_clean()
        for nome in self.errors:
            if nome not in self.fields:
                continue
            widget = self.fields[nome].widget
            widget.attrs['class'] = f'{widget.attrs.get("class", "")} is-invalid'.strip()
            widget.attrs['aria-invalid'] = 'true'
            # Debe coincidir co id do bloque de erros en templates/_formulario.html
            widget.attrs['aria-describedby'] = f'{self.add_prefix(nome)}-erros'
