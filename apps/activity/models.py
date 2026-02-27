"""
Activity Log — registro imutável de todos os eventos da aplicação.
Serve como base para:
  - Aba Atividade (auditoria/transparência)
  - Métricas do módulo Equipe
"""

from django.db import models
from django.conf import settings


class ActivityEvent(models.Model):
    """
    Evento registrado na aplicação. Nunca editável.
    """
    ACTION_CHOICES = [
        # Auth
        ("login",              "Login"),
        ("logout",             "Logout"),
        ("password_changed",   "Senha alterada"),
        # CRUD genérico
        ("created",            "Criado"),
        ("updated",            "Atualizado"),
        ("deleted",            "Excluído"),
        ("restored",           "Restaurado"),
        # Específicos
        ("status_changed",     "Status alterado"),
        ("assigned",           "Atribuído"),
        ("commented",          "Comentou"),
        ("uploaded",           "Upload"),
        ("downloaded",         "Download"),
        ("exported",           "Exportado"),
        ("moved",              "Movido"),
        ("completed",          "Concluído"),
        ("reopened",           "Reaberto"),
        # Permissões / equipe
        ("member_added",       "Membro adicionado"),
        ("member_removed",     "Membro removido"),
        ("role_changed",       "Função alterada"),
        ("permission_changed", "Permissão alterada"),
        
        ("custom",             "Custom"),
    ]

    MODULE_CHOICES = [
        ("auth",       "Autenticação"),
        ("processes",  "Processos"),
        ("deadlines",  "Prazos"),
        ("customers",  "Contatos"),
        ("documents",  "Documentos"),
        ("finance",    "Financeiro"),
        ("tasks",      "Tarefas"),
        ("kanban",     "Kanban"),
        ("calendar",   "Agenda"),
        ("team",       "Equipe"),
        ("settings",   "Configurações"),
        ("system",     "Sistema"),
    ]

    # Tenant
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="activity_events",
        null=True, blank=True,
    )
    office = models.ForeignKey(
        "offices.Office",
        on_delete=models.CASCADE,
        related_name="activity_events",
        null=True, blank=True,
    )

    # Quem fez
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="activity_events",
    )
    actor_name = models.CharField(max_length=255, blank=True)  # snapshot no momento

    # O quê
    module = models.CharField(max_length=32, choices=MODULE_CHOICES)
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)

    # Sobre qual objeto
    entity_type = models.CharField(max_length=100, blank=True)  # ex: "Process"
    entity_id   = models.CharField(max_length=64,  blank=True)  # ex: "42"
    entity_label = models.CharField(max_length=255, blank=True) # ex: "Processo 0001234"

    # Sumário legível
    summary = models.CharField(max_length=500)

    # Diff (apenas em updates)
    changes = models.JSONField(default=dict, blank=True)
    # { "field": {"before": val, "after": val}, ... }

    # Contexto técnico
    ip_address   = models.GenericIPAddressField(null=True, blank=True)
    user_agent   = models.CharField(max_length=512, blank=True)
    request_id   = models.CharField(max_length=64,  blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Evento de Atividade"
        verbose_name_plural = "Eventos de Atividade"
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["organization", "office", "created_at"]),
            models.Index(fields=["organization", "module",  "created_at"]),
            models.Index(fields=["organization", "action",  "created_at"]),
            models.Index(fields=["organization", "actor",   "created_at"]),
            models.Index(fields=["organization", "entity_type", "entity_id"]),
        ]

    def __str__(self):
        return f"[{self.module}] {self.summary} @ {self.created_at:%Y-%m-%d %H:%M}"


def log_event(
    *,
    module: str,
    action: str,
    summary: str,
    actor=None,
    organization=None,
    office=None,
    entity_type: str = "",
    entity_id: str = "",
    entity_label: str = "",
    changes: dict | None = None,
    request=None,
) -> ActivityEvent:
    """
    Helper para registrar eventos de qualquer lugar do código.

    Uso:
        from apps.activity.models import log_event
        log_event(
            module="processes",
            action="created",
            summary=f"{user.get_full_name()} criou Processo {process.number}",
            actor=user,
            organization=org,
            office=office,
            entity_type="Process",
            entity_id=str(process.id),
            entity_label=process.number,
        )
    """
    ip = ua = req_id = ""
    if request:
        ip = (
            request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR", "")
        )
        ua = request.META.get("HTTP_USER_AGENT", "")[:512]
        req_id = request.META.get("HTTP_X_REQUEST_ID", "")[:64]

    actor_name = ""
    if actor:
        actor_name = actor.get_full_name() or actor.email

    return ActivityEvent.objects.create(
        organization=organization,
        office=office,
        actor=actor,
        actor_name=actor_name,
        module=module,
        action=action,
        summary=summary,
        entity_type=entity_type,
        entity_id=str(entity_id),
        entity_label=entity_label,
        changes=changes or {},
        ip_address=ip or None,
        user_agent=ua,
        request_id=req_id,
    )
