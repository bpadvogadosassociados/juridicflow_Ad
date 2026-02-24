from django.db import models
from django.core.exceptions import ValidationError
import re
from django.contrib.auth.models import Group


def validate_cnpj(value: str):
    digits = re.sub(r"\D", "", value or "")
    if len(digits) != 14:
        raise ValidationError("CNPJ deve ter 14 dígitos.")
    return value

class Organization(models.Model):
    PLAN_CHOICES = [("basic", "Básico"), ("pro", "Profissional"), ("enterprise", "Enterprise")]
    name = models.CharField("Nome", max_length=255)
    document = models.CharField("CNPJ", max_length=18, unique=True, validators=[validate_cnpj])
    plan = models.CharField("Plano", max_length=20, choices=PLAN_CHOICES, default="basic")
    is_active = models.BooleanField("Ativa", default=True)
    settings = models.JSONField("Configurações", default=dict, blank=True)

    created_at = models.DateTimeField("Criado em", auto_now_add=True)
    updated_at = models.DateTimeField("Atualizado em", auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Organização"
        verbose_name_plural = "Organizações"

    def __str__(self):
        return self.name

class OrgRole(models.Model):
    name = models.CharField(max_length=100) #Ex: Estagiario
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE)
    office = models.ForeignKey("offices.Office", on_delete=models.CASCADE, null=True, blank=True)

    # Os grupos do Django que compõem essa função
    groups = models.ManyToManyField(Group, blank=True)