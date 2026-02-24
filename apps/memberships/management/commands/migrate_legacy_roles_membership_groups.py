"""
Migra roles legados (Membership.role) para Membership.groups usando os grupos globais.

Útil quando você tem um banco existente e quer mapear os labels antigos
para os novos grupos de permissão sem perder dados.

Uso:
    python manage.py migrate_legacy_roles_membership_groups
    python manage.py migrate_legacy_roles_membership_groups --dry-run

Mapeamento padrão de roles antigos -> nomes de grupos globais:
  org_admin   -> ORG_ADMIN_FULL
  office_admin -> PROCESS_FULL + FINANCE_FULL + CUSTOMERS_FULL + DOCUMENTS_FULL + TASKS_FULL + TEAM_MANAGE + OFFICES_MANAGE
  lawyer      -> PROCESS_FULL + CUSTOMERS_FULL + DOCUMENTS_EDIT + CALENDAR_FULL + PUBLICATIONS_VIEW
  staff       -> CORE_VIEW_ALL
  finance     -> FINANCE_FULL + CUSTOMERS_VIEW + PROCESS_VIEW

Ajuste o ROLE_TO_GROUPS abaixo conforme sua necessidade.
"""
import logging

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from apps.memberships.models import Membership

logger = logging.getLogger(__name__)

ROLE_TO_GROUPS = {
    "org_admin": ["ORG_ADMIN_FULL"],
    "office_admin": [
        "PROCESS_FULL", "FINANCE_FULL", "CUSTOMERS_FULL",
        "DOCUMENTS_FULL", "TASKS_FULL", "TEAM_MANAGE", "OFFICES_MANAGE",
        "CALENDAR_FULL", "PUBLICATIONS_FULL", "ORG_SETTINGS_MANAGE",
    ],
    "lawyer": [
        "PROCESS_FULL", "CUSTOMERS_FULL", "DOCUMENTS_EDIT",
        "CALENDAR_FULL", "PUBLICATIONS_VIEW", "FINANCE_VIEW",
        "TASKS_EDIT", "DEADLINES_FULL",
    ],
    "staff": ["CORE_VIEW_ALL"],
    "finance": ["FINANCE_FULL", "CUSTOMERS_VIEW", "PROCESS_VIEW"],
    # roles legados antigos (portal/permissions.py)
    "admin": ["ORG_ADMIN_FULL"],
    "manager": [
        "PROCESS_FULL", "FINANCE_FULL", "CUSTOMERS_FULL",
        "DOCUMENTS_FULL", "TASKS_FULL",
    ],
    "assistant": [
        "PROCESS_EDIT", "CUSTOMERS_FULL", "DOCUMENTS_EDIT",
        "TASKS_EDIT", "CALENDAR_FULL",
    ],
    "intern": ["CORE_VIEW_ALL", "TASKS_EDIT"],
}


class Command(BaseCommand):
    help = "Migra Membership.role -> Membership.groups usando os grupos globais."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN -- sem alteracoes.\n"))

        self.stdout.write("Iniciando migracao de roles legados para membership groups...\n")

        groups_cache = {}
        missing_groups = set()
        for group_name in set(g for gs in ROLE_TO_GROUPS.values() for g in gs):
            try:
                groups_cache[group_name] = Group.objects.get(name=group_name)
            except Group.DoesNotExist:
                missing_groups.add(group_name)
                logger.warning("Grupo nao encontrado (rode setup_permission_groups primeiro): %s", group_name)

        if missing_groups:
            self.stdout.write(self.style.WARNING(
                f"\nATENCAO: {len(missing_groups)} grupos nao encontrados. "
                "Execute 'python manage.py setup_permission_groups' antes.\n"
                f"Grupos faltando: {', '.join(sorted(missing_groups))}\n"
            ))

        memberships = Membership.objects.select_related("user", "organization", "office")
        total = memberships.count()
        updated = 0
        skipped = 0

        for m in memberships:
            role = m.role
            if not role:
                skipped += 1
                continue

            group_names = ROLE_TO_GROUPS.get(role)
            if not group_names:
                self.stdout.write(self.style.WARNING(f"  SKIP  role nao mapeado: '{role}' (membership {m.pk})"))
                skipped += 1
                continue

            groups = [groups_cache[gn] for gn in group_names if gn in groups_cache]
            if not dry_run:
                m.groups.set(groups)
            updated += 1
            self.stdout.write(
                f"  ok  {m.user.email} @ {m.organization.name} / "
                f"{'org' if not m.office else m.office.name} "
                f"[{role}] -> {len(groups)} grupos"
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Migracao concluida: {updated}/{total} memberships atualizados, {skipped} ignorados."
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: nenhuma alteracao foi salva."))
