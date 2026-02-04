from django.db import models
from apps.shared.models import OrganizationScopedModel
from apps.shared.managers import OrganizationScopedManager

class Process(OrganizationScopedModel):
    number = models.CharField(max_length=40, help_text="Número CNJ ou identificador interno")
    court = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=255, blank=True)
    phase = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=50, default="active")

    objects = OrganizationScopedManager()

    class Meta:
        indexes = [models.Index(fields=["organization", "office", "number"])]
        verbose_name = "Processo"
        verbose_name_plural = "Processos"

    def __str__(self):
        return self.number

class ProcessParty(models.Model):
    ROLE_CHOICES = [
        ("autor", "Autor"),
        ("reu", "Réu"),
        ("terceiro", "Terceiro"),
        ("advogado", "Advogado"),
        ("outro", "Outro"),
    ]
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name="parties")
    customer = models.ForeignKey("customers.Customer", on_delete=models.SET_NULL, null=True, blank=True, related_name="process_parties")
    name = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.process.number} :: {self.role}"
