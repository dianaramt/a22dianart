from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from bambi.probas import crear_centro, crear_exemplar

from .models import Centro


class PortadaTests(TestCase):
    def test_so_amosa_centros_activos(self):
        crear_centro('activo', nome='Biblioteca Activa')
        crear_centro('pendente', nome='Libraría Pendente', estado=Centro.Estado.PENDENTE)
        crear_centro('desactivado', nome='Centro Desactivado', estado=Centro.Estado.DESACTIVADO)
        resposta = self.client.get(reverse('centros:portada'))
        self.assertContains(resposta, 'Biblioteca Activa')
        self.assertNotContains(resposta, 'Libraría Pendente')
        self.assertNotContains(resposta, 'Centro Desactivado')

    def test_tres_idiomas(self):
        crear_exemplar(crear_centro())
        casos = {
            'gl': ['Atopa o teu próximo libro preto de ti', 'Dispoñible'],
            'es': ['Encuentra tu próximo libro cerca de ti', 'Disponible'],
            'en': ['Find your next book close to home', 'Available'],
        }
        for idioma, textos in casos.items():
            with self.subTest(idioma=idioma):
                self.client.post(reverse('set_language'), {'language': idioma, 'next': '/'})
                portada = self.client.get('/')
                self.assertContains(portada, f'lang="{idioma}"')
                self.assertContains(portada, textos[0])
                # Tamén se traducen as etiquetas dos modelos (estado do exemplar)
                self.assertContains(self.client.get(reverse('catalogo:buscar'), {'q': 'follas'}), textos[1])


class EscaparateTests(TestCase):
    def setUp(self):
        self.centro = crear_centro(cor_principal='#123456', tipografia=Centro.Tipografia.SERIF)

    def test_amosa_catalogo_sen_retirados(self):
        crear_exemplar(self.centro, titulo='Libro Visible')
        crear_exemplar(self.centro, titulo='Libro Retirado', estado='retirado')
        crear_exemplar(crear_centro('outro'), titulo='Libro Doutro')
        resposta = self.client.get(reverse('centros:escaparate', args=[self.centro.slug]))
        self.assertContains(resposta, 'Libro Visible')
        self.assertNotContains(resposta, 'Libro Retirado')
        self.assertNotContains(resposta, 'Libro Doutro')

    def test_aplica_identidade_visual(self):
        resposta = self.client.get(reverse('centros:escaparate', args=[self.centro.slug]))
        self.assertContains(resposta, '#123456')
        self.assertContains(resposta, 'Georgia')

    def test_centro_non_activo_da_404(self):
        crear_centro('pendente', estado=Centro.Estado.PENDENTE)
        self.assertEqual(self.client.get(reverse('centros:escaparate', args=['pendente'])).status_code, 404)

    def test_cor_so_admite_hexadecimal(self):
        self.centro.cor_principal = 'red;}body{display:none'
        with self.assertRaises(ValidationError):
            self.centro.full_clean()


class CargarDemoTests(TestCase):
    def test_pode_executarse_varias_veces_e_borrar(self):
        call_command('cargar_demo', stdout=StringIO())
        call_command('cargar_demo', stdout=StringIO())
        self.assertEqual(Centro.objects.count(), 3)
        call_command('cargar_demo', '--borrar', stdout=StringIO())
        self.assertFalse(Centro.objects.exists())

    def test_non_toca_datos_que_non_son_de_demo(self):
        crear_centro('meu-centro')
        call_command('cargar_demo', '--borrar', stdout=StringIO())
        self.assertTrue(Centro.objects.filter(slug='meu-centro').exists())
