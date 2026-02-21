from django.contrib import admin
from .models import (
    OfficePreference, ActivityLog, SupportTicket,
    CalendarEventTemplate, CalendarEntry,
    KanbanBoard, KanbanColumn, KanbanCard,
    ChatThread, ChatMember, ChatMessage,
)

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("id","created_at","organization","office","target","status","subject","created_by")
    list_filter = ("target","status","created_at")
    search_fields = ("subject","message","created_by__email")

#admin.site.register(OfficePreference)
#admin.site.register(ActivityLog)
#admin.site.register(CalendarEventTemplate)
#admin.site.register(CalendarEntry)
#admin.site.register(KanbanBoard)
#admin.site.register(KanbanColumn)
#admin.site.register(KanbanCard)
#admin.site.register(ChatThread)
#admin.site.register(ChatMember)
#admin.site.register(ChatMessage)

