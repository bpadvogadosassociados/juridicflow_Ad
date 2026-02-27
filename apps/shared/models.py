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


