"""
Signals de consistência entre apps.

IMPORTANTE: Django @receiver com sender="string" NÃO funciona.
Por isso, registramos signals no método ready() da AppConfig
usando imports diretos dos models.

Em apps/portal/apps.py:
    class PortalConfig(AppConfig):
        ...
        def ready(self):
            from apps.portal import signals  # noqa: F401
"""
from django.db.models import Sum
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone


# ======================================================
# 1. Auto-atualiza FeeAgreement quando Invoice é salva
# ======================================================

def _connect_invoice_signals():
    """Chamado no ready() após todos os apps carregarem."""
    from apps.finance.models import Invoice

    @receiver(post_save, sender=Invoice)
    def update_agreement_on_invoice_change(sender, instance, **kwargs):
        agreement = getattr(instance, "agreement", None)
        if not agreement:
            return

        invoices = agreement.invoices.all()
        all_paid = not invoices.exclude(status="paid").exists()
        has_invoices = invoices.exists()

        if all_paid and has_invoices and agreement.status == "active":
            agreement.status = "completed"
            agreement.save(update_fields=["status", "updated_at"])


# ======================================================
# 2. Limpa deadlines órfãos quando Process é deletado
# ======================================================

def _connect_process_signals():
    from apps.processes.models import Process

    @receiver(pre_delete, sender=Process)
    def cleanup_deadlines_on_process_delete(sender, instance, **kwargs):
        from django.contrib.contenttypes.models import ContentType
        from apps.deadlines.models import Deadline

        ct = ContentType.objects.get_for_model(instance)
        Deadline.objects.filter(content_type=ct, object_id=instance.id).delete()

    @receiver(pre_delete, sender=Process)
    def unlink_tasks_on_process_delete(sender, instance, **kwargs):
        """Desvincula tasks (não deleta, apenas remove o FK)."""
        if hasattr(instance, "tasks"):
            instance.tasks.update(process=None)


# ======================================================
# 3. Limpa tasks quando Customer é soft-deleted
# ======================================================

def _connect_customer_signals():
    from apps.customers.models import Customer

    @receiver(post_save, sender=Customer)
    def cleanup_tasks_on_customer_soft_delete(sender, instance, **kwargs):
        if instance.is_deleted and hasattr(instance, "tasks"):
            instance.tasks.update(customer=None)


# ======================================================
# 4. Sync Task status com KanbanCard column move
# ======================================================

def _connect_kanban_signals():
    from apps.portal.models import KanbanCard

    COLUMN_STATUS_MAP = {
        "backlog": "backlog",
        "a fazer": "todo",
        "to do": "todo",
        "todo": "todo",
        "em andamento": "in_progress",
        "in progress": "in_progress",
        "doing": "in_progress",
        "revisão": "review",
        "review": "review",
        "concluído": "done",
        "concluido": "done",
        "done": "done",
        "finalizado": "done",
    }

    @receiver(post_save, sender=KanbanCard)
    def sync_task_on_card_move(sender, instance, **kwargs):
        task = getattr(instance, "task", None)
        if not task:
            return

        column_name = instance.column.title.lower().strip() if instance.column else ""
        new_status = COLUMN_STATUS_MAP.get(column_name)

        if new_status and new_status != task.status:
            task.status = new_status
            if new_status == "done" and not task.completed_at:
                task.completed_at = timezone.now()
            task.save(update_fields=["status", "completed_at", "updated_at"])


# ======================================================
# Conecta tudo — chamado ao importar este módulo
# ======================================================

def connect_all_signals():
    """Registra todos os signals. Chamar no AppConfig.ready()."""
    _connect_invoice_signals()
    _connect_process_signals()
    _connect_customer_signals()
    _connect_kanban_signals()


# Auto-conecta ao importar (funciona porque ready() importa este módulo)
connect_all_signals()

# ======================================================
# 5. Notificações automáticas
# ======================================================

def _connect_notification_signals():
    from apps.processes.models import Process
    from apps.deadlines.models import Deadline
    from apps.portal.models import Task
    from apps.portal.notifications import notify, notify_responsible_and_admins

    @receiver(post_save, sender=Process)
    def notify_on_process_create(sender, instance, created, **kwargs):
        if not created:
            return
        try:
            responsible = getattr(instance, "responsible", None)
            notify_responsible_and_admins(
                responsible_user=responsible,
                organization=instance.organization,
                office=instance.office,
                title=f"Novo processo: {instance.number or instance.subject or 'sem número'}",
                message=f"Um novo processo foi criado no sistema.",
                notif_type="info",
                url=f"/app/processos/{instance.pk}/",
            )
        except Exception as exc:
            import logging
            logging.getLogger("apps.portal").warning("Notify process: %s", exc)

    @receiver(post_save, sender=Deadline)
    def notify_on_deadline_create(sender, instance, created, **kwargs):
        if not created:
            return
        try:
            from django.utils import timezone
            import datetime
            days_until = (instance.due_date - timezone.now().date()).days if instance.due_date else 999
            notif_type = "deadline" if days_until <= 3 else "info"
            responsible = getattr(instance, "responsible", None)
            notify_responsible_and_admins(
                responsible_user=responsible,
                organization=instance.organization,
                office=instance.office,
                title=f"Prazo: {instance.title}",
                message=f"Vencimento: {instance.due_date.strftime('%d/%m/%Y') if instance.due_date else 'sem data'}",
                notif_type=notif_type,
                url="/app/prazos/",
            )
        except Exception as exc:
            import logging
            logging.getLogger("apps.portal").warning("Notify deadline: %s", exc)

    @receiver(post_save, sender=Task)
    def notify_on_task_create(sender, instance, created, **kwargs):
        if not created:
            return
        try:
            assigned = getattr(instance, "assigned_to", None)
            if assigned:
                notify(
                    users=[assigned],
                    organization=instance.organization,
                    office=instance.office,
                    title=f"Nova tarefa: {instance.title}",
                    message=f"Uma tarefa foi atribuída a você.",
                    notif_type="task",
                    url="/app/tarefas/",
                )
        except Exception as exc:
            import logging
            logging.getLogger("apps.portal").warning("Notify task: %s", exc)

    def _connect_finance_notification():
        try:
            from apps.finance.models import Invoice, FeeAgreement
            from apps.portal.notifications import notify_responsible_and_admins

            @receiver(post_save, sender=Invoice)
            def notify_on_invoice_create(sender, instance, created, **kwargs):
                if not created:
                    return
                try:
                    notify_responsible_and_admins(
                        responsible_user=None,
                        organization=instance.organization,
                        office=instance.office,
                        title=f"Nova fatura criada",
                        message=f"Fatura de R$ {instance.amount:.2f} para {instance.agreement.customer.name if instance.agreement and instance.agreement.customer else 'cliente'}.",
                        notif_type="info",
                        url="/app/financeiro/faturas/",
                    )
                except Exception as exc:
                    import logging
                    logging.getLogger("apps.portal").warning("Notify invoice: %s", exc)

            @receiver(post_save, sender=FeeAgreement)
            def notify_on_agreement_status(sender, instance, created, **kwargs):
                if created:
                    return
                try:
                    if instance.status in ("completed", "cancelled"):
                        status_label = "concluído" if instance.status == "completed" else "cancelado"
                        notify_responsible_and_admins(
                            responsible_user=None,
                            organization=instance.organization,
                            office=instance.office,
                            title=f"Contrato {status_label}",
                            message=f"O contrato de {instance.customer.name if instance.customer else 'cliente'} foi {status_label}.",
                            notif_type="warning" if instance.status == "cancelled" else "success",
                            url=f"/app/financeiro/contratos/{instance.pk}/",
                        )
                except Exception as exc:
                    import logging
                    logging.getLogger("apps.portal").warning("Notify agreement: %s", exc)
        except Exception:
            pass

    _connect_finance_notification()


connect_all_signals_original = connect_all_signals


def connect_all_signals():
    connect_all_signals_original()
    _connect_notification_signals()


# Re-run including notifications
_connect_notification_signals()
