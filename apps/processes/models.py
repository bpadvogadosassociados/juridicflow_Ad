from django.db import models
from apps.shared.models import OrganizationScopedModel
from apps.shared.managers import OrganizationScopedManager

import re
from django.core.exceptions import ValidationError


def validate_cnj(value):
    """
    Valida número CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO
    Exemplo: 0000000-00.0000.0.00.0000
    """
    if not value:
        return
    value = value.strip()
    pattern = r'^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$'
    if not re.match(pattern, value):
        raise ValidationError(
            f'"{value}" não é um número CNJ válido. '
            'Formato esperado: NNNNNNN-DD.AAAA.J.TR.OOOO '
            '(Exemplo: 0000000-00.2024.8.26.0100)'
        )


class Process(OrganizationScopedModel):
    PHASE_CHOICES = [
        ("initial", "Inicial"),
        ("instruction", "Instrução"),
        ("sentence", "Sentença"),
        ("appeal", "Recurso"),
        ("execution", "Execução"),
        ("archived", "Arquivado"),
    ]
    STATUS_CHOICES = [
        ("active", "Ativo"),
        ("suspended", "Suspenso"),
        ("finished", "Finalizado"),
    ]
    AREA_CHOICES = [
        ("trabalhista", "Trabalhista"),
        ("previdenciario", "Previdenciário"),
        ("civil", "Cível"),
        ("criminal", "Criminal"),
        ("familia", "Família"),
        ("tributario", "Tributário"),
        ("empresarial", "Empresarial"),
        ("consumidor", "Consumidor"),
        ("administrativo", "Administrativo"),
        ("outro", "Outro"),
    ]
    RISK_CHOICES = [
        ("baixo", "Baixo"),
        ("medio", "Médio"),
        ("alto", "Alto"),
        ("critico", "Crítico"),
    ]

    number = models.CharField(
        "Número CNJ",
        max_length=40,
        help_text="Formato: NNNNNNN-DD.AAAA.J.TR.OOOO",
        validators=[validate_cnj]
    )
    court = models.CharField("Tribunal", max_length=255, blank=True)
    subject = models.CharField("Assunto", max_length=255, blank=True)
    phase = models.CharField("Fase", max_length=100, blank=True, choices=PHASE_CHOICES, default="initial")
    status = models.CharField("Status", max_length=50, default="active", choices=STATUS_CHOICES)

    # Campos ricos
    area = models.CharField("Área Jurídica", max_length=50, choices=AREA_CHOICES, blank=True)
    description = models.TextField("Descrição / Objeto da Ação", blank=True)
    cause_value = models.DecimalField("Valor da Causa (R$)", max_digits=14, decimal_places=2, null=True, blank=True)
    filing_date = models.DateField("Data de Ajuizamento", null=True, blank=True)
    distribution_date = models.DateField("Data de Distribuição", null=True, blank=True)
    first_hearing_date = models.DateField("Data da 1ª Audiência", null=True, blank=True)
    sentence_date = models.DateField("Data da Sentença", null=True, blank=True)
    court_unit = models.CharField("Vara / Unidade Judiciária", max_length=255, blank=True)
    judge_name = models.CharField("Nome do Juiz", max_length=255, blank=True)
    risk = models.CharField("Risco", max_length=20, choices=RISK_CHOICES, blank=True)
    success_probability = models.PositiveSmallIntegerField(
        "Probabilidade de Êxito (%)", null=True, blank=True,
        help_text="0 a 100"
    )
    tags = models.CharField("Tags", max_length=500, blank=True, help_text="Separadas por vírgula")
    internal_notes = models.TextField("Observações Internas", blank=True)
    next_action = models.CharField("Próxima Movimentação Esperada", max_length=500, blank=True)
    last_movement = models.CharField("Última Movimentação", max_length=500, blank=True)
    last_movement_date = models.DateField("Data da Última Movimentação", null=True, blank=True)

    responsible = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="processes",
        verbose_name="Responsável"
    )

    objects = OrganizationScopedManager()

    class Meta:
        indexes = [models.Index(fields=["organization", "office", "number"])]
        unique_together = [("organization", "office", "number")]
        verbose_name = "Processo"
        verbose_name_plural = "Processos"

    def __str__(self):
        return self.number

    @property
    def tag_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]


class ProcessParty(models.Model):
    ROLE_CHOICES = [
        ("autor", "Autor"),
        ("reu", "Réu"),
        ("terceiro", "Terceiro"),
        ("advogado", "Advogado"),
        ("testemunha", "Testemunha"),
        ("perito", "Perito"),
        ("outro", "Outro"),
    ]
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name="parties")
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="process_parties"
    )
    name = models.CharField("Nome", max_length=255, blank=True)
    role = models.CharField("Papel", max_length=20, choices=ROLE_CHOICES)
    document = models.CharField("CPF/CNPJ", max_length=50, blank=True)
    email = models.EmailField("Email", blank=True)
    phone = models.CharField("Telefone", max_length=40, blank=True)
    notes = models.TextField("Observações", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Parte do Processo"
        verbose_name_plural = "Partes do Processo"

    def __str__(self):
        display = self.customer.name if self.customer else self.name
        return f"{self.process.number} :: {self.get_role_display()} :: {display}"

    @property
    def display_name(self):
        if self.customer:
            return self.customer.name
        return self.name or "—"


class ProcessNote(models.Model):
    """Notas / timeline interna do processo."""
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, related_name="process_notes"
    )
    text = models.TextField("Texto")
    is_private = models.BooleanField("Privada", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Nota do Processo"
        verbose_name_plural = "Notas do Processo"

    def __str__(self):
        return f"Nota de {self.author} em {self.process.number}"
