from django.db import models
from django.core.exceptions import ValidationError
import re
from django.contrib.auth.models import Group


def validate_cnpj(value: str):
    digits = re.sub(r"\D", "", value or "")
    if len(digits) != 14:
        raise ValidationError("CNPJ deve ter 14 dígitos.")
    # Reject repeated sequences (e.g. 11111111111111)
    if digits == digits[0] * 14:
        raise ValidationError("CNPJ inválido.")
    # First check digit
    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(digits[i]) * weights_1[i] for i in range(12))
    remainder = total % 11
    check_1 = 0 if remainder < 2 else 11 - remainder
    if int(digits[12]) != check_1:
        raise ValidationError("CNPJ inválido (dígito verificador).")
    # Second check digit
    weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(digits[i]) * weights_2[i] for i in range(13))
    remainder = total % 11
    check_2 = 0 if remainder < 2 else 11 - remainder
    if int(digits[13]) != check_2:
        raise ValidationError("CNPJ inválido (dígito verificador).")
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
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="org_roles")
    office = models.ForeignKey("offices.Office", on_delete=models.CASCADE, null=True, blank=True, related_name="org_roles")

    # Os grupos do Django que compõem essa função
    groups = models.ManyToManyField(Group, blank=True, related_name="org_roles")

    class Meta:
        verbose_name = "Função da Organização"
        verbose_name_plural = "Funções da Organização"
        unique_together = [("organization", "office", "name")]

    def __str__(self):
        return f"{self.organization.name} - {self.name}"