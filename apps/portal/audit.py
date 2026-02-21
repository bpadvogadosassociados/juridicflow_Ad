"""
Audit Trail para operações sensíveis.

Registra WHO did WHAT on WHICH object WHEN, com IP e user-agent.

Uso direto:
    from apps.portal.audit import log_audit

    log_audit(
        request=request,
        action="delete",
        model_name="Process",
        object_id=process.id,
        detail="Processo 000123 deletado",
    )

Uso automático via decorator:
    from apps.portal.audit import audited

    @audited(action="delete", model_name="Process")
    def processo_delete(request, process_id):
        ...
"""
import logging
from functools import wraps

from django.db import models
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("apps.portal.audit")


class AuditEntry(models.Model):
    """Registro imutável de operação sensível."""

    ACTION_CHOICES = [
        ("create", "Criação"),
        ("update", "Atualização"),
        ("delete", "Exclusão"),
        ("login", "Login"),
        ("logout", "Logout"),
        ("export", "Exportação"),
        ("import", "Importação"),
        ("permission_change", "Alteração de Permissão"),
        ("payment", "Pagamento"),
        ("share", "Compartilhamento"),
    ]

    # Quem
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_entries",
    )
    user_email = models.CharField(max_length=254)  # Preserva mesmo se user deletado
    user_role = models.CharField(max_length=30, blank=True, default="")

    # Contexto
    organization_id = models.PositiveIntegerField(null=True)
    office_id = models.PositiveIntegerField(null=True)

    # O que
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100, blank=True, default="")
    object_id = models.CharField(max_length=100, blank=True, default="")
    detail = models.TextField(blank=True, default="")

    # Quando + de onde
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")

    class Meta:
        app_label = "portal"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["organization_id", "-timestamp"]),
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
            models.Index(fields=["model_name", "object_id"]),
        ]
        verbose_name = "Registro de Auditoria"
        verbose_name_plural = "Registros de Auditoria"

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.user_email} → {self.action} {self.model_name}"


def _get_client_ip(request) -> str:
    """Extrai IP real considerando proxy."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def log_audit(
    request,
    action: str,
    model_name: str = "",
    object_id: str = "",
    detail: str = "",
):
    """
    Grava entrada de auditoria.
    Nunca levanta exceção — falhas são logadas silenciosamente.
    """
    try:
        membership = getattr(request, "membership", None)
        AuditEntry.objects.create(
            user=request.user if request.user.is_authenticated else None,
            user_email=getattr(request.user, "email", "anonymous"),
            user_role=membership.role if membership else "",
            organization_id=getattr(request, "organization", None) and request.organization.id,
            office_id=getattr(request, "office", None) and request.office.id,
            action=action,
            model_name=model_name,
            object_id=str(object_id),
            detail=detail[:2000],  # Trunca para segurança
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )
    except Exception as exc:
        logger.error("Falha ao gravar audit entry: %s", exc)


def audited(action: str, model_name: str = ""):
    """
    Decorator que grava audit entry após execução da view.

    @audited(action="delete", model_name="Process")
    def processo_delete(request, process_id):
        ...
        return JsonResponse({"ok": True})
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)

            # Só audita se a view retornou sucesso (2xx)
            status = getattr(response, "status_code", 200)
            if 200 <= status < 300:
                # Tenta extrair object_id dos kwargs da URL
                obj_id = ""
                for key in ("process_id", "customer_id", "document_id",
                            "invoice_id", "expense_id", "deadline_id",
                            "event_id", "card_id", "column_id",
                            "share_id", "folder_id", "version_id",
                            "contract_id", "template_id"):
                    if key in kwargs:
                        obj_id = str(kwargs[key])
                        break

                log_audit(
                    request=request,
                    action=action,
                    model_name=model_name or view_func.__name__,
                    object_id=obj_id,
                    detail=f"{view_func.__module__}.{view_func.__name__}",
                )

            return response
        return wrapper
    return decorator