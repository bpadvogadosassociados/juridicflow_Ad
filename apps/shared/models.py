from django.db import models
from django.utils import timezone

class TimestampedModel(models.Model):
    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        abstract = True

class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField("Deletado", default=False)
    deleted_at = models.DateTimeField("Deletado em", null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

class OrganizationScopedModel(TimestampedModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        verbose_name="Organização",
        related_name="%(app_label)s_%(class)s_set",
    )
    office = models.ForeignKey(
        "offices.Office",
        on_delete=models.CASCADE,
        verbose_name="Escritório",
        related_name="%(app_label)s_%(class)s_set",
    )

    class Meta:
        abstract = True

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("create", "Criar"),
        ("update", "Atualizar"),
        ("delete", "Deletar"),
        ("login", "Login"),
        ("other", "Outro"),
    ]
    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, null=True, blank=True)
    office = models.ForeignKey("offices.Office", on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Log de auditoria"
        verbose_name_plural = "Logs de auditoria"
