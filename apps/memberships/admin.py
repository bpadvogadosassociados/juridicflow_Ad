from django.contrib import admin
from .models import Membership

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "office", "role", "is_active")
    list_filter = ("role", "is_active", "organization")
    search_fields = ("user__email", "organization__name", "office__name")
