"""
Management command: atualiza status de prazos e faturas vencidos.

Uso manual:
    python manage.py update_overdue

Uso via cron (rodar diariamente às 6h):
    0 6 * * * cd /path/to/project && python manage.py update_overdue
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Marca prazos e faturas vencidos como 'overdue'"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra o que seria atualizado sem alterar o banco",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        today = timezone.now().date()

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — nada será salvo\n"))

        # ---------- DEADLINES ----------
        from apps.deadlines.models import Deadline

        overdue_deadlines = Deadline.objects.filter(
            status="pending",
            due_date__lt=today,
        )
        count_deadlines = overdue_deadlines.count()

        if dry_run:
            self.stdout.write(f"Prazos vencidos a marcar: {count_deadlines}")
            for d in overdue_deadlines[:10]:
                self.stdout.write(f"  [{d.id}] {d.title} — venceu em {d.due_date}")
            if count_deadlines > 10:
                self.stdout.write(f"  ... e mais {count_deadlines - 10}")
        else:
            updated = overdue_deadlines.update(status="overdue")
            self.stdout.write(f"Prazos marcados como overdue: {updated}")

        # ---------- INVOICES ----------
        from apps.finance.models import Invoice

        overdue_invoices = Invoice.objects.filter(
            status__in=["issued", "sent"],
            due_date__lt=today,
        )
        count_invoices = overdue_invoices.count()

        if dry_run:
            self.stdout.write(f"Faturas vencidas a marcar: {count_invoices}")
            for inv in overdue_invoices[:10]:
                self.stdout.write(
                    f"  [{inv.id}] R${inv.amount} — venceu em {inv.due_date}"
                )
            if count_invoices > 10:
                self.stdout.write(f"  ... e mais {count_invoices - 10}")
        else:
            updated = overdue_invoices.update(status="overdue")
            self.stdout.write(f"Faturas marcadas como overdue: {updated}")

        # ---------- RESUMO ----------
        self.stdout.write("")
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(
                f"Concluído em {timezone.now():%Y-%m-%d %H:%M:%S} — "
                f"{count_deadlines} prazos, {count_invoices} faturas processados."
            ))