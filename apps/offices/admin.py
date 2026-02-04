from django.contrib import admin
from .models import Office

@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "is_active")
    list_filter = ("is_active", "organization")
    search_fields = ("name", "organization__name")
