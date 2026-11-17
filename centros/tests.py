import os
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from bambi.probas import crear_admin, crear_centro, crear_exemplar
from usuarios.models import Usuario

from .models import Centro, Visita
from .visitas import resumo_visitas


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


class VisitasTests(TestCase):
    def setUp(self):
        self.centro = crear_centro()
        self.url = reverse('centros:escaparate', args=[self.centro.slug])

    def total_hoxe(self, centro=None):
        visita = Visita.objects.filter(centro=centro or self.centro, dia=timezone.localdate()).first()
        return visita.total if visita else 0

    def test_conta_as_entradas_nunha_fila_por_dia(self):
        for _ in range(3):
            self.client.get(self.url)
        self.assertEqual(self.total_hoxe(), 3)
        self.assertEqual(Visita.objects.count(), 1)

    def test_non_conta_paxinacion_nin_buscas(self):
        self.client.get(self.url, {'paxina': 2})
        self.client.get(self.url, {'q': 'follas'})
        self.assertEqual(self.total_hoxe(), 0)

    def test_non_conta_ao_persoal_do_centro(self):
        self.client.force_login(crear_admin(self.centro))
        self.client.get(self.url)
        self.assertEqual(self.total_hoxe(), 0)
        # Un admin doutro centro si conta como visitante
        self.client.force_login(crear_admin(crear_centro('outro'), email='outro@proba.test'))
        self.client.get(self.url)
        self.assertEqual(self.total_hoxe(), 1)

    def test_non_conta_centros_non_activos(self):
        pendente = crear_centro('pendente', estado=Centro.Estado.PENDENTE)
        self.client.get(reverse('centros:escaparate', args=[pendente.slug]))
        self.assertFalse(Visita.objects.exists())

    def test_resumo_agrega_por_periodos(self):
        hoxe = timezone.localdate()
        for dias_atras, total in [(0, 2), (3, 5), (10, 7), (40, 11)]:
            Visita.objects.create(centro=self.centro, dia=hoxe - timedelta(days=dias_atras), total=total)
        resumo = resumo_visitas(self.centro)
        self.assertEqual(
            (resumo['hoxe'], resumo['semana'], resumo['mes'], resumo['total']), (2, 7, 14, 25)
        )
        self.assertEqual(len(resumo['serie']), 14)
        self.assertEqual(resumo['serie'][-1], (hoxe, 2, 29))  # 2 de 7 (o máximo) ≈ 29 %

    def test_panel_do_centro_amosa_as_visitas(self):
        Visita.objects.create(centro=self.centro, dia=timezone.localdate(), total=42)
        self.client.force_login(crear_admin(self.centro))
        resposta = self.client.get(reverse('panel:resumo', args=[self.centro.slug]))
        self.assertContains(resposta, 'Visitas ao escaparate')
        self.assertContains(resposta, '42')


class CargarDemoTests(TestCase):
    @override_settings(DEBUG=True)
    def test_pode_executarse_varias_veces_e_borrar(self):
        call_command('cargar_demo', stdout=StringIO())
        call_command('cargar_demo', stdout=StringIO())
        self.assertEqual(Centro.objects.count(), 3)
        call_command('cargar_demo', '--borrar', stdout=StringIO())
        self.assertFalse(Centro.objects.exists())

    @override_settings(DEBUG=True)
    def test_se_baleira_non_recarga_se_xa_hai_usuarios(self):
        call_command('cargar_demo', '--se-baleira', stdout=StringIO())
        self.assertEqual(Centro.objects.count(), 3)
        # Un cambio feito despois (como faría quen proba a web) non se perde ao volver arrancar
        Centro.objects.filter(slug='biblioteca-os-castineiros').update(nome='Nome cambiado')
        call_command('cargar_demo', '--se-baleira', stdout=StringIO())
        self.assertTrue(Centro.objects.filter(nome='Nome cambiado').exists())

    def test_non_toca_datos_que_non_son_de_demo(self):
        crear_centro('meu-centro')
        call_command('cargar_demo', '--borrar', stdout=StringIO())
        self.assertTrue(Centro.objects.filter(slug='meu-centro').exists())

    @override_settings(DEBUG=False)
    def test_en_producion_exixe_contrasinal_propio(self):
        with patch.dict(os.environ):
            os.environ.pop('BAMBI_DEMO_CONTRASINAL', None)
            with self.assertRaises(CommandError):
                call_command('cargar_demo', stdout=StringIO())
        self.assertFalse(Centro.objects.exists())

    @override_settings(DEBUG=False)
    def test_en_producion_usa_o_contrasinal_da_variable(self):
        with patch.dict(os.environ, {'BAMBI_DEMO_CONTRASINAL': 'Outro-Contrasinal-Proba'}):
            call_command('cargar_demo', stdout=StringIO())
        superusuario = Usuario.objects.get(email='plataforma@demo.bambi.test')
        self.assertTrue(superusuario.check_password('Outro-Contrasinal-Proba'))
        self.assertFalse(superusuario.check_password('Demo-Bambi-2026'))
