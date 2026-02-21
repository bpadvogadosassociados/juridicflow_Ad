from django.contrib import admin
from .models import Organization

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "document", "plan", "is_active", "created_at")
    search_fields = ("name", "document")
    list_filter = ("plan", "is_active", "created_at")
    readonly_fields = ("created_at", "updated_at")
