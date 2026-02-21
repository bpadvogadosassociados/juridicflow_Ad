from django.db import models
from apps.shared.models import OrganizationScopedModel
from apps.shared.managers import OrganizationScopedManager

import re
from django.core.exceptions import ValidationError


def validate_cnj(value):
    """
    Valida número CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO
    Exemplo: 0000000-00.0000.0.00.0000
    
    Formato:
    - NNNNNNN: Número sequencial (7 dígitos)
    - DD: Dígitos verificadores (2 dígitos)
    - AAAA: Ano de ajuizamento (4 dígitos)
    - J: Segmento da justiça (1 dígito)
    - TR: Tribunal (2 dígitos)
    - OOOO: Origem (4 dígitos)
    """
    if not value:
        return
    
    # Remove espaços
    value = value.strip()
    
    # Padrão CNJ
    pattern = r'^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$'
    
    if not re.match(pattern, value):
        raise ValidationError(
            f'"{value}" não é um número CNJ válido. '
            'Formato esperado: NNNNNNN-DD.AAAA.J.TR.OOOO '
            '(Exemplo: 0000000-00.2024.8.26.0100)'
        )

class Process(OrganizationScopedModel):
    number = models.CharField(
        max_length=40,
        help_text="Número CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO",
        validators=[validate_cnj]  # ✅ ADICIONAR
    )
    court = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=255, blank=True)
    phase = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=50, default="active")

    objects = OrganizationScopedManager()

    class Meta:
        indexes = [models.Index(fields=["organization", "office", "number"])]
        unique_together = [("organization", "office", "number")]  # ✅ ADICIONAR
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
