import unicodedata

from django.db.models import Q


def normalizar(texto):
    """Minúsculas, sen tiles nin guións: «Rosalía» -> «rosalia», «978-84-...» -> «97884...»."""
    texto = unicodedata.normalize('NFKD', texto or '')
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().replace('-', '')


def filtro_busca(consulta):
    """Q que exixe que cada palabra da consulta apareza en título, autoría ou ISBN."""
    filtro = Q()
    for palabra in normalizar(consulta).split():
        filtro &= Q(texto_busca__contains=palabra)
    return filtro
