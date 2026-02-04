from django.db import models
from apps.shared.models import OrganizationScopedModel
from apps.shared.managers import OrganizationScopedManager

class Document(OrganizationScopedModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="documents/")
    uploaded_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)

    objects = OrganizationScopedManager()

    class Meta:
        indexes = [models.Index(fields=["organization", "office", "title"])]
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"

    def __str__(self):
        return self.title

class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    file = models.FileField(upload_to="documents/versions/")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.document.title} v{self.id}"
