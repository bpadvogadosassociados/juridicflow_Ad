"""
Model Tag reutilizável — substitui o campo CSV tags em Customer e Document.

Uso:
    class Customer(OrganizationScopedModel):
        tags = models.ManyToManyField("core.Tag", blank=True, related_name="customers")

Migração:
    1. Adicione o app 'apps.core' ao INSTALLED_APPS
    2. Crie a migration: python manage.py makemigrations core
    3. Adicione M2M em Customer e Document (veja instruções abaixo)
    4. Rode o management command para migrar tags CSV → M2M
"""
from django.conf import settings
from django.db import models

from apps.organizations.models import Organization
from apps.offices.models import Office


class Tag(models.Model):
    """
    Tag normalizada com escopo por organization.
    
    Garante unicidade por (organization, slug) para evitar duplicatas
    como "VIP", "vip", "Vip".
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="tags",
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    color = models.CharField(max_length=7, blank=True, default="")  # hex: #FF5733

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "core"
        unique_together = [("organization", "slug")]
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization", "slug"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        # Normaliza nome: primeira letra maiúscula
        self.name = self.name.strip()
        super().save(*args, **kwargs)

    @classmethod
    def get_or_create_from_text(cls, organization, tag_text: str):
        """
        Cria ou busca tag a partir de texto livre.
        Retorna (tag, created).
        """
        from django.utils.text import slugify
        name = tag_text.strip()
        slug = slugify(name)
        if not slug:
            return None, False
        return cls.objects.get_or_create(
            organization=organization,
            slug=slug,
            defaults={"name": name},
        )