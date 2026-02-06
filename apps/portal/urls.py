from django.urls import path
from . import views

app_name = "portal"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("portal/login/", views.portal_login, name="login"),
    path("portal/logout/", views.portal_logout, name="logout"),
    path("portal/set-office/<int:office_id>/", views.set_office, name="set_office"),

    path("app/", views.dashboard, name="dashboard"),
    path("app/agenda/", views.agenda, name="agenda"),
    path("app/tarefas/", views.kanban, name="kanban"),
    path("app/processos/", views.processos, name="processos"),
    path("app/processos/novo/", views.processo_create, name="processo_create"),
    path("app/processos/<int:process_id>/", views.processo_detail, name="processo_detail"),
    path("app/processos/<int:process_id>/delete/", views.processo_delete, name="processo_delete"),
    path("app/suporte/novo/", views.support_new, name="support_new"),
    path("app/suporte/", views.support_inbox, name="support_inbox"),
    path("app/configuracoes/", views.settings_view, name="settings"),

    # JSON endpoints (portal)
    path("app/api/search/", views.global_search, name="global_search"),
    path("app/api/notifications/", views.notifications_json, name="notifications_json"),

    # Calendar JSON
    path("app/api/calendar/events/", views.calendar_events_json, name="calendar_events_json"),
    path("app/api/calendar/events/create/", views.calendar_event_create, name="calendar_event_create"),
    path("app/api/calendar/events/update/<int:event_id>/", views.calendar_event_update, name="calendar_event_update"),
    path("app/api/calendar/events/delete/<int:event_id>/", views.calendar_event_delete, name="calendar_event_delete"),

    # Calendar templates (settings ERP)
    path("app/api/calendar/templates/list/", views.calendar_templates_list, name="calendar_templates_list"),
    path("app/api/calendar/templates/create/", views.calendar_template_create, name="calendar_template_create"),
    path("app/api/calendar/templates/delete/<int:tpl_id>/", views.calendar_template_delete, name="calendar_template_delete"),

    # Kanban JSON
    path("app/api/kanban/board/", views.kanban_board_json, name="kanban_board_json"),
    path("app/api/kanban/columns/create/", views.kanban_column_create, name="kanban_column_create"),
    path("app/api/kanban/columns/update/<int:col_id>/", views.kanban_column_update, name="kanban_column_update"),
    path("app/api/kanban/columns/delete/<int:col_id>/", views.kanban_column_delete, name="kanban_column_delete"),
    path("app/api/kanban/cards/create/", views.kanban_card_create, name="kanban_card_create"),
    path("app/api/kanban/cards/update/<int:card_id>/", views.kanban_card_update, name="kanban_card_update"),
    path("app/api/kanban/cards/move/", views.kanban_card_move, name="kanban_card_move"),
    path("app/api/kanban/cards/detail/<int:card_id>/", views.kanban_card_detail, name="kanban_card_detail"),

    # Chat
    path("app/api/chat/threads/", views.chat_threads, name="chat_threads"),
    path("app/api/chat/thread/create/", views.chat_thread_create, name="chat_thread_create"),
    path("app/api/chat/thread/<int:thread_id>/messages/", views.chat_messages, name="chat_messages"),
    path("app/api/chat/thread/<int:thread_id>/send/", views.chat_send, name="chat_send"),

    # Prazos
    path("app/prazos/", views.prazos, name="prazos"),
    path("app/prazos/create/", views.prazo_create, name="prazo_create"),
    path("app/prazos/<int:prazo_id>/detail/", views.prazo_detail, name="prazo_detail"),
    path("app/prazos/<int:prazo_id>/update/", views.prazo_update, name="prazo_update"),
    path("app/prazos/<int:prazo_id>/delete/", views.prazo_delete, name="prazo_delete"),
    path("app/prazos/calendar/", views.prazos_calendar, name="prazos_calendar"),
    path("app/prazos/calendar/json/", views.prazos_calendar_json, name="prazos_calendar_json"),

# Contatos/CRM
    path("app/contatos/dashboard/", views.contatos_dashboard, name="contatos_dashboard"),
    path("app/contatos/", views.contatos, name="contatos"),
    path("app/contatos/novo/", views.contato_create, name="contato_create"),
    path("app/contatos/<int:customer_id>/", views.contato_detail, name="contato_detail"),
    path("app/contatos/<int:customer_id>/editar/", views.contato_edit, name="contato_edit"),
    path("app/contatos/<int:customer_id>/delete/", views.contato_delete, name="contato_delete"),
    path("app/contatos/<int:customer_id>/interaction/", views.contato_interaction_create, name="contato_interaction_create"),
    path("app/contatos/export/", views.contatos_export, name="contatos_export"),
    path("app/contatos/import/", views.contatos_import, name="contatos_import"),
]
