"""
Utilitários compartilhados entre as views do portal.
"""
import json
import logging

from apps.portal.models import ActivityLog

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
        ActivityLog.objects.create(
            organization=request.organization,
            office=request.office,
            actor=request.user,
            verb=verb,
            description=description,
        )
    except Exception as exc:
        logger.warning("Falha ao gravar ActivityLog: %s", exc)