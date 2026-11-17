from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from bambi.probas import crear_admin, crear_centro, crear_exemplar, crear_lector
from catalogo.models import Exemplar
from usuarios.models import Usuario

from .models import EventoFiabilidade, Reserva
from .servizos import (
    ReservaErro, caducar_reservas, cancelar_reserva, crear_reserva, marcar_non_recollida, marcar_recollida,
)


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


@override_settings(BAMBI_PUNTOS_NON_RECOLLIDA=1, BAMBI_PUNTOS_RECOLLIDA=1, BAMBI_PUNTOS_BLOQUEO=3, BAMBI_DIAS_BLOQUEO=14)
class FiabilidadeTests(TestCase):
    def setUp(self):
        self.centro = crear_centro()
        self.admin = crear_admin(self.centro)
        self.ana = crear_lector('ana@proba.test')

    def reservar(self, lector=None):
        return crear_reserva(lector or self.ana, crear_exemplar(self.centro).pk)

    def non_recoller(self, veces=1):
        for _ in range(veces):
            marcar_non_recollida(self.centro, self.reservar().pk, actor=self.admin)
        self.ana.refresh_from_db()

    def test_non_recollida_suma_punto_e_garda_evento(self):
        reserva = self.reservar()
        marcar_non_recollida(self.centro, reserva.pk, actor=self.admin)
        self.ana.refresh_from_db()
        reserva.refresh_from_db()
        self.assertEqual(self.ana.puntos_penalizacion, 1)
        self.assertEqual(reserva.puntos_aplicados, 1)
        evento = EventoFiabilidade.objects.get()
        self.assertEqual(
            (evento.lector, evento.reserva, evento.cambio, evento.motivo, evento.actor),
            (self.ana, reserva, 1, EventoFiabilidade.Motivo.NON_RECOLLIDA, self.admin),
        )

    def test_recollida_resta_punto_pero_non_baixa_de_cero(self):
        marcar_recollida(self.centro, self.reservar().pk)
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.puntos_penalizacion, 0)
        self.assertFalse(EventoFiabilidade.objects.exists())  # sen cambio, sen evento

        self.non_recoller(2)
        marcar_recollida(self.centro, self.reservar().pk)
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.puntos_penalizacion, 1)

    def test_ao_chegar_ao_limite_bloquea_e_reinicia(self):
        self.non_recoller(3)
        self.assertTrue(self.ana.esta_bloqueado)
        self.assertEqual(self.ana.puntos_penalizacion, 0)
        dias = (self.ana.bloqueado_ata - timezone.now()).total_seconds() / 86400
        self.assertAlmostEqual(dias, 14, delta=0.01)
        bloqueo = EventoFiabilidade.objects.get(motivo=EventoFiabilidade.Motivo.BLOQUEO)
        self.assertEqual(bloqueo.cambio, -3)

    def test_lector_bloqueado_non_pode_reservar(self):
        self.non_recoller(3)
        with self.assertRaisesMessage(ReservaErro, 'bloqueada'):
            self.reservar()
        # Os demais lectores non se ven afectados
        self.reservar(crear_lector('bea@proba.test'))

    def test_o_bloqueo_remata_soa(self):
        self.non_recoller(3)
        Usuario.objects.filter(pk=self.ana.pk).update(bloqueado_ata=timezone.now() - timedelta(minutes=1))
        self.ana.refresh_from_db()
        self.assertFalse(self.ana.esta_bloqueado)
        self.reservar()

    def test_bloqueo_novo_suma_ao_que_queda(self):
        self.non_recoller(3)
        primeiro = self.ana.bloqueado_ata
        # Reservas feitas antes do bloqueo que tampouco se recollen
        Usuario.objects.filter(pk=self.ana.pk).update(bloqueado_ata=None)
        reservas = [self.reservar() for _ in range(3)]
        Usuario.objects.filter(pk=self.ana.pk).update(bloqueado_ata=primeiro)
        for reserva in reservas:
            marcar_non_recollida(self.centro, reserva.pk)
        self.ana.refresh_from_db()
        self.assertAlmostEqual((self.ana.bloqueado_ata - primeiro).total_seconds(), 14 * 86400, delta=60)

    def test_cancelar_a_tempo_non_penaliza(self):
        reserva = self.reservar()
        cancelar_reserva(self.ana, reserva.pk)
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.puntos_penalizacion, 0)

    def test_area_persoal_amosa_puntos_e_bloqueo(self):
        self.client.force_login(self.ana)
        self.non_recoller(2)
        resposta = self.client.get(reverse('reservas:area_persoal'))
        self.assertContains(resposta, 'Tes 2 puntos de penalización')
        self.assertContains(resposta, 'Reserva non recollida')

        self.non_recoller(1)
        resposta = self.client.get(reverse('reservas:area_persoal'))
        self.assertContains(resposta, 'Non podes facer reservas ata o')
        self.assertContains(resposta, 'Bloqueo temporal')

    def test_confirmacion_sen_boton_se_esta_bloqueado(self):
        self.non_recoller(3)
        self.client.force_login(self.ana)
        exemplar = crear_exemplar(self.centro)
        url = reverse('reservas:reservar', args=[exemplar.pk])
        resposta = self.client.get(url)
        self.assertContains(resposta, 'Non podes facer reservas ata o')
        self.assertNotContains(resposta, 'Confirmar reserva</button>')
        # Aínda que se envíe o formulario a man, o servidor rexeita a reserva
        resposta = self.client.post(url, follow=True)
        self.assertContains(resposta, 'bloqueada')
        exemplar.refresh_from_db()
        self.assertEqual(exemplar.estado, Exemplar.Estado.DISPONIBLE)


@override_settings(BAMBI_PUNTOS_NON_RECOLLIDA=1, BAMBI_PUNTOS_BLOQUEO=3)
class CaducidadeTests(TestCase):
    def setUp(self):
        self.centro = crear_centro()
        self.ana = crear_lector('ana@proba.test')

    def reserva_vencida(self, horas=1):
        reserva = crear_reserva(self.ana, crear_exemplar(self.centro).pk)
        Reserva.objects.filter(pk=reserva.pk).update(vence_en=timezone.now() - timedelta(hours=horas))
        return reserva

    def test_caduca_so_as_vencidas(self):
        vencida = self.reserva_vencida()
        en_prazo = crear_reserva(self.ana, crear_exemplar(self.centro).pk)
        self.assertEqual(caducar_reservas(), 1)

        vencida.refresh_from_db()
        en_prazo.refresh_from_db()
        self.assertEqual(vencida.estado, Reserva.Estado.CADUCADA)
        self.assertEqual(en_prazo.estado, Reserva.Estado.ACTIVA)
        self.assertEqual(vencida.exemplar.estado, Exemplar.Estado.DISPONIBLE)
        # Penalización aplicada polo sistema (sen actor)
        evento = EventoFiabilidade.objects.get()
        self.assertEqual((evento.motivo, evento.cambio, evento.actor), (EventoFiabilidade.Motivo.CADUCADA, 1, None))
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.puntos_penalizacion, 1)

    def test_executar_duas_veces_non_penaliza_de_novo(self):
        self.reserva_vencida()
        caducar_reservas()
        self.assertEqual(caducar_reservas(), 0)
        self.assertEqual(EventoFiabilidade.objects.count(), 1)

    def test_non_libera_un_exemplar_retirado(self):
        reserva = self.reserva_vencida()
        Exemplar.objects.filter(pk=reserva.exemplar_id).update(estado=Exemplar.Estado.RETIRADO)
        caducar_reservas()
        reserva.exemplar.refresh_from_db()
        self.assertEqual(reserva.exemplar.estado, Exemplar.Estado.RETIRADO)

    def test_tres_caducadas_bloquean(self):
        for _ in range(3):
            self.reserva_vencida()
        caducar_reservas()
        self.ana.refresh_from_db()
        self.assertTrue(self.ana.esta_bloqueado)

    def test_centro_non_pode_marcar_unha_caducada(self):
        reserva = self.reserva_vencida()
        caducar_reservas()
        with self.assertRaises(ReservaErro):
            marcar_recollida(self.centro, reserva.pk)

    def test_comando(self):
        self.reserva_vencida()
        saida = StringIO()
        call_command('caducar_reservas', stdout=saida)
        self.assertIn('Reservas caducadas: 1', saida.getvalue())
