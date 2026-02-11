from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.shared.models import OrganizationScopedModel
from apps.shared.managers import OrganizationScopedManager


class Deadline(OrganizationScopedModel):
    TYPE_CHOICES = [
        ("legal", "Prazo Legal"),
        ("hearing", "Audiência"),
        ("meeting", "Reunião"),
        ("task", "Tarefa"),
        ("other", "Outro"),
    ]
    PRIORITY_CHOICES = [
        ("low", "Baixa"),
        ("medium", "Média"),
        ("high", "Alta"),
        ("urgent", "Urgente"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pendente"),
        ("completed", "Concluído"),
        ("overdue", "Vencido"),
        ("cancelled", "Cancelado"),
    ]

    title = models.CharField(max_length=255)
    due_date = models.DateField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="legal")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    description = models.TextField(blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey("content_type", "object_id")

    responsible = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)

    objects = OrganizationScopedManager()

    class Meta:
        indexes = [
            models.Index(fields=["organization", "office", "due_date"]),
            models.Index(fields=["organization", "office", "status"]),
        ]
        verbose_name = "Prazo"
        verbose_name_plural = "Prazos"

    def __str__(self):
        return f"{self.title} ({self.due_date})"
