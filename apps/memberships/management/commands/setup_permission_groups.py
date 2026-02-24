"""
Comando idempotente para criar/atualizar os grupos globais de permissão do JuridicFlow.

Grupos globais são os "átomos" do sistema. Apenas o superadmin cria grupos.
Org admins criam LocalRoles que combinam esses grupos.

Uso:
    python manage.py setup_permission_groups
    python manage.py setup_permission_groups --dry-run
"""
import logging

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from apps.memberships.models import PermissionGroupProfile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Cria/atualiza grupos globais de permissao (idempotente)."

    # Cada entrada: nome -> (slug, descricao, assignable_org_admin, assignable_tech_dir, internal_only, sort_order, [perms])
    GROUPS = {
        "CORE_VIEW_ALL": (
            "core-view-all", "Leitura de todos os modulos.", True, True, False, 10,
            [
                "customers.view_customer", "processes.view_process", "deadlines.view_deadline",
                "documents.view_document", "finance.view_feeagreement", "finance.view_invoice",
                "finance.view_payment", "finance.view_expense", "offices.view_office",
                "organizations.view_organization", "memberships.view_membership",
                "publications.view_publication", "portal.view_calendarentry",
                "portal.view_kanbanboard", "portal.view_kanbancolumn", "portal.view_kanbancard",
                "portal.view_task",
            ],
        ),
        "TEAM_MANAGE": (
            "team-manage", "Gerenciamento de equipe e funcoes locais.", True, True, False, 20,
            [
                "memberships.view_membership", "memberships.add_membership",
                "memberships.change_membership", "memberships.delete_membership",
                "memberships.view_localrole", "memberships.add_localrole",
                "memberships.change_localrole", "memberships.delete_localrole",
            ],
        ),
        "OFFICES_MANAGE": (
            "offices-manage", "Criacao e edicao de escritorios.", True, True, False, 30,
            ["offices.view_office", "offices.add_office", "offices.change_office"],
        ),
        "ORG_SETTINGS_MANAGE": (
            "org-settings-manage", "Configuracoes da organizacao.", True, True, False, 40,
            ["organizations.view_organization", "organizations.change_organization"],
        ),
        "PROCESS_VIEW": (
            "process-view", "Visualizacao de processos e prazos.", True, True, False, 50,
            ["processes.view_process", "deadlines.view_deadline"],
        ),
        "PROCESS_EDIT": (
            "process-edit", "Criacao e edicao de processos e prazos.", True, True, False, 51,
            [
                "processes.view_process", "processes.add_process", "processes.change_process",
                "deadlines.view_deadline", "deadlines.add_deadline", "deadlines.change_deadline",
            ],
        ),
        "PROCESS_FULL": (
            "process-full", "Acesso completo a processos e prazos (incl. exclusao).", True, True, False, 52,
            [
                "processes.view_process", "processes.add_process", "processes.change_process", "processes.delete_process",
                "deadlines.view_deadline", "deadlines.add_deadline", "deadlines.change_deadline", "deadlines.delete_deadline",
            ],
        ),
        "FINANCE_VIEW": (
            "finance-view", "Visualizacao do financeiro.", True, True, False, 60,
            ["finance.view_feeagreement", "finance.view_invoice", "finance.view_payment", "finance.view_expense"],
        ),
        "FINANCE_EDIT": (
            "finance-edit", "Criacao e edicao de contratos, faturas e despesas.", True, True, False, 61,
            [
                "finance.view_feeagreement", "finance.add_feeagreement", "finance.change_feeagreement",
                "finance.view_invoice", "finance.add_invoice", "finance.change_invoice",
                "finance.view_payment", "finance.add_payment", "finance.change_payment",
                "finance.view_expense", "finance.add_expense", "finance.change_expense",
            ],
        ),
        "FINANCE_FULL": (
            "finance-full", "Acesso completo ao financeiro (incl. exclusao).", True, True, False, 62,
            [
                "finance.view_feeagreement", "finance.add_feeagreement", "finance.change_feeagreement", "finance.delete_feeagreement",
                "finance.view_invoice", "finance.add_invoice", "finance.change_invoice", "finance.delete_invoice",
                "finance.view_payment", "finance.add_payment", "finance.change_payment", "finance.delete_payment",
                "finance.view_expense", "finance.add_expense", "finance.change_expense", "finance.delete_expense",
            ],
        ),
        "CUSTOMERS_VIEW": (
            "customers-view", "Visualizacao de contatos.", True, True, False, 70,
            ["customers.view_customer"],
        ),
        "CUSTOMERS_FULL": (
            "customers-full", "Acesso completo a contatos (incl. exclusao).", True, True, False, 71,
            ["customers.view_customer", "customers.add_customer", "customers.change_customer", "customers.delete_customer"],
        ),
        "DOCUMENTS_VIEW": (
            "documents-view", "Visualizacao e download de documentos.", True, True, False, 80,
            ["documents.view_document"],
        ),
        "DOCUMENTS_EDIT": (
            "documents-edit", "Upload e edicao de documentos.", True, True, False, 81,
            ["documents.view_document", "documents.add_document", "documents.change_document"],
        ),
        "DOCUMENTS_FULL": (
            "documents-full", "Acesso completo a documentos (incl. exclusao).", True, True, False, 82,
            ["documents.view_document", "documents.add_document", "documents.change_document", "documents.delete_document"],
        ),
        "TASKS_VIEW": (
            "tasks-view", "Visualizacao de Kanban e tarefas.", True, True, False, 90,
            ["portal.view_kanbanboard", "portal.view_kanbancolumn", "portal.view_kanbancard", "portal.view_task"],
        ),
        "TASKS_EDIT": (
            "tasks-edit", "Criacao e edicao de cards e tarefas.", True, True, False, 91,
            [
                "portal.view_kanbanboard", "portal.view_kanbancolumn",
                "portal.view_kanbancard", "portal.add_kanbancard", "portal.change_kanbancard",
                "portal.view_task", "portal.add_task", "portal.change_task",
            ],
        ),
        "TASKS_FULL": (
            "tasks-full", "Acesso completo ao Kanban (incl. exclusao e colunas).", True, True, False, 92,
            [
                "portal.view_kanbanboard", "portal.add_kanbanboard", "portal.change_kanbanboard", "portal.delete_kanbanboard",
                "portal.view_kanbancolumn", "portal.add_kanbancolumn", "portal.change_kanbancolumn", "portal.delete_kanbancolumn",
                "portal.view_kanbancard", "portal.add_kanbancard", "portal.change_kanbancard", "portal.delete_kanbancard",
                "portal.view_task", "portal.add_task", "portal.change_task", "portal.delete_task",
            ],
        ),
        "PUBLICATIONS_VIEW": (
            "publications-view", "Visualizacao de publicacoes.", True, True, False, 100,
            ["publications.view_publication"],
        ),
        "PUBLICATIONS_FULL": (
            "publications-full", "Gerenciamento completo de publicacoes.", True, True, False, 101,
            ["publications.view_publication", "publications.add_publication", "publications.change_publication", "publications.delete_publication"],
        ),
        "CALENDAR_VIEW": (
            "calendar-view", "Visualizacao da agenda.", True, True, False, 110,
            ["portal.view_calendarentry"],
        ),
        "CALENDAR_FULL": (
            "calendar-full", "Gerenciamento completo da agenda.", True, True, False, 111,
            ["portal.view_calendarentry", "portal.add_calendarentry", "portal.change_calendarentry", "portal.delete_calendarentry"],
        ),
        # Supergrupo composto -- interno, nao atribuivel diretamente por org admins
        "ORG_ADMIN_FULL": (
            "org-admin-full",
            "Admin completo da organizacao (todos os modulos + equipe + configuracoes).",
            False, False, True, 200,
            [
                "customers.view_customer", "customers.add_customer", "customers.change_customer", "customers.delete_customer",
                "processes.view_process", "processes.add_process", "processes.change_process", "processes.delete_process",
                "deadlines.view_deadline", "deadlines.add_deadline", "deadlines.change_deadline", "deadlines.delete_deadline",
                "documents.view_document", "documents.add_document", "documents.change_document", "documents.delete_document",
                "finance.view_feeagreement", "finance.add_feeagreement", "finance.change_feeagreement", "finance.delete_feeagreement",
                "finance.view_invoice", "finance.add_invoice", "finance.change_invoice", "finance.delete_invoice",
                "finance.view_payment", "finance.add_payment", "finance.change_payment", "finance.delete_payment",
                "finance.view_expense", "finance.add_expense", "finance.change_expense", "finance.delete_expense",
                "publications.view_publication", "publications.add_publication", "publications.change_publication", "publications.delete_publication",
                "memberships.view_membership", "memberships.add_membership", "memberships.change_membership", "memberships.delete_membership",
                "memberships.view_localrole", "memberships.add_localrole", "memberships.change_localrole", "memberships.delete_localrole",
                "offices.view_office", "offices.add_office", "offices.change_office",
                "organizations.view_organization", "organizations.change_organization",
                "portal.view_kanbanboard", "portal.add_kanbanboard", "portal.change_kanbanboard", "portal.delete_kanbanboard",
                "portal.view_kanbancolumn", "portal.add_kanbancolumn", "portal.change_kanbancolumn", "portal.delete_kanbancolumn",
                "portal.view_kanbancard", "portal.add_kanbancard", "portal.change_kanbancard", "portal.delete_kanbancard",
                "portal.view_task", "portal.add_task", "portal.change_task", "portal.delete_task",
                "portal.view_calendarentry", "portal.add_calendarentry", "portal.change_calendarentry", "portal.delete_calendarentry",
            ],
        ),
    }

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Simula sem salvar.")

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN -- nenhuma alteracao sera salva.\n"))

        self.stdout.write("Configurando grupos globais de permissao do JuridicFlow...\n")
        total_ok = 0
        total_warn = 0

        for group_name, config in self.GROUPS.items():
            slug, desc, assignable_org, assignable_tech, internal, sort_order, perm_strings = config

            if not dry_run:
                group, created = Group.objects.get_or_create(name=group_name)
            else:
                created = not Group.objects.filter(name=group_name).exists()

            perms, missing = [], []
            for perm_str in perm_strings:
                app_label, codename = perm_str.split(".", 1)
                try:
                    perms.append(Permission.objects.get(content_type__app_label=app_label, codename=codename))
                except Permission.DoesNotExist:
                    missing.append(perm_str)
                    logger.warning("Permissao nao encontrada: %s", perm_str)

            if not dry_run:
                group.permissions.set(perms)
                PermissionGroupProfile.objects.update_or_create(
                    group=group,
                    defaults=dict(
                        slug=slug, description=desc,
                        is_assignable_by_org_admin=assignable_org,
                        is_assignable_by_tech_director=assignable_tech,
                        is_internal_only=internal,
                        sort_order=sort_order,
                    ),
                )

            action = "criado" if created else "atualizado"
            self.stdout.write(self.style.SUCCESS(f"  ok  {group_name} ({action}, {len(perms)} perms)"))
            for mp in missing:
                self.stdout.write(self.style.WARNING(f"  WARN  permissao nao encontrada: {mp}"))
                total_warn += 1
            total_ok += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Concluido: {total_ok} grupos, {total_warn} avisos."))
        if not dry_run:
            self.stdout.write("Acesse /admin -> Auth -> Grupos para inspecionar.")
