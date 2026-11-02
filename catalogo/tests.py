from django.test import TestCase
from django.urls import reverse

from bambi.probas import crear_centro, crear_exemplar
from centros.models import Centro

from .busca import normalizar


class NormalizarTests(TestCase):
    def test_quita_tiles_maiusculas_e_guions(self):
        self.assertEqual(normalizar('Rosalía CASTRO'), 'rosalia castro')
        self.assertEqual(normalizar('978-84-9121'), '978849121')


class BuscaTests(TestCase):
    def setUp(self):
        self.centro = crear_centro()
        self.follas = crear_exemplar(self.centro, isbn='978-84-9121-000-1')
        crear_exemplar(self.centro, titulo='Memorias dun neno labrego', autoria='Xosé Neira Vilas')
        crear_exemplar(self.centro, titulo='Follas retiradas', estado='retirado')
        crear_exemplar(crear_centro('pendente', estado=Centro.Estado.PENDENTE), titulo='Follas pendentes')

    def buscar(self, consulta):
        return self.client.get(reverse('catalogo:buscar'), {'q': consulta})

    def test_isbn_gardase_sen_guions(self):
        self.assertEqual(self.follas.isbn, '9788491210001')

    def test_sen_tiles_e_varias_palabras(self):
        for consulta in ['rosalia', 'ROSALÍA castro', 'castro follas']:
            with self.subTest(consulta=consulta):
                self.assertContains(self.buscar(consulta), 'Follas novas')

    def test_isbn_con_e_sen_guions(self):
        self.assertContains(self.buscar('978-84-9121-000-1'), 'Follas novas')
        self.assertContains(self.buscar('9788491210001'), 'Follas novas')

    def test_non_amosa_retirados_nin_centros_non_activos(self):
        resposta = self.buscar('follas')
        self.assertNotContains(resposta, 'Follas retiradas')
        self.assertNotContains(resposta, 'Follas pendentes')

    def test_sen_resultados(self):
        self.assertContains(self.buscar('quixote'), '0 resultados')

    def test_busca_dentro_do_escaparate(self):
        resposta = self.client.get(reverse('centros:escaparate', args=[self.centro.slug]), {'q': 'xose'})
        self.assertContains(resposta, 'Memorias dun neno')
        self.assertNotContains(resposta, 'Follas novas')


class DetalleTests(TestCase):
    def test_exemplar_doutro_centro_na_url_da_404(self):
        centro = crear_centro()
        doutro = crear_exemplar(crear_centro('outro'))
        resposta = self.client.get(reverse('catalogo:detalle', args=[centro.slug, doutro.pk]))
        self.assertEqual(resposta.status_code, 404)
