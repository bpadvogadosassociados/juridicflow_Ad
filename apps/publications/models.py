"""
MÓDULO PUBLICAÇÕES / ANDAMENTOS
================================
Gerencia publicações judiciais, eventos jurídicos e monitoramento de processos.

Integrações suportadas:
  - DataJud (CNJ) — metadados e movimentações via API pública
  - Comunica / PJe — download de cadernos diários compactados
  - DJEN — Diário Eletrônico Nacional
  - Manual — registro direto pelo usuário

Arquitetura de camadas:
  1. Publication        → dado oficial imutável (o que veio da fonte)
  2. JudicialEvent      → interpretação jurídica + workflow (o que o escritório faz)
  3. ProcessMonitoring  → qual processo monitorar e como
  4. PublicationRule    → regras de prazo configuráveis por tipo de evento
  5. PublicationFilter  → palavras-chave / CNJ / OAB para matching automático
  6. PublicationImport  → log rastreável de cada importação
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings

from apps.shared.models import OrganizationScopedModel
from apps.shared.managers import OrganizationScopedManager
import hashlib


# ═══════════════════════════════════════════════════════════════════════════════
# Publication — dado oficial, imutável
# ═══════════════════════════════════════════════════════════════════════════════

class Publication(OrganizationScopedModel):
    """
    Registro oficial da publicação/andamento exatamente como veio da fonte.
    NUNCA deve ser editado após criação (princípio de auditoria).
    """

    SOURCE_CHOICES = [
        ("datajud", "DataJud (CNJ)"),
        ("comunica", "Comunica API (PJe)"),
        ("djen", "DJEN — Diário Eletrônico Nacional"),
        ("tjsp", "TJSP"),
        ("tjrj", "TJRJ"),
        ("trf1", "TRF1"),
        ("trf2", "TRF2"),
        ("trf3", "TRF3"),
        ("trf4", "TRF4"),
        ("trf5", "TRF5"),
        ("manual", "Inserção Manual"),
        ("other", "Outro"),
    ]

    # Origem
    source = models.CharField("Fonte", max_length=20, choices=SOURCE_CHOICES, default="manual")
    source_id = models.CharField(
        "ID na Fonte", max_length=255, blank=True,
        help_text="ID único da publicação na fonte externa (idempotência)"
    )

    # Conteúdo oficial — imutável
    raw_text = models.TextField("Texto Bruto", help_text="Texto completo da publicação/andamento")
    content_hash = models.CharField(
        "Hash de Conteúdo", max_length=64,
        help_text="SHA-256 para deduplicação automática"
    )

    # Metadados
    publication_date = models.DateField("Data da Publicação")
    import_date = models.DateTimeField("Data de Importação", auto_now_add=True)

    # Número CNJ detectado automaticamente (via CNJMatcher)
    process_cnj = models.CharField(
        "Número CNJ", max_length=40, blank=True, db_index=True,
        help_text="Extraído automaticamente do texto"
    )

    # Processo vinculado (se encontrado na base)
    process = models.ForeignKey(
        "processes.Process",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="publications",
        verbose_name="Processo",
    )

    # Arquivo original (PDF do diário, ZIP do caderno, etc.)
    original_file = models.FileField(
        "Arquivo Original",
        upload_to="publications/%Y/%m/",
        null=True, blank=True,
    )

    # Metadados adicionais flexíveis (tribunal, órgão, classe, etc.)
    metadata = models.JSONField("Metadados", default=dict, blank=True)

    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="publications_imported",
    )

    objects = OrganizationScopedManager()

    class Meta:
        indexes = [
            models.Index(fields=["organization", "office", "publication_date"]),
            models.Index(fields=["organization", "office", "process_cnj"]),
            models.Index(fields=["organization", "office", "source"]),
            models.Index(fields=["source", "source_id"]),
            models.Index(fields=["content_hash"]),
        ]
        constraints = [
            # Deduplicação deve ser por tenant (organization + office), não global.
            models.UniqueConstraint(
                fields=["organization", "office", "content_hash"],
                name="uniq_publication_content_hash_per_tenant",
            ),
            # Idempotência por fonte: se source_id existir, ele deve ser único no tenant.
            models.UniqueConstraint(
                fields=["organization", "office", "source", "source_id"],
                condition=~models.Q(source_id=""),
                name="uniq_publication_source_id_per_tenant",
            ),
        ]
        verbose_name = "Publicação / Andamento"
        verbose_name_plural = "Publicações / Andamentos"
        ordering = ["-publication_date", "-import_date"]

    def __str__(self):
        return f"[{self.get_source_display()}] {self.publication_date} — {self.process_cnj or 'Sem CNJ'}"

    def save(self, *args, **kwargs):
        if not self.content_hash:
            content = f"{self.source}:{self.source_id}:{self.raw_text}:{self.publication_date}"
            self.content_hash = hashlib.sha256(content.encode()).hexdigest()
        super().save(*args, **kwargs)

    @property
    def text_preview(self):
        return self.raw_text[:300] + "…" if len(self.raw_text) > 300 else self.raw_text

    @property
    def has_process(self):
        return bool(self.process_id or self.process_cnj)


# ═══════════════════════════════════════════════════════════════════════════════
# JudicialEvent — interpretação jurídica + workflow
# ═══════════════════════════════════════════════════════════════════════════════

class JudicialEvent(OrganizationScopedModel):
    """
    Interpretação jurídica de uma Publication.
    Representa o efeito no workflow do escritório: o que fazer, quem faz, até quando.
    Diferente da Publication, pode ser editado (notas, status, responsável).
    """

    TYPE_CHOICES = [
        ("citacao", "Citação"),
        ("intimacao", "Intimação"),
        ("sentenca", "Sentença"),
        ("acordao", "Acórdão"),
        ("decisao", "Decisão Interlocutória"),
        ("despacho", "Despacho"),
        ("juntada", "Juntada"),
        ("audiencia", "Audiência"),
        ("peticao", "Petição"),
        ("edital", "Edital"),
        ("movimento", "Movimento Processual"),
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
        ("critical", "Crítica"),   # < 3 dias úteis
        ("urgent", "Urgente"),     # 3–7 dias
        ("normal", "Normal"),      # > 7 dias
    ]

    # Vínculo com o dado oficial
    publication = models.ForeignKey(
        Publication,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name="Publicação Oficial",
    )

    # Interpretação
    event_type = models.CharField("Tipo de Evento", max_length=20, choices=TYPE_CHOICES, default="movimento")
    status = models.CharField("Status", max_length=20, choices=STATUS_CHOICES, default="new")
    urgency = models.CharField("Urgência", max_length=20, choices=URGENCY_CHOICES, default="normal")

    # Vínculos
    process = models.ForeignKey(
        "processes.Process",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="judicial_events",
        verbose_name="Processo Vinculado",
    )
    deadline = models.ForeignKey(
        "deadlines.Deadline",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="judicial_events",
        verbose_name="Prazo Derivado",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="assigned_events",
        verbose_name="Responsável",
    )

    # Workflow
    notes = models.TextField("Observações Internas", blank=True)
    assigned_at = models.DateTimeField("Atribuído em", null=True, blank=True)
    resolved_at = models.DateTimeField("Resolvido em", null=True, blank=True)

    objects = OrganizationScopedManager()

    class Meta:
        indexes = [
            models.Index(fields=["organization", "office", "status"]),
            models.Index(fields=["organization", "office", "urgency"]),
            models.Index(fields=["organization", "office", "event_type"]),
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["process"]),
        ]
        verbose_name = "Evento Jurídico"
        verbose_name_plural = "Eventos Jurídicos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.publication.process_cnj or 'Sem CNJ'}"

    @property
    def is_overdue(self):
        if not self.deadline:
            return False
        from django.utils import timezone
        return self.deadline.due_date < timezone.now().date()

    @property
    def days_until_deadline(self):
        if not self.deadline:
            return None
        from django.utils import timezone
        return (self.deadline.due_date - timezone.now().date()).days


# ═══════════════════════════════════════════════════════════════════════════════
# ProcessMonitoring — qual processo monitorar e como
# ═══════════════════════════════════════════════════════════════════════════════

class ProcessMonitoring(OrganizationScopedModel):
    """
    Configura o monitoramento automático de um processo.

    Quando ativo, o sistema verifica diariamente as fontes configuradas
    (DataJud, Comunica, etc.) e cria Publications automaticamente quando
    encontra novidades relacionadas ao processo.

    O campo autocomplete_enabled controla se os dados encontrados nas APIs
    podem preencher automaticamente campos do processo (título, partes, etc.).
    """

    SOURCE_CHOICES = [
        ("datajud", "DataJud (CNJ)"),
        ("comunica", "Comunica API (PJe)"),
        ("djen", "DJEN"),
        ("all", "Todas as fontes"),
    ]

    process = models.OneToOneField(
        "processes.Process",
        on_delete=models.CASCADE,
        related_name="monitoring",
        verbose_name="Processo",
    )

    # O número CNJ é armazenado aqui para acesso rápido sem JOIN
    process_cnj = models.CharField("Número CNJ", max_length=40, db_index=True)

    # Fontes ativas de monitoramento
    sources = models.JSONField(
        "Fontes de Monitoramento",
        default=list,
        help_text='Ex: ["datajud", "comunica"]',
    )

    # Estado atual do processo (sincronizado com DataJud)
    tribunal = models.CharField("Tribunal", max_length=20, blank=True)
    tribunal_index = models.CharField(
        "Índice DataJud", max_length=20, blank=True,
        help_text="Ex: tjsp, trf3 — usado nas queries ao DataJud"
    )
    current_phase = models.CharField("Fase Atual", max_length=200, blank=True)

    # Controle de sync
    is_active = models.BooleanField("Ativo", default=True)
    autocomplete_enabled = models.BooleanField(
        "Autocompletar Processo", default=False,
        help_text="Permite que dados das APIs preencham campos do processo"
    )
    initial_sync_done = models.BooleanField("Sync Inicial Concluído", default=False)
    last_synced_at = models.DateTimeField("Última Sincronização", null=True, blank=True)

    # Cursores por fonte para paginação incremental
    sync_cursors = models.JSONField(
        "Cursores de Sync", default=dict, blank=True,
        help_text="Controla onde cada fonte parou (ex: {'datajud': '2026-01-15'})"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Ativado por",
    )

    objects = OrganizationScopedManager()

    class Meta:
        verbose_name = "Monitoramento de Processo"
        verbose_name_plural = "Monitoramentos"
        ordering = ["-created_at"]

    def __str__(self):
        status = "ativo" if self.is_active else "pausado"
        return f"Monitoramento [{status}]: {self.process_cnj}"


# ═══════════════════════════════════════════════════════════════════════════════
# PublicationRule — regras de prazo configuráveis
# ═══════════════════════════════════════════════════════════════════════════════

class PublicationRule(OrganizationScopedModel):
    """
    Define quanto tempo o escritório tem para responder a cada tipo de evento.
    Não hardcoded! Permite customização por área, tribunal, preferência do escritório.
    """

    event_type = models.CharField(
        "Tipo de Evento", max_length=20,
        choices=JudicialEvent.TYPE_CHOICES,
    )
    description = models.CharField("Descrição", max_length=255)
    base_legal = models.TextField(
        "Base Legal", blank=True,
        help_text="Ex: CPC art. 335 — 15 dias para contestar"
    )

    # Cálculo de prazo
    days = models.PositiveIntegerField("Dias", validators=[MinValueValidator(1)])
    business_days = models.BooleanField("Dias Úteis", default=True)

    # Automações
    auto_create_deadline = models.BooleanField("Criar Prazo Automaticamente", default=True)
    auto_urgency = models.CharField(
        "Urgência Automática", max_length=20,
        choices=JudicialEvent.URGENCY_CHOICES, default="normal",
    )

    is_active = models.BooleanField("Ativa", default=True)
    priority = models.PositiveIntegerField(
        "Prioridade", default=0,
        help_text="Maior número = maior prioridade quando houver múltiplas regras para o mesmo tipo"
    )

    objects = OrganizationScopedManager()

    class Meta:
        indexes = [
            models.Index(fields=["organization", "office", "event_type", "is_active"]),
        ]
        verbose_name = "Regra de Prazo"
        verbose_name_plural = "Regras de Prazo"
        ordering = ["-priority", "event_type"]

    def __str__(self):
        tipo = "úteis" if self.business_days else "corridos"
        return f"{self.get_event_type_display()} → {self.days} dias {tipo}"


# ═══════════════════════════════════════════════════════════════════════════════
# PublicationFilter — filtros para matching automático
# ═══════════════════════════════════════════════════════════════════════════════

class PublicationFilter(OrganizationScopedModel):
    """
    Define critérios para identificar publicações relevantes ao escritório.
    Matching primário: CNJ (exato). Secundário: OAB, CPF, CNPJ. Terciário: keyword.
    """

    TYPE_CHOICES = [
        ("cnj", "Número CNJ"),
        ("oab", "OAB"),
        ("cpf", "CPF"),
        ("cnpj", "CNPJ"),
        ("keyword", "Palavra-chave"),
    ]

    filter_type = models.CharField("Tipo de Filtro", max_length=20, choices=TYPE_CHOICES)
    value = models.CharField("Valor", max_length=255)
    description = models.CharField("Descrição", max_length=255, blank=True)

    # Vínculo opcional a um processo específico
    process = models.ForeignKey(
        "processes.Process",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="publication_filters",
        verbose_name="Processo",
    )

    is_active = models.BooleanField("Ativo", default=True)
    case_sensitive = models.BooleanField("Case Sensitive", default=False)

    # Estatísticas de uso
    match_count = models.PositiveIntegerField("Total de Matches", default=0)
    last_matched_at = models.DateTimeField("Último Match", null=True, blank=True)

    objects = OrganizationScopedManager()

    class Meta:
        indexes = [
            models.Index(fields=["organization", "office", "filter_type", "is_active"]),
            models.Index(fields=["organization", "office", "process"]),
        ]
        verbose_name = "Filtro de Publicação"
        verbose_name_plural = "Filtros de Publicações"
        ordering = ["filter_type", "value"]

    def __str__(self):
        return f"{self.get_filter_type_display()}: {self.value}"


# ═══════════════════════════════════════════════════════════════════════════════
# PublicationImport — log de importações
# ═══════════════════════════════════════════════════════════════════════════════

class PublicationImport(OrganizationScopedModel):
    """
    Rastreia cada rodada de importação: quando aconteceu, quantas publicações
    foram encontradas, quantas novas, duplicatas, erros.
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

    # Referência de data (para downloads de cadernos)
    reference_date = models.DateField("Data de Referência", null=True, blank=True)

    # Contadores
    total_found = models.PositiveIntegerField("Encontradas", default=0)
    total_imported = models.PositiveIntegerField("Importadas", default=0)
    total_duplicates = models.PositiveIntegerField("Duplicatas ignoradas", default=0)
    total_matched = models.PositiveIntegerField("Vinculadas a processos", default=0)
    total_errors = models.PositiveIntegerField("Erros", default=0)

    # Filtros usados
    filters_applied = models.JSONField("Filtros Aplicados", default=dict, blank=True)

    # Logs
    error_log = models.TextField("Log de Erros", blank=True)
    summary = models.TextField("Resumo", blank=True)

    # Arquivo-fonte (ZIP do caderno, etc.)
    source_file = models.FileField(
        "Arquivo Fonte",
        upload_to="publications/imports/%Y/%m/",
        null=True, blank=True,
    )

    started_at = models.DateTimeField("Iniciado em", auto_now_add=True)
    finished_at = models.DateTimeField("Finalizado em", null=True, blank=True)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="publication_imports_triggered",
        verbose_name="Disparado por",
    )

    objects = OrganizationScopedManager()

    class Meta:
        verbose_name = "Importação de Publicações"
        verbose_name_plural = "Importações de Publicações"
        ordering = ["-started_at"]

    def __str__(self):
        ts = self.started_at.strftime("%d/%m/%Y %H:%M")
        return f"[{self.get_source_display()}] {ts} — {self.get_status_display()}"

    @property
    def success_rate(self):
        if self.total_found == 0:
            return 0
        return round((self.total_imported / self.total_found) * 100, 1)

    @property
    def duration_seconds(self):
        if not self.finished_at:
            return None
        return (self.finished_at - self.started_at).seconds
