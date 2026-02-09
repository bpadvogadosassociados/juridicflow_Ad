from django.db import models

# Create your models here.
"""
MÓDULO PUBLICAÇÕES - MODELS
Seguindo arquitetura recomendada pelo gerente:
- Separação entre dado oficial (Publication) e workflow (JudicialEvent)
- Regras de prazo configuráveis
- Preparado para múltiplas fontes (DJEN, Datajud, futuros tribunais)
"""

from django.db import models
from django.core.validators import MinValueValidator
from apps.shared.models import OrganizationScopedModel
from apps.shared.managers import OrganizationScopedManager
import hashlib


class Publication(OrganizationScopedModel):
    """
    DADO OFICIAL - IMUTÁVEL
    Armazena a publicação exatamente como veio da fonte oficial.
    NUNCA deve ser editada após criação (auditoria).
    """
    
    SOURCE_CHOICES = [
        ("djen", "DJEN - Diário Eletrônico Nacional"),
        ("datajud", "Datajud (enriquecimento)"),
        ("manual", "Importação Manual"),
        ("tjsp", "TJSP - Tribunal de Justiça de SP"),
        ("tjrj", "TJRJ - Tribunal de Justiça do RJ"),
        ("other", "Outro"),
    ]
    
    # Origem
    source = models.CharField("Fonte", max_length=20, choices=SOURCE_CHOICES, default="manual")
    source_id = models.CharField("ID na Fonte", max_length=255, blank=True, help_text="ID único da fonte externa")
    
    # Conteúdo oficial (IMUTÁVEL)
    raw_text = models.TextField("Texto Bruto", help_text="Texto completo da publicação")
    content_hash = models.CharField("Hash", max_length=64, unique=True, help_text="SHA256 do conteúdo para idempotência")
    
    # Metadados oficiais
    publication_date = models.DateField("Data da Publicação", help_text="Data oficial da publicação no diário")
    import_date = models.DateTimeField("Data de Importação", auto_now_add=True)
    
    # CNJ do processo (se detectado)
    process_cnj = models.CharField(
        "Número CNJ",
        max_length=40,
        blank=True,
        db_index=True,
        help_text="Número CNJ extraído da publicação"
    )
    
    # Arquivo original (se houver)
    original_file = models.FileField(
        "Arquivo Original",
        upload_to="publications/%Y/%m/",
        null=True,
        blank=True,
        help_text="PDF ou arquivo original da publicação"
    )
    
    # Metadados adicionais (JSON flexível)
    metadata = models.JSONField(
        "Metadados",
        default=dict,
        blank=True,
        help_text="Dados adicionais da fonte (tribunal, órgão, etc)"
    )
    
    # Controle
    imported_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="publications_imported"
    )
    
    objects = OrganizationScopedManager()
    
    class Meta:
        indexes = [
            models.Index(fields=["organization", "office", "publication_date"]),
            models.Index(fields=["organization", "office", "process_cnj"]),
            models.Index(fields=["source", "source_id"]),
            models.Index(fields=["content_hash"]),
        ]
        verbose_name = "Publicação Oficial"
        verbose_name_plural = "Publicações Oficiais"
        ordering = ["-publication_date", "-import_date"]
    
    def __str__(self):
        return f"[{self.get_source_display()}] {self.publication_date} - {self.process_cnj or 'Sem CNJ'}"
    
    def save(self, *args, **kwargs):
        # Gera hash do conteúdo para idempotência
        if not self.content_hash:
            content = f"{self.source}:{self.raw_text}:{self.publication_date}"
            self.content_hash = hashlib.sha256(content.encode()).hexdigest()
        super().save(*args, **kwargs)
    
    @property
    def text_preview(self):
        """Preview curto do texto"""
        if len(self.raw_text) > 200:
            return self.raw_text[:200] + "..."
        return self.raw_text
    
    @property
    def has_process(self):
        """Verifica se tem CNJ"""
        return bool(self.process_cnj)


class JudicialEvent(OrganizationScopedModel):
    """
    INTERPRETAÇÃO JURÍDICA - EDITÁVEL
    Representa o efeito jurídico da publicação no workflow do escritório.
    Pode ser editado, ter status alterado, responsável mudado, etc.
    """
    
    TYPE_CHOICES = [
        ("citacao", "Citação"),
        ("intimacao", "Intimação"),
        ("sentenca", "Sentença"),
        ("acordao", "Acórdão"),
        ("decisao", "Decisão Interlocutória"),
        ("despacho", "Despacho"),
        ("edital", "Edital"),
        ("other", "Outro"),
    ]
    
    STATUS_CHOICES = [
        ("new", "Nova"),
        ("assigned", "Atribuída"),
        ("in_progress", "Em Andamento"),
        ("resolved", "Resolvida"),
        ("archived", "Arquivada"),
    ]
    
    URGENCY_CHOICES = [
        ("critical", "Crítica"),   # < 3 dias
        ("urgent", "Urgente"),     # 3-7 dias
        ("normal", "Normal"),      # > 7 dias
    ]
    
    # Vinculação com publicação oficial
    publication = models.ForeignKey(
        Publication,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name="Publicação Oficial"
    )
    
    # Interpretação jurídica
    event_type = models.CharField("Tipo de Evento", max_length=20, choices=TYPE_CHOICES)
    status = models.CharField("Status", max_length=20, choices=STATUS_CHOICES, default="new")
    urgency = models.CharField("Urgência", max_length=20, choices=URGENCY_CHOICES, default="normal")
    
    # Vinculações
    process = models.ForeignKey(
        "processes.Process",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="judicial_events",
        verbose_name="Processo Vinculado"
    )
    
    # Prazo calculado (referência ao Deadline criado)
    deadline = models.ForeignKey(
        "deadlines.Deadline",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="judicial_events",
        verbose_name="Prazo Derivado"
    )
    
    # Responsável
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_events",
        verbose_name="Responsável"
    )
    
    # Observações internas (editável)
    notes = models.TextField("Observações Internas", blank=True)
    
    # Datas de workflow
    assigned_at = models.DateTimeField("Atribuído em", null=True, blank=True)
    resolved_at = models.DateTimeField("Resolvido em", null=True, blank=True)
    
    objects = OrganizationScopedManager()
    
    class Meta:
        indexes = [
            models.Index(fields=["organization", "office", "status"]),
            models.Index(fields=["organization", "office", "urgency"]),
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["process"]),
        ]
        verbose_name = "Evento Jurídico"
        verbose_name_plural = "Eventos Jurídicos"
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.publication.process_cnj or 'Sem processo'}"
    
    @property
    def is_overdue(self):
        """Verifica se o prazo está vencido"""
        if not self.deadline:
            return False
        from django.utils import timezone
        return self.deadline.due_date < timezone.now().date()
    
    @property
    def days_until_deadline(self):
        """Dias até o vencimento"""
        if not self.deadline:
            return None
        from django.utils import timezone
        delta = self.deadline.due_date - timezone.now().date()
        return delta.days


class PublicationRule(OrganizationScopedModel):
    """
    REGRAS DE PRAZO CONFIGURÁVEIS
    NÃO hardcoded! Permite ajustes por área, tribunal, etc.
    """
    
    event_type = models.CharField(
        "Tipo de Evento",
        max_length=20,
        choices=JudicialEvent.TYPE_CHOICES
    )
    
    description = models.CharField("Descrição", max_length=255)
    base_legal = models.TextField("Base Legal", blank=True, help_text="CPC, CLT, etc")
    
    # Cálculo de prazo
    days = models.PositiveIntegerField("Dias", validators=[MinValueValidator(1)])
    business_days = models.BooleanField("Dias Úteis", default=True)
    
    # Configurações
    auto_create_deadline = models.BooleanField("Criar Prazo Automaticamente", default=True)
    auto_urgency = models.CharField(
        "Urgência Automática",
        max_length=20,
        choices=JudicialEvent.URGENCY_CHOICES,
        default="normal"
    )
    
    # Controle
    is_active = models.BooleanField("Ativa", default=True)
    priority = models.PositiveIntegerField("Prioridade", default=0, help_text="Maior número = maior prioridade")
    
    objects = OrganizationScopedManager()
    
    class Meta:
        indexes = [
            models.Index(fields=["organization", "office", "event_type", "is_active"]),
        ]
        verbose_name = "Regra de Prazo"
        verbose_name_plural = "Regras de Prazo"
        ordering = ["-priority", "event_type"]
    
    def __str__(self):
        dias_tipo = "úteis" if self.business_days else "corridos"
        return f"{self.get_event_type_display()} → {self.days} dias {dias_tipo}"


class PublicationImport(OrganizationScopedModel):
    """
    LOG DE IMPORTAÇÕES
    Rastreabilidade completa de todas as importações.
    """
    
    SOURCE_CHOICES = Publication.SOURCE_CHOICES
    
    STATUS_CHOICES = [
        ("processing", "Processando"),
        ("success", "Sucesso"),
        ("partial", "Parcial (com erros)"),
        ("failed", "Falhou"),
    ]
    
    source = models.CharField("Fonte", max_length=20, choices=SOURCE_CHOICES)
    status = models.CharField("Status", max_length=20, choices=STATUS_CHOICES, default="processing")
    
    # Contadores
    total_found = models.PositiveIntegerField("Total Encontrado", default=0)
    total_imported = models.PositiveIntegerField("Total Importado", default=0)
    total_duplicates = models.PositiveIntegerField("Duplicados (ignorados)", default=0)
    total_errors = models.PositiveIntegerField("Erros", default=0)
    
    # Filtros aplicados
    filters_applied = models.JSONField("Filtros Aplicados", default=dict, blank=True)
    
    # Logs
    error_log = models.TextField("Log de Erros", blank=True)
    summary = models.TextField("Resumo", blank=True)
    
    # Arquivo importado
    source_file = models.FileField(
        "Arquivo Fonte",
        upload_to="publications/imports/%Y/%m/",
        null=True,
        blank=True
    )
    
    # Controle
    started_at = models.DateTimeField("Iniciado em", auto_now_add=True)
    finished_at = models.DateTimeField("Finalizado em", null=True, blank=True)
    imported_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="publication_imports"
    )
    
    objects = OrganizationScopedManager()
    
    class Meta:
        verbose_name = "Importação de Publicações"
        verbose_name_plural = "Importações de Publicações"
        ordering = ["-started_at"]
    
    def __str__(self):
        return f"[{self.get_source_display()}] {self.started_at.strftime('%d/%m/%Y %H:%M')} - {self.get_status_display()}"
    
    @property
    def success_rate(self):
        """Taxa de sucesso"""
        if self.total_found == 0:
            return 0
        return round((self.total_imported / self.total_found) * 100, 1)


class PublicationFilter(OrganizationScopedModel):
    """
    FILTROS/KEYWORDS SIMPLIFICADOS (MVP)
    Matching primário por CNJ, secundário por OAB/CNPJ/CPF
    """
    
    TYPE_CHOICES = [
        ("cnj", "Número CNJ"),
        ("oab", "OAB"),
        ("cpf", "CPF"),
        ("cnpj", "CNPJ"),
        ("keyword", "Palavra-chave (auxiliar)"),
    ]
    
    filter_type = models.CharField("Tipo", max_length=20, choices=TYPE_CHOICES)
    value = models.CharField("Valor", max_length=255)
    description = models.CharField("Descrição", max_length=255, blank=True)
    
    is_active = models.BooleanField("Ativo", default=True)
    case_sensitive = models.BooleanField("Case Sensitive", default=False)
    
    # Estatísticas
    match_count = models.PositiveIntegerField("Matches", default=0)
    last_matched_at = models.DateTimeField("Último Match", null=True, blank=True)
    
    objects = OrganizationScopedManager()
    
    class Meta:
        indexes = [
            models.Index(fields=["organization", "office", "filter_type", "is_active"]),
        ]
        verbose_name = "Filtro de Publicação"
        verbose_name_plural = "Filtros de Publicações"
        ordering = ["filter_type", "value"]
    
    def __str__(self):
        return f"{self.get_filter_type_display()}: {self.value}"