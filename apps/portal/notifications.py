"""
Utilitários para criação de notificações no portal.

Uso:
    from apps.portal.notifications import notify, notify_office_admins

    notify(
        users=[process.responsible],
        organization=org,
        office=office,
        title="Novo processo criado",
        message="O processo 0001234-00.2024... foi atribuído a você.",
        notif_type="info",
        url=f"/app/processos/{process.id}/",
    )
"""
from __future__ import annotations

import logging
from typing import Iterable

from django.contrib.auth import get_user_model
from django.db import transaction

logger = logging.getLogger("apps.portal")

User = get_user_model()


def notify(
    users,
    organization,
    office,
    title: str,
    message: str = "",
    notif_type: str = "info",
    url: str = "",
):
    """
    Cria notificações para uma lista/queryset de usuários.
    Usa bulk_create para eficiência.
    """
    from apps.portal.models import Notification

    if not users:
        return

    # Aceita queryset, lista ou usuário único
    if hasattr(users, "__iter__") and not hasattr(users, "model"):
        user_list = list(users)
    elif hasattr(users, "model"):
        user_list = list(users)
    else:
        user_list = [users]

    # Remove None e duplicatas
    user_list = list({u.pk: u for u in user_list if u is not None}.values())
    if not user_list:
        return

    try:
        with transaction.atomic():
            Notification.objects.bulk_create([
                Notification(
                    user=user,
                    organization=organization,
                    office=office,
                    title=title,
                    message=message,
                    type=notif_type,
                    url=url,
                    is_read=False,
                )
                for user in user_list
            ], ignore_conflicts=True)
    except Exception as exc:
        logger.warning("Erro ao criar notificações: %s", exc)


def notify_office_admins(organization, office, title: str, message: str = "",
                         notif_type: str = "info", url: str = ""):
    """Notifica todos os admins do office."""
    from apps.memberships.models import Membership
    admins = User.objects.filter(
        memberships__organization=organization,
        memberships__office=office,
        memberships__role__in=["org_admin", "office_admin", "admin"],
        memberships__is_active=True,
    ).distinct()
    notify(admins, organization, office, title, message, notif_type, url)


def notify_responsible_and_admins(responsible_user, organization, office,
                                   title: str, message: str = "",
                                   notif_type: str = "info", url: str = ""):
    """Notifica o responsável + admins do office (sem duplicar)."""
    from apps.memberships.models import Membership
    admins = list(User.objects.filter(
        memberships__organization=organization,
        memberships__office=office,
        memberships__role__in=["org_admin", "office_admin", "admin"],
        memberships__is_active=True,
    ).distinct())

    users = admins[:]
    if responsible_user and responsible_user not in users:
        users.append(responsible_user)

    notify(users, organization, office, title, message, notif_type, url)
