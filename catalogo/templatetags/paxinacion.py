from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def url_paxina(context, numero):
    """?q=...&estado=...&paxina=N: mantén os filtros actuais e só cambia a páxina."""
    parametros = context['request'].GET.copy()
    parametros['paxina'] = numero
    return f'?{parametros.urlencode()}'
