from __future__ import annotations
from django.conf import settings
from django.db import models
from django.utils import timezone

class OfficePreference(models.Model):
    THEME_CHOICES = [
        ("default", "Padrão (Dark)"),
        ("dark", "Dark"),
        ("light", "Claro"),
    ]
    office = models.OneToOneField("offices.Office", on_delete=models.CASCADE, related_name="preference")
    theme = models.CharField(max_length=16, choices=THEME_CHOICES, default="default")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferências: {self.office.name}"

class ActivityLog(models.Model):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="activity_logs")
    office = models.ForeignKey("offices.Office", on_delete=models.CASCADE, related_name="activity_logs")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs")
    verb = models.CharField(max_length=64)  # ex: created_process
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

class SupportTicket(models.Model):
    STATUS_CHOICES = [
        ("open", "Aberto"),
        ("in_progress", "Em andamento"),
        ("closed", "Fechado"),
    ]
    TARGET_CHOICES = [
        ("office_admin", "Chefe do Escritório"),
        ("org_admin", "Admin da Organização"),
        ("platform_admin", "Admin da Plataforma"),
    ]

    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="support_tickets")
    office = models.ForeignKey("offices.Office", on_delete=models.CASCADE, related_name="support_tickets")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_tickets")
    target = models.CharField(max_length=32, choices=TARGET_CHOICES)
    subject = models.CharField(max_length=120)
    message = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="open")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.subject}"

class CalendarEventTemplate(models.Model):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="calendar_templates")
    office = models.ForeignKey("offices.Office", on_delete=models.CASCADE, related_name="calendar_templates")
    title = models.CharField(max_length=120)
    color = models.CharField(max_length=24, default="#3c8dbc")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("office", "title"),)
        ordering = ["title"]

class CalendarEntry(models.Model):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="calendar_entries")
    office = models.ForeignKey("offices.Office", on_delete=models.CASCADE, related_name="calendar_entries")
    title = models.CharField(max_length=120)
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    all_day = models.BooleanField(default=False)
    color = models.CharField(max_length=24, default="#3c8dbc")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="calendar_entries")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start"]

class KanbanBoard(models.Model):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="kanban_boards")
    office = models.OneToOneField("offices.Office", on_delete=models.CASCADE, related_name="kanban_board")
    title = models.CharField(max_length=120, default="Atividades")

    def __str__(self):
        return f"{self.office.name} - {self.title}"

class KanbanColumn(models.Model):
    board = models.ForeignKey(KanbanBoard, on_delete=models.CASCADE, related_name="columns")
    title = models.CharField(max_length=120)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        unique_together = (("board", "title"),)

class KanbanCard(models.Model):
    board = models.ForeignKey(KanbanBoard, on_delete=models.CASCADE, related_name="cards")
    column = models.ForeignKey(KanbanColumn, on_delete=models.CASCADE, related_name="cards")
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=120)
    body_md = models.TextField(blank=True, default="")
    order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="kanban_cards")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["board", "number"], name="uniq_card_number_per_board"),
            models.UniqueConstraint(fields=["board", "title"], name="uniq_card_title_per_board"),
        ]

    def save(self, *args, **kwargs):
        if self.column_id and not self.board_id:
            self.board_id = self.column.board_id
        super().save(*args, **kwargs)

class ChatThread(models.Model):
    TYPE_CHOICES = [
        ("direct", "Direto"),
        ("group", "Grupo"),
    ]
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="chat_threads")
    office = models.ForeignKey("offices.Office", on_delete=models.CASCADE, related_name="chat_threads")
    type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    title = models.CharField(max_length=120, blank=True, default="")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="chat_threads_created")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

class ChatMember(models.Model):
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_memberships")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("thread", "user"),)

class ChatMessage(models.Model):
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="chat_messages")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
