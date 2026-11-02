from datetime import timedelta

from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from bambi.probas import crear_admin, crear_centro, crear_exemplar, crear_lector
from catalogo.models import Exemplar

from .models import Reserva
from .servizos import ReservaErro, cancelar_reserva, crear_reserva


class ServizosReservaTests(TestCase):
    def setUp(self):
        self.centro = crear_centro(dias_reserva=5)
        self.exemplar = crear_exemplar(self.centro)
        self.ana = crear_lector('ana@proba.test')
        self.bea = crear_lector('bea@proba.test')

    def test_reservar_cambia_estado_e_aplica_prazo(self):
        reserva = crear_reserva(self.ana, self.exemplar.pk)
        self.exemplar.refresh_from_db()
        self.assertEqual(self.exemplar.estado, Exemplar.Estado.RESERVADO)
        self.assertAlmostEqual((reserva.vence_en - reserva.creado_en).total_seconds(), 5 * 86400, delta=60)

    def test_non_se_pode_reservar_duas_veces(self):
        crear_reserva(self.ana, self.exemplar.pk)
        with self.assertRaises(ReservaErro):
            crear_reserva(self.bea, self.exemplar.pk)

    def test_restricion_da_bd_unha_activa_por_exemplar(self):
        reserva = crear_reserva(self.ana, self.exemplar.pk)
        with self.assertRaises(IntegrityError):
            Reserva.objects.create(lector=self.bea, exemplar=self.exemplar, vence_en=reserva.vence_en)

    def test_admin_non_pode_reservar(self):
        with self.assertRaises(ReservaErro):
            crear_reserva(crear_admin(), self.exemplar.pk)

    def test_cancelar_libera_o_exemplar(self):
        reserva = crear_reserva(self.ana, self.exemplar.pk)
        cancelar_reserva(self.ana, reserva.pk)
        self.exemplar.refresh_from_db()
        self.assertEqual(self.exemplar.estado, Exemplar.Estado.DISPONIBLE)
        crear_reserva(self.bea, self.exemplar.pk)  # xa se pode reservar de novo

    def test_non_se_pode_cancelar_reserva_allea(self):
        reserva = crear_reserva(self.ana, self.exemplar.pk)
        with self.assertRaises(ReservaErro):
            cancelar_reserva(self.bea, reserva.pk)

    def envellecer(self, reserva, minutos):
        """Simula que a reserva se fixo hai `minutos` minutos."""
        Reserva.objects.filter(pk=reserva.pk).update(creado_en=timezone.now() - timedelta(minutes=minutos))
        reserva.refresh_from_db()

    @override_settings(BAMBI_MINUTOS_CANCELACION=5)
    def test_podese_cancelar_dentro_dos_5_minutos(self):
        reserva = crear_reserva(self.ana, self.exemplar.pk)
        self.envellecer(reserva, 4)
        self.assertTrue(reserva.pode_cancelarse)
        cancelar_reserva(self.ana, reserva.pk)

    @override_settings(BAMBI_MINUTOS_CANCELACION=5)
    def test_non_se_pode_cancelar_pasados_5_minutos(self):
        reserva = crear_reserva(self.ana, self.exemplar.pk)
        self.envellecer(reserva, 6)
        self.assertFalse(reserva.pode_cancelarse)
        with self.assertRaisesMessage(ReservaErro, '5 minutos'):
            cancelar_reserva(self.ana, reserva.pk)
        reserva.refresh_from_db()
        self.exemplar.refresh_from_db()
        self.assertEqual(reserva.estado, Reserva.Estado.ACTIVA)
        self.assertEqual(self.exemplar.estado, Exemplar.Estado.RESERVADO)

    @override_settings(BAMBI_MINUTOS_CANCELACION=15)
    def test_o_prazo_e_configurable(self):
        reserva = crear_reserva(self.ana, self.exemplar.pk)
        self.envellecer(reserva, 10)
        self.assertTrue(reserva.pode_cancelarse)


class VistasReservaTests(TestCase):
    def setUp(self):
        self.centro = crear_centro()
        self.exemplar = crear_exemplar(self.centro)
        self.ana = crear_lector('ana@proba.test')
        self.url_reservar = reverse('reservas:reservar', args=[self.exemplar.pk])

    def test_sen_sesion_leva_ao_login_con_next(self):
        resposta = self.client.get(self.url_reservar)
        self.assertRedirects(resposta, f"{reverse('usuarios:entrar')}?next={self.url_reservar}")

    def test_fluxo_completo(self):
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(self.url_reservar).status_code, 200)  # confirmación
        resposta = self.client.post(self.url_reservar)
        reserva = Reserva.objects.get(lector=self.ana)
        self.assertRedirects(resposta, reverse('reservas:detalle', args=[reserva.pk]))
        self.assertContains(self.client.get(reverse('reservas:area_persoal')), self.exemplar.titulo)

        self.client.post(reverse('reservas:cancelar', args=[reserva.pk]))
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, Reserva.Estado.CANCELADA)

    def test_reservas_alleas_dan_404(self):
        reserva = crear_reserva(self.ana, self.exemplar.pk)
        self.client.force_login(crear_lector('bea@proba.test'))
        self.assertEqual(self.client.get(reverse('reservas:detalle', args=[reserva.pk])).status_code, 404)

    def test_boton_cancelar_desaparece_pasado_o_prazo(self):
        reserva = crear_reserva(self.ana, self.exemplar.pk)
        self.client.force_login(self.ana)
        url_cancelar = reverse('reservas:cancelar', args=[reserva.pk])
        for url in [reverse('reservas:area_persoal'), reverse('reservas:detalle', args=[reserva.pk])]:
            self.assertContains(self.client.get(url), url_cancelar)

        Reserva.objects.filter(pk=reserva.pk).update(creado_en=timezone.now() - timedelta(hours=1))
        for url in [reverse('reservas:area_persoal'), reverse('reservas:detalle', args=[reserva.pk])]:
            resposta = self.client.get(url)
            self.assertNotContains(resposta, url_cancelar)
            self.assertContains(resposta, 'Xa non se pode cancelar')

        # Aínda que se envíe o formulario a man, o servidor rexeita a cancelación
        resposta = self.client.post(url_cancelar, follow=True)
        self.assertContains(resposta, 'Xa pasou o prazo')
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado, Reserva.Estado.ACTIVA)

    def test_cancelar_so_por_post(self):
        reserva = crear_reserva(self.ana, self.exemplar.pk)
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(reverse('reservas:cancelar', args=[reserva.pk])).status_code, 405)
