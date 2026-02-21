from django.db import models

class Office(models.Model):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="offices")
    name = models.CharField("Nome", max_length=255)
    is_active = models.BooleanField("Ativo", default=True)
    settings = models.JSONField("Configurações", default=dict, blank=True)

    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        unique_together = (("organization", "name"),)
        ordering = ("name",)
        verbose_name = "Escritório"
        verbose_name_plural = "Escritórios"

    def __str__(self):
        return f"{self.organization.name} :: {self.name}"
