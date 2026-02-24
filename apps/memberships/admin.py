
from django.contrib import admin

from .models import LocalRole, Membership, PermissionGroupProfile


@admin.register(PermissionGroupProfile)
class PermissionGroupProfileAdmin(admin.ModelAdmin):
    list_display = ("group", "slug", "is_assignable_by_org_admin", "is_assignable_by_tech_director", "is_internal_only", "sort_order")
    list_filter = ("is_assignable_by_org_admin", "is_assignable_by_tech_director", "is_internal_only")
    search_fields = ("group__name", "slug", "description")


@admin.register(LocalRole)
class LocalRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "office", "is_active")
    list_filter = ("organization", "office", "is_active")
    search_fields = ("name", "description", "organization__name", "office__name")
    filter_horizontal = ("groups",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "office", "role", "local_role", "is_active")
    list_filter = ("role", "is_active", "organization", "office")
    search_fields = ("user__email", "organization__name", "office__name")
    filter_horizontal = ("groups",)
