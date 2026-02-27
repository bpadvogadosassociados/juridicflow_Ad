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
    description = models.TextField("Descrição", blank=True, default="")
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
    description = models.CharField(max_length=120, blank=True, verbose_name="Descrição curta")
    required_fields = models.JSONField(default=list, blank=True, verbose_name="Campos obrigatórios")
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

class Notification(models.Model):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="notifications")
    office = models.ForeignKey("offices.Office", on_delete=models.CASCADE, related_name="notifications")

    """Notificações do portal para usuários."""

    TYPE_CHOICES = [
        ("info", "Informação"),
        ("warning", "Aviso"),
        ("success", "Sucesso"),
        ("error", "Erro"),
        ("deadline", "Prazo"),
        ("publication", "Publicação"),
        ("task", "Tarefa"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portal_notifications",
    )
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True, default="")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="info")
    is_read = models.BooleanField(default=False)
    url = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.type}] {self.title} → {self.user}"


class Task(models.Model):
    """
    Tarefa com campos completos — substitui KanbanCard como fonte de verdade.
    O KanbanCard continua existindo para posição visual no board,
    mas agora aponta para Task via OneToOne.
    """

    PRIORITY_CHOICES = [
        ("low", "Baixa"),
        ("medium", "Média"),
        ("high", "Alta"),
        ("critical", "Crítica"),
    ]

    STATUS_CHOICES = [
        ("backlog", "Backlog"),
        ("todo", "A Fazer"),
        ("in_progress", "Em Andamento"),
        ("review", "Em Revisão"),
        ("done", "Concluído"),
        ("cancelled", "Cancelado"),
    ]

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="tasks"
    )
    office = models.ForeignKey(
        "offices.Office", on_delete=models.CASCADE, related_name="tasks"
    )

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="todo")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium")

    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        blank=True, 
        related_name="assignee_tasks"
    )

    # Atribuição
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="assigned_tasks",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="created_tasks",
    )

    # Datas
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Vinculações opcionais
    process = models.ForeignKey(
        "processes.Process",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="tasks",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="tasks",
    )

    # Tags (usa o model Tag do core — adicione apps.core ao INSTALLED_APPS primeiro)
    # Descomente quando o app core estiver instalado:
    # labels = models.ManyToManyField("core.Tag", blank=True, related_name="tasks")

    # Kanban visual
    kanban_card = models.OneToOneField(
        "portal.KanbanCard",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="task",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["office", "status"]),
            models.Index(fields=["office", "assigned_to"]),
            models.Index(fields=["office", "due_date"]),
            models.Index(fields=["office", "priority", "status"]),
        ]

    def __str__(self):
        return self.title

    def mark_done(self):
        self.status = "done"
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])

    @property
    def is_overdue(self):
        if not self.due_date or self.status in ("done", "cancelled"):
            return False
        return self.due_date < timezone.now().date()
