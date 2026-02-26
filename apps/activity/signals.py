"""
Django signals para registrar automaticamente eventos de atividade.

Conecta post_save / post_delete dos modelos principais ao log_event.
Instalar: adicionar 'apps.activity' em INSTALLED_APPS e chamar
ActivityConfig.ready() → signals.setup().
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import log_event


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _actor_from_instance(instance):
    """Tenta extrair o usuário que causou a mudança (se anotado)."""
    return getattr(instance, "_current_user", None)


def _request_from_instance(instance):
    return getattr(instance, "_current_request", None)


def _safe_log(**kwargs):
    try:
        log_event(**kwargs)
    except Exception:
        pass  # Nunca quebrar a request por causa do log


# ─────────────────────────────────────────────────────────────────────────────
# Processos
# ─────────────────────────────────────────────────────────────────────────────

def _connect_process():
    try:
        from apps.processes.models import Process

        @receiver(post_save, sender=Process, weak=False)
        def on_process_save(sender, instance, created, **kwargs):
            actor = _actor_from_instance(instance)
            action = "created" if created else "updated"
            label = getattr(instance, "number", "") or f"#{instance.pk}"
            actor_name = actor.get_full_name() if actor else "Sistema"
            summary = f"{actor_name} {'criou' if created else 'atualizou'} Processo {label}"
            _safe_log(
                module="processes", action=action, summary=summary,
                actor=actor,
                organization=getattr(instance, "organization", None),
                office=getattr(instance, "office", None),
                entity_type="Process", entity_id=str(instance.pk),
                entity_label=label,
                request=_request_from_instance(instance),
            )

        @receiver(post_delete, sender=Process, weak=False)
        def on_process_delete(sender, instance, **kwargs):
            actor = _actor_from_instance(instance)
            label = getattr(instance, "number", "") or f"#{instance.pk}"
            actor_name = actor.get_full_name() if actor else "Sistema"
            _safe_log(
                module="processes", action="deleted",
                summary=f"{actor_name} excluiu Processo {label}",
                actor=actor,
                organization=getattr(instance, "organization", None),
                office=getattr(instance, "office", None),
                entity_type="Process", entity_id=str(instance.pk),
                entity_label=label,
            )
    except ImportError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Prazos
# ─────────────────────────────────────────────────────────────────────────────

def _connect_deadline():
    try:
        from apps.deadlines.models import Deadline

        @receiver(post_save, sender=Deadline, weak=False)
        def on_deadline_save(sender, instance, created, **kwargs):
            actor = _actor_from_instance(instance)
            action = "created" if created else "updated"
            label = getattr(instance, "title", "") or f"#{instance.pk}"
            actor_name = actor.get_full_name() if actor else "Sistema"
            _safe_log(
                module="deadlines", action=action,
                summary=f"{actor_name} {'criou' if created else 'atualizou'} Prazo '{label}'",
                actor=actor,
                organization=getattr(instance, "organization", None),
                office=getattr(instance, "office", None),
                entity_type="Deadline", entity_id=str(instance.pk),
                entity_label=label,
                request=_request_from_instance(instance),
            )
    except ImportError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Clientes
# ─────────────────────────────────────────────────────────────────────────────

def _connect_customer():
    try:
        from apps.customers.models import Customer

        @receiver(post_save, sender=Customer, weak=False)
        def on_customer_save(sender, instance, created, **kwargs):
            actor = _actor_from_instance(instance)
            action = "created" if created else "updated"
            label = getattr(instance, "name", "") or f"#{instance.pk}"
            actor_name = actor.get_full_name() if actor else "Sistema"
            _safe_log(
                module="customers", action=action,
                summary=f"{actor_name} {'criou' if created else 'atualizou'} Contato '{label}'",
                actor=actor,
                organization=getattr(instance, "organization", None),
                office=getattr(instance, "office", None),
                entity_type="Customer", entity_id=str(instance.pk),
                entity_label=label,
                request=_request_from_instance(instance),
            )
    except ImportError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Documentos
# ─────────────────────────────────────────────────────────────────────────────

def _connect_document():
    try:
        from apps.documents.models import Document

        @receiver(post_save, sender=Document, weak=False)
        def on_document_save(sender, instance, created, **kwargs):
            actor = _actor_from_instance(instance)
            action = "uploaded" if created else "updated"
            label = getattr(instance, "title", "") or f"#{instance.pk}"
            actor_name = actor.get_full_name() if actor else "Sistema"
            _safe_log(
                module="documents", action=action,
                summary=f"{actor_name} fez upload de '{label}'" if created else f"{actor_name} atualizou '{label}'",
                actor=actor,
                organization=getattr(instance, "organization", None),
                office=getattr(instance, "office", None),
                entity_type="Document", entity_id=str(instance.pk),
                entity_label=label,
                request=_request_from_instance(instance),
            )
    except ImportError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Tasks
# ─────────────────────────────────────────────────────────────────────────────

def _connect_task():
    try:
        from apps.portal.models import Task

        @receiver(post_save, sender=Task, weak=False)
        def on_task_save(sender, instance, created, **kwargs):
            actor = _actor_from_instance(instance)
            action = "created" if created else "updated"
            label = getattr(instance, "title", "") or f"#{instance.pk}"
            actor_name = actor.get_full_name() if actor else "Sistema"
            _safe_log(
                module="tasks", action=action,
                summary=f"{actor_name} {'criou' if created else 'atualizou'} Tarefa '{label}'",
                actor=actor,
                organization=getattr(instance, "organization", None),
                office=getattr(instance, "office", None),
                entity_type="Task", entity_id=str(instance.pk),
                entity_label=label,
                request=_request_from_instance(instance),
            )
    except ImportError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Finance
# ─────────────────────────────────────────────────────────────────────────────

def _connect_finance():
    try:
        from apps.finance.models import Invoice, Expense

        @receiver(post_save, sender=Invoice, weak=False)
        def on_invoice_save(sender, instance, created, **kwargs):
            actor = _actor_from_instance(instance)
            action = "created" if created else "updated"
            actor_name = actor.get_full_name() if actor else "Sistema"
            _safe_log(
                module="finance", action=action,
                summary=f"{actor_name} {'criou' if created else 'atualizou'} Fatura #{instance.pk}",
                actor=actor,
                organization=getattr(instance, "organization", None),
                office=getattr(instance, "office", None),
                entity_type="Invoice", entity_id=str(instance.pk),
                entity_label=f"Fatura #{instance.pk}",
                request=_request_from_instance(instance),
            )

        @receiver(post_save, sender=Expense, weak=False)
        def on_expense_save(sender, instance, created, **kwargs):
            actor = _actor_from_instance(instance)
            action = "created" if created else "updated"
            actor_name = actor.get_full_name() if actor else "Sistema"
            _safe_log(
                module="finance", action=action,
                summary=f"{actor_name} {'registrou' if created else 'atualizou'} Despesa '{getattr(instance, 'description', '') or ''}' ",
                actor=actor,
                organization=getattr(instance, "organization", None),
                office=getattr(instance, "office", None),
                entity_type="Expense", entity_id=str(instance.pk),
                entity_label=f"Despesa #{instance.pk}",
                request=_request_from_instance(instance),
            )
    except ImportError:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Login signal (via api/views.py — já registra manualmente)
# ─────────────────────────────────────────────────────────────────────────────


def setup():
    """Conectar todos os signals. Chamar de ActivityConfig.ready()."""
    _connect_process()
    _connect_deadline()
    _connect_customer()
    _connect_document()
    _connect_task()
    _connect_finance()
