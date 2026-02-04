from django.db import models
from apps.shared.models import OrganizationScopedModel, SoftDeleteModel
from apps.shared.managers import OrganizationScopedManager

class Customer(OrganizationScopedModel, SoftDeleteModel):
    TYPE_CHOICES = [("PF", "Pessoa Física"), ("PJ", "Pessoa Jurídica")]

    name = models.CharField(max_length=255)
    document = models.CharField(max_length=50, blank=True)
    type = models.CharField(max_length=2, choices=TYPE_CHOICES, default="PF")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    notes = models.TextField(blank=True)

    objects = OrganizationScopedManager()

    class Meta:
        indexes = [models.Index(fields=["organization", "office", "name"])]
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return self.name
