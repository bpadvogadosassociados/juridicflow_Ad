
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class PermissionGroupProfile(models.Model):
    """Metadados dos grupos globais (auth.Group)."""
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="profile")
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_assignable_by_org_admin = models.BooleanField(default=True)
    is_assignable_by_tech_director = models.BooleanField(default=True)
    is_internal_only = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "group__name")
        verbose_name = "Perfil de Grupo de Permissão"
        verbose_name_plural = "Perfis de Grupos de Permissão"

    def __str__(self):
        return self.group.name


class LocalRole(models.Model):
    """Função local (cliente) que combina grupos globais."""
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="local_roles")
    office = models.ForeignKey("offices.Office", on_delete=models.CASCADE, null=True, blank=True, related_name="local_roles")
    name = models.CharField("Nome", max_length=100)
    description = models.TextField("Descrição", blank=True)
    groups = models.ManyToManyField(Group, blank=True, related_name="local_roles")
    is_active = models.BooleanField("Ativa", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Função Local"
        verbose_name_plural = "Funções Locais"
        constraints = [
            models.UniqueConstraint(fields=["organization", "office", "name"], name="uniq_local_role_name_per_scope"),
        ]

    def clean(self):
        super().clean()
        if self.office_id and self.organization_id and self.office.organization_id != self.organization_id:
            raise ValidationError({"office": "O escritório precisa pertencer à organização da função."})

    def __str__(self):
        scope = self.office.name if self.office_id else "ORG"
        return f"{self.organization.name} / {scope} / {self.name}"


class Membership(models.Model):
    ROLE_CHOICES = [
        ("org_admin", "Admin da Organização"),
        ("office_admin", "Admin do Escritório"),
        ("lawyer", "Advogado"),
        ("staff", "Equipe"),
        ("finance", "Financeiro"),
    ]

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="memberships")
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="memberships")
    office = models.ForeignKey("offices.Office", on_delete=models.CASCADE, null=True, blank=True, related_name="memberships")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, help_text="Label legado (não controla autorização).")
    local_role = models.ForeignKey(
        LocalRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memberships",
        help_text="Função local usada como preset de grupos (opcional).",
    )
    groups = models.ManyToManyField(Group, blank=True, related_name="memberships")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Vínculo"
        verbose_name_plural = "Vínculos"
        constraints = [
            models.UniqueConstraint(fields=["user", "organization", "office"], condition=Q(office__isnull=False), name="uniq_membership_user_org_office_nonnull"),
            models.UniqueConstraint(fields=["user", "organization"], condition=Q(office__isnull=True), name="uniq_membership_user_org_orglevel"),
        ]

    def clean(self):
        super().clean()
        if self.office_id and self.organization_id and self.office.organization_id != self.organization_id:
            raise ValidationError({"office": "O escritório precisa pertencer à organização do vínculo."})
        if self.user_id and self.organization_id:
            conflict = (Membership.objects.filter(user_id=self.user_id).exclude(pk=self.pk).exclude(organization_id=self.organization_id).exists())
            if conflict:
                raise ValidationError({"organization": "Usuário já pertence a outra organização."})
        if self.local_role_id:
            if self.local_role.organization_id != self.organization_id:
                raise ValidationError({"local_role": "Função local pertence a outra organização."})
            if self.local_role.office_id and self.local_role.office_id != self.office_id:
                raise ValidationError({"local_role": "Função local é específica de outro escritório."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def sync_groups_from_local_role(self):
        if not self.pk:
            raise ValueError("Membership precisa estar salvo para sincronizar grupos.")
        if self.local_role_id:
            self.groups.set(self.local_role.groups.all())
        else:
            self.groups.clear()

    def get_all_permissions(self):
        perms = set()
        for group in self.groups.all():
            for perm in group.permissions.all():
                perms.add(f"{perm.content_type.app_label}.{perm.codename}")
        return perms

    def has_perm(self, perm):
        return perm in self.get_all_permissions()

    def has_any_perm(self, *perms):
        current = self.get_all_permissions()
        return any(p in current for p in perms)

    def has_all_perms(self, *perms):
        current = self.get_all_permissions()
        return all(p in current for p in perms)

    def __str__(self):
        scope = self.office.name if self.office_id else "ORG"
        return f"{self.user.email} @ {self.organization.name} ({scope}) [{self.role}]"
