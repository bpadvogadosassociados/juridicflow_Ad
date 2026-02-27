"""
Utilitários compartilhados entre as views do portal.
"""
import json
import logging

from apps.activity.models import log_event

logger = logging.getLogger("apps.portal")


def parse_json_body(request) -> dict:
    """
    Faz parse seguro do body JSON de uma request.
    Retorna dict vazio se body estiver vazio ou inválido.
    """
    try:
        body = request.body.decode("utf-8")
        if not body:
            return {}
        return json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def log_activity(request, verb: str, description: str):
    """Cria ActivityLog de forma padronizada."""
    try:
        log_event(
            module="system",
            action="custom",
            summary=description[:500],
            actor=request.user if getattr(request, "user", None) and request.user.is_authenticated else None,
            organization=getattr(request, "organization", None),
            office=getattr(request, "office", None),
            entity_type="portal",
            entity_id="",
            entity_label="",
            request=request,
            changes={"verb": verb, "legacy_source": "portal.ActivityLog"},
            
            )
    except Exception as exc:
        logger.warning("Falha ao gravar ActivityLog: %s", exc)