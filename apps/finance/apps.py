from django.apps import AppConfig
class FinanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoAutoField" if False else "django.db.models.BigAutoField"
    name = "apps.finance"
    verbose_name = "Financeiro"
