from django.db import models
from apps.shared.models import OrganizationScopedModel
from apps.shared.managers import OrganizationScopedManager

class FeeAgreement(OrganizationScopedModel):
    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE, related_name="fee_agreements")
    process = models.ForeignKey("processes.Process", on_delete=models.SET_NULL, null=True, blank=True, related_name="fee_agreements")
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    billing_type = models.CharField(max_length=20, default="one_time")
    notes = models.TextField(blank=True)

    objects = OrganizationScopedManager()

    class Meta:
        verbose_name = "Contrato de honorários"
        verbose_name_plural = "Contratos de honorários"

class Invoice(OrganizationScopedModel):
    agreement = models.ForeignKey(FeeAgreement, on_delete=models.CASCADE, related_name="invoices")
    issue_date = models.DateField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, default="open")

    objects = OrganizationScopedManager()

    class Meta:
        verbose_name = "Fatura"
        verbose_name_plural = "Faturas"

class Payment(OrganizationScopedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    paid_at = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=30, default="pix")

    objects = OrganizationScopedManager()

class Expense(OrganizationScopedModel):
    title = models.CharField(max_length=255)
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    notes = models.TextField(blank=True)

    objects = OrganizationScopedManager()
