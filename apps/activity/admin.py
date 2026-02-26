from django.contrib import admin
from .models import ActivityEvent


@admin.register(ActivityEvent)
class ActivityEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor_name", "module", "action", "entity_type", "entity_label", "summary")
    list_filter = ("module", "action", "organization")
    search_fields = ("summary", "actor_name", "entity_label", "entity_id")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False  # Log-only — sem criação manual

    def has_change_permission(self, request, obj=None):
        return False  # Imutável
