from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "organization", "office", "action", "model_name", "object_id")
    list_filter = ("action", "created_at")
    search_fields = ("user__email", "model_name", "object_id")
    readonly_fields = ("created_at",)
