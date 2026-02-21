from django.db import models
from django.core.validators import MinValueValidator
from apps.shared.models import OrganizationScopedModel
from apps.shared.managers import OrganizationScopedManager
from decimal import Decimal

class FeeAgreement(OrganizationScopedModel):
    """Contrato de honorários com cliente"""
    
    BILLING_TYPE_CHOICES = [
        ("one_time", "Pagamento Único"),
        ("monthly", "Mensal"),
        ("success_fee", "Êxito"),
        ("hourly", "Por Hora"),
        ("installments", "Parcelado"),
    ]
    
    STATUS_CHOICES = [
        ("draft", "Rascunho"),
        ("active", "Ativo"),
        ("suspended", "Suspenso"),
        ("completed", "Concluído"),
        ("cancelled", "Cancelado"),
    ]
    
    customer = models.ForeignKey(
        "customers.Customer", 
        on_delete=models.CASCADE, 
        related_name="fee_agreements",
        verbose_name="Cliente"
    )
    process = models.ForeignKey(
        "processes.Process", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="fee_agreements",
        verbose_name="Processo"
    )
    
    title = models.CharField("Título", max_length=255)
    description = models.TextField("Descrição", blank=True)
    
    amount = models.DecimalField(
        "Valor",
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    billing_type = models.CharField(
        "Tipo de Cobrança",
        max_length=20, 
        choices=BILLING_TYPE_CHOICES,
        default="one_time"
    )
    
    installments = models.PositiveIntegerField(
        "Parcelas",
        default=1,
        help_text="Número de parcelas (para tipo 'Parcelado')"
    )
    
    status = models.CharField(
        "Status",
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )
    
    start_date = models.DateField("Data de Início", null=True, blank=True)
    end_date = models.DateField("Data de Término", null=True, blank=True)
    
    notes = models.TextField("Observações", blank=True)
    
    responsible = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fee_agreements",
        verbose_name="Responsável"
    )

    objects = OrganizationScopedManager()

    class Meta:
        verbose_name = "Contrato de Honorários"
        verbose_name_plural = "Contratos de Honorários"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "office", "status"]),
            models.Index(fields=["customer", "status"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.customer.name}"
    
    @property
    def total_invoiced(self):
        """Total faturado"""
        return self.invoices.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
    
    @property
    def total_received(self):
        """Total recebido"""
        return Payment.objects.filter(
            invoice__agreement=self
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
    
    @property
    def balance(self):
        """Saldo pendente"""
        return self.amount - self.total_received


class Invoice(OrganizationScopedModel):
    """Fatura/Cobrança"""
    
    STATUS_CHOICES = [
        ("draft", "Rascunho"),
        ("issued", "Emitida"),
        ("sent", "Enviada"),
        ("paid", "Paga"),
        ("overdue", "Vencida"),
        ("cancelled", "Cancelada"),
    ]
    
    agreement = models.ForeignKey(
        FeeAgreement, 
        on_delete=models.CASCADE, 
        related_name="invoices",
        verbose_name="Contrato"
    )
    
    number = models.CharField(
        "Número",
        max_length=50,
        blank=True,
        null=True,
        help_text="Número da fatura (ex: 2024/001)"
    )
    
    issue_date = models.DateField("Data de Emissão")
    due_date = models.DateField("Data de Vencimento")
    
    amount = models.DecimalField(
        "Valor",
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    discount = models.DecimalField(
        "Desconto",
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    status = models.CharField(
        "Status",
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )
    
    description = models.TextField("Descrição", blank=True)
    notes = models.TextField("Observações", blank=True)
    
    payment_method = models.CharField(
        "Método de Pagamento",
        max_length=50,
        blank=True
    )

    objects = OrganizationScopedManager()

    class Meta:
        verbose_name = "Fatura"
        verbose_name_plural = "Faturas"
        ordering = ["-issue_date"]
        unique_together = [("organization", "office", "number")]
        indexes = [
            models.Index(fields=["organization", "office", "status"]),
            models.Index(fields=["agreement", "status"]),
            models.Index(fields=["due_date"]),
        ]

    def __str__(self):
        return f"Fatura {self.number} - {self.agreement.customer.name}"
    
    @property
    def net_amount(self):
        """Valor líquido (com desconto)"""
        return self.amount - self.discount
    
    @property
    def paid_amount(self):
        """Valor pago"""
        return self.payments.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
    
    @property
    def balance(self):
        """Saldo pendente"""
        return self.net_amount - self.paid_amount
    
    @property
    def is_overdue(self):
        """Verifica se está vencida"""
        from django.utils import timezone
        return (
            self.status not in ('paid', 'cancelled') and 
            self.due_date < timezone.now().date()
        )


class Payment(OrganizationScopedModel):
    """Pagamento recebido"""
    
    METHOD_CHOICES = [
        ("pix", "PIX"),
        ("bank_transfer", "Transferência Bancária"),
        ("debit_card", "Cartão de Débito"),
        ("credit_card", "Cartão de Crédito"),
        ("cash", "Dinheiro"),
        ("check", "Cheque"),
        ("boleto", "Boleto"),
        ("other", "Outro"),
    ]
    
    invoice = models.ForeignKey(
        Invoice, 
        on_delete=models.CASCADE, 
        related_name="payments",
        verbose_name="Fatura"
    )
    
    paid_at = models.DateField("Data do Pagamento")
    
    amount = models.DecimalField(
        "Valor",
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    method = models.CharField(
        "Método",
        max_length=30,
        choices=METHOD_CHOICES,
        default="pix"
    )
    
    reference = models.CharField(
        "Referência",
        max_length=255,
        blank=True,
        help_text="Número do comprovante, transação, etc"
    )
    
    notes = models.TextField("Observações", blank=True)
    
    recorded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments_recorded",
        verbose_name="Registrado por"
    )

    objects = OrganizationScopedManager()

    class Meta:
        verbose_name = "Pagamento"
        verbose_name_plural = "Pagamentos"
        ordering = ["-paid_at"]
        indexes = [
            models.Index(fields=["organization", "office", "paid_at"]),
            models.Index(fields=["invoice"]),
        ]

    def __str__(self):
        return f"Pagamento de R$ {self.amount} em {self.paid_at}"


class Expense(OrganizationScopedModel):
    """Despesa do escritório"""
    
    CATEGORY_CHOICES = [
        ("salary", "Salários"),
        ("rent", "Aluguel"),
        ("utilities", "Contas (água, luz, etc)"),
        ("supplies", "Material de Escritório"),
        ("technology", "Tecnologia/Software"),
        ("marketing", "Marketing"),
        ("legal_fees", "Taxas Judiciais"),
        ("travel", "Viagens"),
        ("training", "Treinamentos"),
        ("consulting", "Consultoria"),
        ("other", "Outros"),
    ]
    
    STATUS_CHOICES = [
        ("pending", "Pendente"),
        ("paid", "Paga"),
        ("cancelled", "Cancelada"),
    ]
    
    title = models.CharField("Título", max_length=255)
    description = models.TextField("Descrição", blank=True)
    
    category = models.CharField(
        "Categoria",
        max_length=50,
        choices=CATEGORY_CHOICES,
        default="other"
    )
    
    date = models.DateField("Data")
    due_date = models.DateField("Data de Vencimento", null=True, blank=True)
    
    amount = models.DecimalField(
        "Valor",
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    status = models.CharField(
        "Status",
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    
    payment_method = models.CharField(
        "Método de Pagamento",
        max_length=50,
        blank=True
    )
    
    supplier = models.CharField(
        "Fornecedor",
        max_length=255,
        blank=True
    )
    
    reference = models.CharField(
        "Referência",
        max_length=255,
        blank=True,
        help_text="Número da nota fiscal, comprovante, etc"
    )
    
    notes = models.TextField("Observações", blank=True)
    
    responsible = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
        verbose_name="Responsável"
    )

    objects = OrganizationScopedManager()

    class Meta:
        verbose_name = "Despesa"
        verbose_name_plural = "Despesas"
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["organization", "office", "date"]),
            models.Index(fields=["organization", "office", "status"]),
            models.Index(fields=["category", "date"]),
        ]

    def __str__(self):
        return f"{self.title} - R$ {self.amount}"

class Proposal(OrganizationScopedModel):
    """Proposta comercial / pré-contrato de honorários."""
    STATUS_CHOICES = [
        ("draft", "Rascunho"),
        ("sent", "Enviada"),
        ("accepted", "Aceita"),
        ("rejected", "Rejeitada"),
        ("expired", "Expirada"),
    ]

    title = models.CharField("Título", max_length=255)
    description = models.TextField("Escopo / Descrição", blank=True)
    amount = models.DecimalField(
        "Valor Total", max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))]
    )
    status = models.CharField("Status", max_length=20, choices=STATUS_CHOICES, default="draft")
    issue_date = models.DateField("Data de Emissão", null=True, blank=True)
    valid_until = models.DateField("Válida até", null=True, blank=True)

    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.CASCADE,
        related_name="proposals", verbose_name="Cliente"
    )
    process = models.ForeignKey(
        "processes.Process", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="proposals", verbose_name="Processo"
    )
    responsible = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="proposals", verbose_name="Responsável"
    )

    notes = models.TextField("Observações", blank=True)
    pdf_file = models.FileField("PDF", upload_to="proposals/", null=True, blank=True)

    objects = OrganizationScopedManager()

    class Meta:
        verbose_name = "Proposta"
        verbose_name_plural = "Propostas"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "office", "status"]),
            models.Index(fields=["customer", "status"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.customer.name}"

    def convert_to_agreement(self):
        """Converte proposta aceita em FeeAgreement."""
        if self.status != "accepted":
            raise ValueError("Apenas propostas aceitas podem ser convertidas.")
        return FeeAgreement.objects.create(
            organization=self.organization,
            office=self.office,
            customer=self.customer,
            process=self.process,
            title=self.title,
            description=self.description,
            amount=self.amount,
            responsible=self.responsible,
            status="active",
        )
