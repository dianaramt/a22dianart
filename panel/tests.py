from django.test import TestCase
from django.urls import reverse

from bambi.probas import CONTRASINAL, crear_admin, crear_centro, crear_exemplar, crear_lector, crear_superusuario
from catalogo.models import Exemplar
from centros.models import Centro
from reservas.models import Reserva
from reservas.servizos import crear_reserva
from usuarios.models import Usuario


class PermisosPanelTests(TestCase):
    def setUp(self):
        self.biblioteca = crear_centro('biblioteca')
        self.libraria = crear_centro('libraria', tipo=Centro.Tipo.LIBRARIA)
        self.admin = crear_admin(self.biblioteca)

    def test_un_so_centro_vai_directo_ao_seu_panel(self):
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.get(reverse('panel:inicio')), reverse('panel:resumo', args=['biblioteca']))

    def test_non_ve_paneis_alleos(self):
        self.client.force_login(self.admin)
        for nome in ['resumo', 'catalogo', 'reservas', 'escaparate']:
            with self.subTest(vista=nome):
                self.assertEqual(self.client.get(reverse(f'panel:{nome}', args=['libraria'])).status_code, 404)

    def test_lector_e_centro_desactivado_dan_404(self):
        self.client.force_login(crear_lector())
        self.assertEqual(self.client.get(reverse('panel:resumo', args=['biblioteca'])).status_code, 404)
        self.biblioteca.estado = Centro.Estado.DESACTIVADO
        self.biblioteca.save()
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('panel:resumo', args=['biblioteca'])).status_code, 404)


class CatalogoPanelTests(TestCase):
    def setUp(self):
        self.centro = crear_centro()
        self.client.force_login(crear_admin(self.centro))
        self.url_novo = reverse('panel:exemplar_novo', args=[self.centro.slug])

    def test_engadir_usa_sempre_o_centro_do_panel(self):
        outro = crear_centro('outro')
        self.client.post(self.url_novo, {'titulo': 'Novo', 'autoria': 'A', 'estado': 'disponible', 'centro': outro.pk})
        self.assertEqual(Exemplar.objects.get(titulo='Novo').centro, self.centro)

    def test_valida_isbn(self):
        resposta = self.client.post(self.url_novo, {'titulo': 'X', 'autoria': 'A', 'isbn': '123', 'estado': 'disponible'})
        self.assertContains(resposta, 'O ISBN debe ter')

    def test_non_se_pode_por_reservado_a_man(self):
        self.client.post(self.url_novo, {'titulo': 'Trampa', 'autoria': 'A', 'estado': 'reservado'})
        self.assertFalse(Exemplar.objects.filter(titulo='Trampa').exists())

    def test_estado_bloqueado_con_reserva_activa(self):
        exemplar = crear_exemplar(self.centro)
        crear_reserva(crear_lector(), exemplar.pk)
        url = reverse('panel:exemplar_editar', args=[self.centro.slug, exemplar.pk])
        self.client.post(url, {'titulo': 'Título novo', 'autoria': 'A', 'estado': 'retirado'})
        exemplar.refresh_from_db()
        self.assertEqual(exemplar.titulo, 'Título novo')
        self.assertEqual(exemplar.estado, Exemplar.Estado.RESERVADO)

    def test_paxinacion_manten_filtros(self):
        for i in range(30):
            crear_exemplar(self.centro, titulo=f'Retirado {i}', estado='retirado')
        resposta = self.client.get(reverse('panel:catalogo', args=[self.centro.slug]), {'estado': 'retirado'})
        self.assertContains(resposta, 'estado=retirado&amp;paxina=2')


class ReservasPanelTests(TestCase):
    def accion(self, centro, reserva, accion):
        return self.client.post(reverse('panel:accion_reserva', args=[centro.slug, reserva.pk, accion]))

    def preparar(self, tipo):
        centro = crear_centro(f'centro-{tipo}', tipo=tipo)
        self.client.force_login(crear_admin(centro, email=f'admin-{tipo}@proba.test'))
        exemplar = crear_exemplar(centro)
        reserva = crear_reserva(crear_lector(f'lector-{tipo}@proba.test'), exemplar.pk)
        return centro, exemplar, reserva

    def estados(self, exemplar, reserva):
        exemplar.refresh_from_db()
        reserva.refresh_from_db()
        return reserva.estado, exemplar.estado

    def test_biblioteca_recollida_e_devolucion(self):
        centro, exemplar, reserva = self.preparar(Centro.Tipo.BIBLIOTECA)
        self.accion(centro, reserva, 'recollida')
        self.assertEqual(self.estados(exemplar, reserva), ('recollida', 'prestado'))
        self.accion(centro, reserva, 'devolta')
        self.assertEqual(self.estados(exemplar, reserva), ('devolta', 'disponible'))

    def test_libraria_recollida_retira_o_exemplar(self):
        centro, exemplar, reserva = self.preparar(Centro.Tipo.LIBRARIA)
        self.accion(centro, reserva, 'recollida')
        self.assertEqual(self.estados(exemplar, reserva), ('recollida', 'retirado'))
        self.accion(centro, reserva, 'devolta')  # as librarías non teñen devolucións
        self.assertEqual(self.estados(exemplar, reserva), ('recollida', 'retirado'))

    def test_non_recollida_libera_o_exemplar(self):
        centro, exemplar, reserva = self.preparar(Centro.Tipo.BIBLIOTECA)
        self.accion(centro, reserva, 'non_recollida')
        self.assertEqual(self.estados(exemplar, reserva), ('non_recollida', 'disponible'))

    def test_non_se_poden_atender_reservas_doutro_centro(self):
        _, exemplar, reserva = self.preparar(Centro.Tipo.BIBLIOTECA)
        outro, _, _ = self.preparar(Centro.Tipo.LIBRARIA)  # agora a sesión é do admin da libraría
        self.accion(outro, reserva, 'recollida')
        self.assertEqual(self.estados(exemplar, reserva), ('activa', 'reservado'))

    def test_accion_desconecida_e_get(self):
        centro, _, reserva = self.preparar(Centro.Tipo.BIBLIOTECA)
        self.assertEqual(self.accion(centro, reserva, 'borrar').status_code, 404)
        url = reverse('panel:accion_reserva', args=[centro.slug, reserva.pk, 'recollida'])
        self.assertEqual(self.client.get(url).status_code, 405)


class EscaparatePanelTests(TestCase):
    def test_edita_identidade_pero_non_o_estado(self):
        centro = crear_centro()
        self.client.force_login(crear_admin(centro))
        url = reverse('panel:escaparate', args=[centro.slug])
        datos = {'nome': 'Novo nome', 'descricion': '', 'localizacion': 'Lugo', 'cor_principal': '#123456',
                 'cor_secundaria': '#fafafa', 'tipografia': 'serif', 'dias_reserva': 7, 'estado': 'desactivado'}
        self.client.post(url, datos)
        centro.refresh_from_db()
        self.assertEqual((centro.nome, centro.cor_principal, centro.dias_reserva), ('Novo nome', '#123456', 7))
        self.assertEqual(centro.estado, Centro.Estado.ACTIVO)

        resposta = self.client.post(url, {**datos, 'cor_principal': 'red', 'dias_reserva': 99})
        self.assertContains(resposta, 'formato #rrggbb')
        self.assertContains(resposta, 'entre 1 e 30')


class PlataformaTests(TestCase):
    def setUp(self):
        self.client.force_login(crear_superusuario())

    def alta(self, **cambios):
        datos = {
            'centro-nome': 'Biblioteca de Proba', 'centro-tipo': 'biblioteca', 'centro-slug': '',
            'centro-localizacion': 'Lugo', 'centro-descricion': '',
            'admin-email': 'Admin@Novo.test', 'admin-nome_visible': 'Admin',
            'admin-contrasinal1': CONTRASINAL, 'admin-contrasinal2': CONTRASINAL, **cambios,
        }
        return self.client.post(reverse('plataforma:centro_novo'), datos)

    def test_so_o_superusuario_entra(self):
        for usuario in [crear_lector(), crear_admin()]:
            with self.subTest(rol=usuario.rol):
                self.client.force_login(usuario)
                self.assertEqual(self.client.get(reverse('plataforma:inicio')).status_code, 404)

    def test_alta_crea_centro_pendente_e_admin_novo(self):
        self.alta()
        centro = Centro.objects.get(slug='biblioteca-de-proba')
        admin = Usuario.objects.get(email='admin@novo.test')
        self.assertEqual(centro.estado, Centro.Estado.PENDENTE)
        self.assertEqual(admin.rol, Usuario.Rol.ADMIN_CENTRO)
        self.assertTrue(admin.check_password(CONTRASINAL))
        self.assertIn(admin, centro.administradores.all())

    def test_slug_repetido_recibe_sufixo(self):
        crear_centro('biblioteca-de-proba')
        self.alta()
        self.assertTrue(Centro.objects.filter(slug='biblioteca-de-proba-2').exists())

    def test_admin_existente_non_necesita_contrasinal(self):
        crear_admin(email='admin@novo.test')
        self.alta(**{'admin-contrasinal1': '', 'admin-contrasinal2': ''})
        self.assertEqual(Centro.objects.get(slug='biblioteca-de-proba').administradores.count(), 1)

    def test_non_converte_lectores_en_admins(self):
        crear_lector('admin@novo.test')
        resposta = self.alta()
        self.assertContains(resposta, 'non é de administrador')
        self.assertFalse(Centro.objects.exists())  # nin centro nin admin: todo ou nada

    def test_conta_nova_exixe_contrasinal_valido(self):
        resposta = self.alta(**{'admin-contrasinal1': '123', 'admin-contrasinal2': '123'})
        self.assertContains(resposta, 'is-invalid')
        self.assertFalse(Centro.objects.exists())

    def test_activar_exixe_administrador(self):
        centro = crear_centro(estado=Centro.Estado.PENDENTE)
        url = reverse('plataforma:centro_estado', args=[centro.pk, 'activo'])
        self.client.post(url)
        centro.refresh_from_db()
        self.assertEqual(centro.estado, Centro.Estado.PENDENTE)
        crear_admin(centro)
        self.client.post(url)
        centro.refresh_from_db()
        self.assertEqual(centro.estado, Centro.Estado.ACTIVO)

    def test_non_quita_o_ultimo_admin_dun_centro_activo(self):
        centro = crear_centro()
        admin = crear_admin(centro)
        self.client.post(reverse('plataforma:quitar_admin', args=[centro.pk, admin.pk]))
        self.assertEqual(centro.administradores.count(), 1)

    def test_pestanas_por_estado(self):
        crear_centro('a', nome='Centro Activo')
        crear_centro('p', nome='Centro Pendente', estado=Centro.Estado.PENDENTE)
        resposta = self.client.get(reverse('plataforma:inicio'), {'estado': 'activo'})
        self.assertContains(resposta, 'Centro Activo')
        self.assertNotContains(resposta, 'Centro Pendente')
