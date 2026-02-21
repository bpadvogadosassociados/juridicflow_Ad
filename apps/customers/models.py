from django.db import models
from django.core.validators import RegexValidator
from apps.shared.models import OrganizationScopedModel, SoftDeleteModel
from apps.shared.managers import OrganizationScopedManager

class Customer(OrganizationScopedModel, SoftDeleteModel):
    """Contato/Cliente do escritório"""
    
    TYPE_CHOICES = [
        ("PF", "Pessoa Física"), 
        ("PJ", "Pessoa Jurídica")
    ]
    
    STATUS_CHOICES = [
        ("lead", "Lead"),
        ("prospect", "Prospect"),
        ("client", "Cliente"),
        ("inactive", "Inativo"),
        ("archived", "Arquivado"),
    ]
    
    ORIGIN_CHOICES = [
        ("website", "Website"),
        ("referral", "Indicação"),
        ("social_media", "Redes Sociais"),
        ("advertising", "Publicidade"),
        ("event", "Evento"),
        ("partner", "Parceiro"),
        ("other", "Outro"),
    ]
    
    # Dados básicos
    name = models.CharField("Nome/Razão Social", max_length=255)
    document = models.CharField(
        "CPF/CNPJ", 
        max_length=50, 
        blank=True,
        help_text="CPF (11 dígitos) ou CNPJ (14 dígitos)"
    )
    type = models.CharField("Tipo", max_length=2, choices=TYPE_CHOICES, default="PF")
    status = models.CharField("Status", max_length=20, choices=STATUS_CHOICES, default="lead")
    
    # Contato
    email = models.EmailField("Email", blank=True)
    phone = models.CharField(
        "Telefone", 
        max_length=40, 
        blank=True,
        help_text="Formato: (XX) XXXXX-XXXX"
    )
    phone_secondary = models.CharField("Telefone Secundário", max_length=40, blank=True)
    whatsapp = models.CharField("WhatsApp", max_length=40, blank=True)
    
    # Endereço
    address_street = models.CharField("Rua", max_length=255, blank=True)
    address_number = models.CharField("Número", max_length=20, blank=True)
    address_complement = models.CharField("Complemento", max_length=100, blank=True)
    address_neighborhood = models.CharField("Bairro", max_length=100, blank=True)
    address_city = models.CharField("Cidade", max_length=100, blank=True)
    address_state = models.CharField("Estado", max_length=2, blank=True)
    address_zipcode = models.CharField("CEP", max_length=10, blank=True)
    
    # Profissional (PF)
    profession = models.CharField("Profissão", max_length=100, blank=True)
    birth_date = models.DateField("Data de Nascimento", null=True, blank=True)
    nationality = models.CharField("Nacionalidade", max_length=50, blank=True, default="Brasileira")
    marital_status = models.CharField("Estado Civil", max_length=50, blank=True)
    
    # Empresa (PJ)
    company_name = models.CharField("Nome Fantasia", max_length=255, blank=True)
    state_registration = models.CharField("Inscrição Estadual", max_length=50, blank=True)
    municipal_registration = models.CharField("Inscrição Municipal", max_length=50, blank=True)
    
    # CRM
    origin = models.CharField("Origem", max_length=50, choices=ORIGIN_CHOICES, default="other")
    referral_name = models.CharField("Nome do Indicador", max_length=255, blank=True)
    tags = models.CharField(
        "Tags", 
        max_length=500, 
        blank=True,
        help_text="Tags separadas por vírgula (ex: vip, urgente, trabalhista)"
    )
    
    # Observações
    notes = models.TextField("Observações", blank=True)
    internal_notes = models.TextField(
        "Notas Internas", 
        blank=True,
        help_text="Notas visíveis apenas internamente"
    )
    
    # Responsável
    responsible = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customers",
        verbose_name="Responsável"
    )
    
    # Datas importantes
    first_contact_date = models.DateField("Data do Primeiro Contato", null=True, blank=True)
    last_interaction_date = models.DateField("Última Interação", null=True, blank=True)

    # Pipeline / CRM
    PIPELINE_STAGE_CHOICES = [
        ("novo", "Novo"),
        ("contato_feito", "Contato Feito"),
        ("reuniao_marcada", "Reunião Marcada"),
        ("proposta_enviada", "Proposta Enviada"),
        ("em_negociacao", "Em Negociação"),
        ("ganho", "Ganho"),
        ("perdido", "Perdido"),
    ]
    pipeline_stage = models.CharField(
        "Etapa do Funil", max_length=30, choices=PIPELINE_STAGE_CHOICES, blank=True
    )
    next_action = models.CharField("Próxima Ação", max_length=500, blank=True)
    next_action_date = models.DateField("Data da Próxima Ação", null=True, blank=True)
    estimated_value = models.DecimalField(
        "Valor Estimado (R$)", max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Previsão de honorários ou valor de causa"
    )
    loss_reason = models.CharField("Motivo da Perda", max_length=500, blank=True)
    # LGPD
    can_whatsapp = models.BooleanField("Aceita WhatsApp", default=True)
    can_email = models.BooleanField("Aceita Email", default=True)
    lgpd_consent_date = models.DateField("Data do Consentimento LGPD", null=True, blank=True)

    objects = OrganizationScopedManager()

    class Meta:
        indexes = [
            models.Index(fields=["organization", "office", "name"]),
            models.Index(fields=["organization", "office", "status"]),
            models.Index(fields=["organization", "office", "document"]),
            models.Index(fields=["email"]),
        ]
        verbose_name = "Contato"
        verbose_name_plural = "Contatos"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
    
    @property
    def full_address(self):
        """Endereço completo formatado"""
        parts = []
        if self.address_street:
            street_part = self.address_street
            if self.address_number:
                street_part += f", {self.address_number}"
            if self.address_complement:
                street_part += f" - {self.address_complement}"
            parts.append(street_part)
        
        if self.address_neighborhood:
            parts.append(self.address_neighborhood)
        
        if self.address_city and self.address_state:
            parts.append(f"{self.address_city}/{self.address_state}")
        
        if self.address_zipcode:
            parts.append(f"CEP: {self.address_zipcode}")
        
        return ", ".join(parts) if parts else ""
    
    @property
    def tag_list(self):
        """Lista de tags"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]
    
    @property
    def processes_count(self):
        """Quantidade de processos vinculados"""
        return self.process_parties.count()
    
    @property
    def contracts_count(self):
        """Quantidade de contratos"""
        return self.fee_agreements.filter(status__in=['active', 'completed']).count()


class CustomerInteraction(OrganizationScopedModel):
    """Histórico de interações com o contato"""
    
    TYPE_CHOICES = [
        ("call", "Ligação"),
        ("email", "Email"),
        ("meeting", "Reunião"),
        ("whatsapp", "WhatsApp"),
        ("visit", "Visita"),
        ("note", "Nota"),
        ("other", "Outro"),
    ]
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="interactions",
        verbose_name="Contato"
    )
    
    type = models.CharField("Tipo", max_length=20, choices=TYPE_CHOICES, default="note")
    date = models.DateTimeField("Data/Hora")
    subject = models.CharField("Assunto", max_length=255)
    description = models.TextField("Descrição")
    
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="customer_interactions",
        verbose_name="Registrado por"
    )
    
    class Meta:
        ordering = ["-date"]
        verbose_name = "Interação"
        verbose_name_plural = "Interações"
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.customer.name} ({self.date.strftime('%d/%m/%Y')})"


class CustomerDocument(OrganizationScopedModel):
    """Documentos anexados ao contato"""
    
    TYPE_CHOICES = [
        ("cpf", "CPF"),
        ("rg", "RG"),
        ("cnpj", "CNPJ"),
        ("contract", "Contrato"),
        ("power_of_attorney", "Procuração"),
        ("proof_of_address", "Comprovante de Endereço"),
        ("other", "Outro"),
    ]
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="customer_documents",
        verbose_name="Contato"
    )
    
    title = models.CharField("Título", max_length=255)
    type = models.CharField("Tipo", max_length=50, choices=TYPE_CHOICES, default="other")
    file = models.FileField("Arquivo", upload_to="customer_documents/")
    notes = models.TextField("Observações", blank=True)
    
    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="customer_documents_uploaded",
        verbose_name="Enviado por"
    )
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Documento do Contato"
        verbose_name_plural = "Documentos do Contato"
    
    def __str__(self):
        return f"{self.title} - {self.customer.name}"

class CustomerRelationship(models.Model):
    """Relacionamentos entre contatos (sócio, cônjuge, representante, etc.)."""
    RELATION_CHOICES = [
        ("socio", "Sócio(a)"),
        ("representante", "Representante Legal"),
        ("conjuge", "Cônjuge"),
        ("dependente", "Dependente"),
        ("testemunha", "Testemunha"),
        ("indicador", "Indicador"),
        ("outro", "Outro"),
    ]

    from_customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE,
        related_name="relationships_from",
        verbose_name="Contato"
    )
    to_customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE,
        related_name="relationships_to",
        verbose_name="Relacionado com"
    )
    relation_type = models.CharField("Tipo de Relação", max_length=30, choices=RELATION_CHOICES)
    notes = models.CharField("Observações", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("from_customer", "to_customer", "relation_type")]
        verbose_name = "Relacionamento"
        verbose_name_plural = "Relacionamentos"

    def __str__(self):
        return f"{self.from_customer.name} → {self.get_relation_type_display()} → {self.to_customer.name}"
