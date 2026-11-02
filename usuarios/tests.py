from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from bambi.probas import CONTRASINAL, crear_admin, crear_lector, crear_superusuario

from .models import Usuario


class ModeloUsuarioTests(TestCase):
    def test_lector_por_defecto_e_correo_en_minusculas(self):
        usuario = Usuario.objects.create_user('Ana@Proba.TEST', CONTRASINAL)
        self.assertEqual(usuario.email, 'ana@proba.test')
        self.assertTrue(usuario.es_lector)

    def test_superusuario_ten_rol_de_plataforma(self):
        usuario = crear_superusuario()
        self.assertTrue(usuario.is_superuser)
        self.assertTrue(usuario.es_superusuario)


class RexistroTests(TestCase):
    url = reverse('usuarios:rexistro')

    def datos(self, **cambios):
        return {'email': 'novo@proba.test', 'nome_visible': 'Ana', 'password1': CONTRASINAL, 'password2': CONTRASINAL, **cambios}

    def test_rexistro_crea_lector_e_inicia_sesion(self):
        resposta = self.client.post(self.url, self.datos(rol='superusuario'))
        usuario = Usuario.objects.get(email='novo@proba.test')
        self.assertEqual(usuario.rol, Usuario.Rol.LECTOR)  # o rol do POST ignórase
        self.assertRedirects(resposta, reverse('reservas:area_persoal'))
        self.assertEqual(int(self.client.session['_auth_user_id']), usuario.pk)

    def test_correo_duplicado_con_outras_maiusculas(self):
        crear_lector('novo@proba.test')
        resposta = self.client.post(self.url, self.datos(email='Novo@Proba.test'))
        self.assertContains(resposta, 'Xa existe unha conta')

    def test_contrasinais_distintos_marcan_o_campo(self):
        resposta = self.client.post(self.url, self.datos(password2='outro'))
        self.assertContains(resposta, 'is-invalid')
        self.assertFalse(Usuario.objects.exists())

    def test_next_externo_ignorase(self):
        resposta = self.client.post(self.url, self.datos(next='https://malicioso.example/'))
        self.assertRedirects(resposta, reverse('reservas:area_persoal'))


class LoginTests(TestCase):
    def test_login_con_maiusculas(self):
        crear_lector('ana@proba.test')
        resposta = self.client.post(reverse('usuarios:entrar'), {'username': 'ANA@proba.test', 'password': CONTRASINAL})
        self.assertRedirects(resposta, reverse('usuarios:inicio'), fetch_redirect_response=False)

    def test_destino_segundo_o_rol(self):
        casos = [
            (crear_lector(), reverse('reservas:area_persoal')),
            (crear_admin(), reverse('panel:inicio')),
            (crear_superusuario(), reverse('plataforma:inicio')),
        ]
        for usuario, destino in casos:
            with self.subTest(rol=usuario.rol):
                self.client.force_login(usuario)
                self.assertRedirects(self.client.get(reverse('usuarios:inicio')), destino, fetch_redirect_response=False)

    def test_cambiar_idioma_con_sesion_gardao_na_conta(self):
        lector = crear_lector()
        self.client.force_login(lector)
        self.client.post(reverse('set_language'), {'language': 'en', 'next': '/'})
        lector.refresh_from_db()
        self.assertEqual(lector.idioma, 'en')

    def test_ao_entrar_aplicase_o_idioma_da_conta(self):
        crear_lector('ana@proba.test', idioma='es')
        resposta = self.client.post(reverse('usuarios:entrar'), {'username': 'ana@proba.test', 'password': CONTRASINAL})
        self.assertEqual(resposta.cookies[settings.LANGUAGE_COOKIE_NAME].value, 'es')
        self.assertContains(self.client.get('/'), 'lang="es"')

    def test_idioma_desconecido_non_se_garda(self):
        lector = crear_lector()
        self.client.force_login(lector)
        self.client.post(reverse('set_language'), {'language': 'xx', 'next': '/'})
        lector.refresh_from_db()
        self.assertEqual(lector.idioma, 'gl')

    def test_pechar_sesion_so_por_post(self):
        self.client.force_login(crear_lector())
        self.assertEqual(self.client.get(reverse('usuarios:sair')).status_code, 405)
        self.client.post(reverse('usuarios:sair'))
        self.assertNotIn('_auth_user_id', self.client.session)
