from django.db import models

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
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("user", "organization", "office", "role"),)
        verbose_name = "Vínculo"
        verbose_name_plural = "Vínculos"

    def __str__(self):
        scope = self.office.name if self.office_id else "ORG"
        return f"{self.user.email} @ {self.organization.name} ({scope}) [{self.role}]"
