from django.db import models
from django.core.validators import FileExtensionValidator
from apps.shared.models import OrganizationScopedModel
from apps.shared.managers import OrganizationScopedManager
import os

class Document(OrganizationScopedModel):
    """Documento do escritório"""
    
    CATEGORY_CHOICES = [
        ("contract", "Contrato"),
        ("petition", "Petição"),
        ("decision", "Decisão/Sentença"),
        ("power_of_attorney", "Procuração"),
        ("certificate", "Certidão"),
        ("minutes", "Ata"),
        ("opinion", "Parecer"),
        ("appeal", "Recurso"),
        ("evidence", "Prova"),
        ("correspondence", "Correspondência"),
        ("internal", "Documento Interno"),
        ("other", "Outro"),
    ]
    
    STATUS_CHOICES = [
        ("draft", "Rascunho"),
        ("review", "Em Revisão"),
        ("approved", "Aprovado"),
        ("signed", "Assinado"),
        ("filed", "Protocolado"),
        ("archived", "Arquivado"),
    ]
    
    # Dados básicos
    title = models.CharField("Título", max_length=255)
    description = models.TextField("Descrição", blank=True)
    category = models.CharField("Categoria", max_length=50, choices=CATEGORY_CHOICES, default="other")
    status = models.CharField("Status", max_length=20, choices=STATUS_CHOICES, default="draft")
    
    # Arquivo
    file = models.FileField(
        "Arquivo",
        upload_to="documents/%Y/%m/",
        validators=[FileExtensionValidator(
            allowed_extensions=['pdf', 'doc', 'docx', 'txt', 'odt', 'rtf', 
                              'jpg', 'jpeg', 'png', 'xlsx', 'xls', 'csv']
        )]
    )
    file_size = models.BigIntegerField("Tamanho (bytes)", default=0)
    file_extension = models.CharField("Extensão", max_length=10, blank=True)
    
    # Metadata
    tags = models.CharField(
        "Tags", 
        max_length=500, 
        blank=True,
        help_text="Tags separadas por vírgula"
    )
    
    # Vinculações
    process = models.ForeignKey(
        "processes.Process",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
        verbose_name="Processo"
    )
    
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="process_documents",
        verbose_name="Cliente"
    )
    
    # Controle
    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents_uploaded",
        verbose_name="Enviado por"
    )
    
    is_confidential = models.BooleanField("Confidencial", default=False)
    is_template = models.BooleanField("Modelo/Template", default=False)
    
    # Datas
    document_date = models.DateField("Data do Documento", null=True, blank=True)
    expiry_date = models.DateField("Data de Validade", null=True, blank=True)
    
    objects = OrganizationScopedManager()

    class Meta:
        indexes = [
            models.Index(fields=["organization", "office", "title"]),
            models.Index(fields=["organization", "office", "category"]),
            models.Index(fields=["organization", "office", "status"]),
            models.Index(fields=["process"]),
            models.Index(fields=["customer"]),
        ]
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            self.file_extension = os.path.splitext(self.file.name)[1][1:].lower()
        super().save(*args, **kwargs)
    
    @property
    def filename(self):
        if not self.file:
            return ""
        return os.path.basename(self.file.name)

    @property
    def file_size_mb(self):
        """Tamanho em MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def tag_list(self):
        """Lista de tags"""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]
    
    @property
    def has_versions(self):
        """Verifica se tem versões"""
        return self.versions.exists()
    
    @property
    def latest_version(self):
        """Última versão"""
        return self.versions.order_by("-version_number").first()
    
    @property
    def version_count(self):
        """Quantidade de versões"""
        return self.versions.count()
    
    @property
    def is_expired(self):
        """Verifica se está vencido"""
        if not self.expiry_date:
            return False
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()


class DocumentVersion(models.Model):
    """Versionamento de documentos"""
    
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="versions",
        verbose_name="Documento"
    )
    
    version_number = models.PositiveIntegerField("Versão", blank=True, null=True)
    file = models.FileField("Arquivo", upload_to="documents/versions/%Y/%m/")
    file_size = models.BigIntegerField("Tamanho (bytes)", default=0)
    
    changes_description = models.TextField("Descrição das Alterações", blank=True)
    
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="document_versions_created",
        verbose_name="Criado por"
    )
    created_at = models.DateTimeField("Criado em", auto_now_add=True)

    class Meta:
        ordering = ["-version_number"]
        unique_together = [("document", "version_number")]
        verbose_name = "Versão do Documento"
        verbose_name_plural = "Versões do Documento"

    def __str__(self):
        return f"{self.document.title} v{self.version_number}"
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
    
    @property
    def file_size_mb(self):
        """Tamanho em MB"""
        return round(self.file_size / (1024 * 1024), 2)


class DocumentShare(OrganizationScopedModel):
    """Compartilhamento de documentos"""
    
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="shares",
        verbose_name="Documento"
    )
    
    shared_with = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="shared_documents",
        verbose_name="Compartilhado com"
    )
    
    shared_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="documents_shared_by_me",
        verbose_name="Compartilhado por"
    )
    
    can_edit = models.BooleanField("Pode Editar", default=False)
    can_download = models.BooleanField("Pode Baixar", default=True)
    
    expires_at = models.DateTimeField("Expira em", null=True, blank=True)
    access_count = models.PositiveIntegerField("Acessos", default=0)
    last_accessed_at = models.DateTimeField("Último acesso", null=True, blank=True)
    
    class Meta:
        unique_together = [("document", "shared_with")]
        verbose_name = "Compartilhamento"
        verbose_name_plural = "Compartilhamentos"
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.document.title} → {self.shared_with.email}"
    
    @property
    def is_expired(self):
        """Verifica se o compartilhamento expirou"""
        if not self.expires_at:
            return False
        from django.utils import timezone
        return self.expires_at < timezone.now()


class DocumentComment(OrganizationScopedModel):
    """Comentários em documentos"""
    
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Documento"
    )
    
    author = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="document_comments",
        verbose_name="Autor"
    )
    
    comment = models.TextField("Comentário")
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Comentário"
        verbose_name_plural = "Comentários"
    
    def __str__(self):
        return f"{self.author.email} em {self.document.title}"


class Folder(OrganizationScopedModel):
    """Pastas para organização de documentos"""
    
    name = models.CharField("Nome", max_length=255)
    description = models.TextField("Descrição", blank=True)
    
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subfolders",
        verbose_name="Pasta pai"
    )
    
    color = models.CharField("Cor", max_length=7, default="#007bff")
    icon = models.CharField("Ícone", max_length=50, default="fas fa-folder")
    
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="folders_created",
        verbose_name="Criado por"
    )
    
    class Meta:
        unique_together = [("organization", "office", "name", "parent")]
        verbose_name = "Pasta"
        verbose_name_plural = "Pastas"
        ordering = ["name"]
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} / {self.name}"
        return self.name
    
    @property
    def full_path(self):
        """Caminho completo da pasta"""
        path = [self.name]
        parent = self.parent
        while parent:
            path.insert(0, parent.name)
            parent = parent.parent
        return " / ".join(path)
    
    @property
    def document_count(self):
        """Quantidade de documentos na pasta"""
        return self.documents.count()


class DocumentFolder(models.Model):
    """Relacionamento Documento-Pasta (muitos para muitos)"""
    
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="folder_links"
    )
    
    folder = models.ForeignKey(
        Folder,
        on_delete=models.CASCADE,
        related_name="documents"
    )
    
    added_at = models.DateTimeField("Adicionado em", auto_now_add=True)
    added_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="document_folder_adds"
    )
    
    class Meta:
        unique_together = [("document", "folder")]
        verbose_name = "Documento na Pasta"
        verbose_name_plural = "Documentos nas Pastas"
    
    def __str__(self):
        return f"{self.document.title} em {self.folder.name}"