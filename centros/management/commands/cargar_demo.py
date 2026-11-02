"""Carga datos ficticios de demostración: python manage.py cargar_demo [--borrar]

Pódese executar varias veces: primeiro borra os datos de demo anteriores (só eses).
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from catalogo.models import Exemplar
from centros.models import Centro
from reservas.models import Reserva
from reservas.servizos import cancelar_reserva, crear_reserva, marcar_recollida
from usuarios.models import Usuario

DOMINIO = '@demo.bambi.test'
CONTRASINAL = 'Demo-Bambi-2026'

CENTROS = [
    {
        'slug': 'biblioteca-os-castineiros', 'nome': 'Biblioteca Veciñal Os Castiñeiros', 'tipo': Centro.Tipo.BIBLIOTECA,
        'estado': Centro.Estado.ACTIVO, 'localizacion': 'Rúa da Proba, 12 · Lugo',
        'descricion': 'Biblioteca da asociación veciñal do barrio. Préstamos de luns a venres, de 17:00 a 20:30.',
        'cor_principal': '#2f5d50', 'cor_secundaria': '#eef4f1', 'tipografia': Centro.Tipografia.SERIF, 'dias_reserva': 3,
        'admin': 'castineiros',
        'libros': [
            ('Follas novas', 'Rosalía de Castro'), ('Cantares gallegos', 'Rosalía de Castro'),
            ('Memorias dun neno labrego', 'Xosé Neira Vilas'), ('O lapis do carpinteiro', 'Manuel Rivas'),
            ('Que me queres, amor?', 'Manuel Rivas'), ('Os eidos', 'Uxío Novoneyra'),
            ('Merlín e familia', 'Álvaro Cunqueiro'), ('A esmorga', 'Eduardo Blanco Amor'),
            ('Longa noite de pedra', 'Celso Emilio Ferreiro'), ('Arraianos', 'Xosé Luís Méndez Ferrín'),
            ('O único que queda é o amor', 'Agustín Fernández Paz'), ('Cartas de inverno', 'Agustín Fernández Paz'),
        ],
    },
    {
        'slug': 'libraria-a-pequena-andaina', 'nome': 'Libraría A Pequena Andaina', 'tipo': Centro.Tipo.LIBRARIA,
        'estado': Centro.Estado.ACTIVO, 'localizacion': 'Praza do Exemplo, 3 · Santiago de Compostela',
        'descricion': 'Libraría independente especializada en literatura infantil e xuvenil e narrativa contemporánea.',
        'cor_principal': '#7a2e3a', 'cor_secundaria': '#fbf3ea', 'tipografia': Centro.Tipografia.SANS, 'dias_reserva': 5,
        'admin': 'andaina',
        'libros': [
            ('Follas novas', 'Rosalía de Castro'), ('O principiño', 'Antoine de Saint-Exupéry'),
            ('Matilda', 'Roald Dahl'), ('Harry Potter e a pedra filosofal', 'J. K. Rowling'),
            ('Cen anos de soidade', 'Gabriel García Márquez'), ('A sombra do vento', 'Carlos Ruiz Zafón'),
            ('A illa do tesouro', 'Robert Louis Stevenson'), ('Fariña', 'Nacho Carretero'),
            ('Don Quixote da Mancha', 'Miguel de Cervantes'), ('1984', 'George Orwell'),
        ],
    },
    {
        'slug': 'biblioteca-escolar-alecrin', 'nome': 'Biblioteca Escolar Alecrín', 'tipo': Centro.Tipo.BIBLIOTECA,
        'estado': Centro.Estado.PENDENTE, 'localizacion': 'Camiño Ficticio, s/n · Ourense',
        'descricion': 'Biblioteca dun centro educativo pendente de revisión pola plataforma.',
        'admin': 'alecrin',
        'libros': [('Contos por palabras', 'Agustín Fernández Paz'), ('O principiño', 'Antoine de Saint-Exupéry')],
    },
]

LECTORES = [('lucia', 'Lucía'), ('martin', 'Martín'), ('noa', 'Noa')]


class Command(BaseCommand):
    help = 'Carga (ou borra con --borrar) os datos ficticios de demostración.'

    def add_arguments(self, parser):
        parser.add_argument('--borrar', action='store_true', help='Só borra os datos de demostración.')

    @transaction.atomic
    def handle(self, *args, **opcions):
        self.borrar()
        if opcions['borrar']:
            self.stdout.write(self.style.SUCCESS('Datos de demostración borrados.'))
            return
        self.cargar()

    def borrar(self):
        slugs = [c['slug'] for c in CENTROS]
        # As reservas protexen exemplares e lectores: bórranse primeiro
        Reserva.objects.filter(exemplar__centro__slug__in=slugs).delete()
        Reserva.objects.filter(lector__email__endswith=DOMINIO).delete()
        Exemplar.objects.filter(centro__slug__in=slugs).delete()
        Centro.objects.filter(slug__in=slugs).delete()
        Usuario.objects.filter(email__endswith=DOMINIO).delete()

    def cargar(self):
        Usuario.objects.create_superuser(f'plataforma{DOMINIO}', CONTRASINAL, nome_visible='Plataforma Bambi')

        centros = {}
        for datos in CENTROS:
            datos = dict(datos)
            libros, admin = datos.pop('libros'), datos.pop('admin')
            centro = Centro.objects.create(**datos)
            usuario = Usuario.objects.create_user(
                f'{admin}{DOMINIO}', CONTRASINAL, rol=Usuario.Rol.ADMIN_CENTRO, nome_visible=f'Admin {centro.nome}'
            )
            centro.administradores.add(usuario)
            for titulo, autoria in libros:
                Exemplar.objects.create(centro=centro, titulo=titulo, autoria=autoria)
            centros[centro.slug] = centro

        # Dous exemplares do mesmo libro na biblioteca, para ver que cada copia se reserva por separado
        Exemplar.objects.create(centro=centros['biblioteca-os-castineiros'], titulo='Follas novas', autoria='Rosalía de Castro')

        lectores = {
            nome: Usuario.objects.create_user(f'{nome}{DOMINIO}', CONTRASINAL, nome_visible=visible)
            for nome, visible in LECTORES
        }

        # Algunhas reservas para que os paneis e a área persoal non estean baleiros
        biblioteca, libraria = centros['biblioteca-os-castineiros'], centros['libraria-a-pequena-andaina']
        def libro(centro, titulo):
            return centro.exemplares.filter(titulo=titulo).first().pk

        crear_reserva(lectores['lucia'], libro(biblioteca, 'A esmorga'))
        crear_reserva(lectores['lucia'], libro(libraria, 'Matilda'))
        crear_reserva(lectores['martin'], libro(libraria, 'O principiño'))
        prestamo = crear_reserva(lectores['martin'], libro(biblioteca, 'Os eidos'))
        marcar_recollida(biblioteca, prestamo.pk)
        cancelada = crear_reserva(lectores['noa'], libro(biblioteca, 'Merlín e familia'))
        cancelar_reserva(lectores['noa'], cancelada.pk)

        self.stdout.write(self.style.SUCCESS('Datos de demostración cargados.'))
        self.stdout.write(f'Contrasinal de todas as contas: {CONTRASINAL}')
        self.stdout.write(f'  Superusuario:   plataforma{DOMINIO}')
        for datos in CENTROS:
            self.stdout.write(f"  Admin centro:   {datos['admin']}{DOMINIO}  ({datos['nome']})")
        for nome, _ in LECTORES:
            self.stdout.write(f'  Lector:         {nome}{DOMINIO}')
