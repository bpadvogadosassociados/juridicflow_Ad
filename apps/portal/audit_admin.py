"""
Admin para AuditEntry — somente leitura.

Adicione este import em apps/portal/admin.py:
    from apps.portal.audit_admin import AuditEntryAdmin  # noqa: F401

Ou cole o conteúdo diretamente no admin.py existente.
"""
from django.contrib import admin
from apps.portal.audit import AuditEntry


@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):
    list_display = [
        "timestamp", "user_email", "user_role",
        "action", "model_name", "object_id", "ip_address",
    ]
    list_filter = ["action", "model_name", "user_role", "timestamp"]
    search_fields = ["user_email", "detail", "object_id", "ip_address"]
    readonly_fields = [
        "user", "user_email", "user_role",
        "organization_id", "office_id",
        "action", "model_name", "object_id", "detail",
        "timestamp", "ip_address", "user_agent",
    ]
    date_hierarchy = "timestamp"
    ordering = ["-timestamp"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # Só superuser pode limpar audit (e mesmo assim, pense duas vezes)
        return request.user.is_superuser