from django.core.management.base import BaseCommand

from reservas.servizos import caducar_reservas


class Command(BaseCommand):
    help = (
        'Pecha as reservas activas cuxo prazo de recollida xa pasou, libera os exemplares '
        'e aplica a penalización de fiabilidade. Pensado para executarse unha vez ao día.'
    )

    def handle(self, *args, **opcions):
        total = caducar_reservas()
        self.stdout.write(self.style.SUCCESS(f'Reservas caducadas: {total}'))
