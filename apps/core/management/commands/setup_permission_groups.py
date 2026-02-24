"""
DEPRECATED: Este comando foi movido para apps/memberships/management/commands/setup_permission_groups.py.
Este arquivo existe apenas para compatibilidade e delega ao comando correto.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "DEPRECATED - use: python manage.py setup_permission_groups (no app memberships)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            "AVISO: Este comando esta em apps/core e sera removido. "
            "Use: python manage.py setup_permission_groups"
        ))
        call_command("setup_permission_groups", *args, **options)
