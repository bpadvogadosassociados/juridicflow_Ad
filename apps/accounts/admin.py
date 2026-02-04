from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-date_joined",)
    list_display = ("email", "username", "is_staff", "is_active", "date_joined")
    search_fields = ("email", "username", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        ("Informações pessoais", {"fields": ("first_name", "last_name")}),
        ("Permissões", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Datas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "username", "password1", "password2", "is_staff", "is_active")}),
    )
