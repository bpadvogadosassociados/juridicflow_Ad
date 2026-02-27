import logging
from functools import wraps

from django.db import models
from django.conf import settings
from django.utils import timezone

from apps.activity.models import log_event

logger = logging.getLogger("apps.portal.audit")

_ACTION_MAP = {
    "create": "created",
    "update": "updated",
    "delete": "deleted",
    "login": "login",
    "logout": "logout",
    "export": "exported",
    "import": "custom",
    "permission_change": "permission_changed",
    "payment": "custom",
    "share": "custom",
}


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
    Auditoria definitiva: grava em ActivityEvent.
    Nunca levanta exceção.
    """
    try:
        membership = getattr(request, "membership", None)
        mapped_action = _ACTION_MAP.get(action, "custom")

        actor = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
        actor_label = (actor.get_full_name() or actor.email) if actor else "anonymous"

        summary = detail or f"{actor_label} executou {action} em {model_name} {object_id}".strip()
        summary = summary[:500]

        log_event(
            module="system",
            action=mapped_action,
            summary=summary,
            actor=actor,
            organization=getattr(request, "organization", None),
            office=getattr(request, "office", None),
            entity_type=model_name or "",
            entity_id=str(object_id or ""),
            entity_label=str(object_id or ""),
            request=request,
            changes={
                "legacy_action": action,
                "legacy_source": "portal.AuditEntry",
                "user_role": getattr(membership, "role", "") if membership else "",
                "detail": (detail or "")[:2000],
            },
        )
    except Exception as exc:
        logger.error("Falha ao gravar audit event: %s", exc)


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