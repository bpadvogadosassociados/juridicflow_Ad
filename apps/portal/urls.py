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
    path("app/tarefas/", views.task_list, name="tarefas"),
    path("app/tarefas/kanban/", views.kanban, name="kanban"),    
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
    path("app/api/notifications/<int:notif_id>/read/", views.notification_mark_read, name="notification_mark_read"),
    path("app/api/notifications/read-all/", views.notification_mark_all_read, name="notification_mark_all_read"),
    path("app/api/chat/users/search/", views.chat_users_search, name="chat_users_search"),
    path("app/relatorios/", views.relatorios_dashboard, name="relatorios_dashboard"),
    path("app/relatorios/json/", views.relatorios_json, name="relatorios_json"),
    path("app/relatorios/export/", views.relatorios_export, name="relatorios_export"),

    # Calendar JSON
    path("app/api/calendar/events/", views.calendar_events_json, name="calendar_events_json"),
    path("app/api/calendar/events/create/", views.calendar_event_create, name="calendar_event_create"),
    path("app/api/calendar/events/update/<int:event_id>/", views.calendar_event_update, name="calendar_event_update"),
    path("app/api/calendar/events/delete/<int:event_id>/", views.calendar_event_delete, name="calendar_event_delete"),

    # Calendar templates (settings ERP)
    path("app/api/calendar/templates/list/", views.calendar_templates_list, name="calendar_templates_list"),
    path("app/api/calendar/templates/create/", views.calendar_template_create, name="calendar_template_create"),
    path("app/api/calendar/templates/delete/<int:template_id>/", views.calendar_template_delete, name="calendar_template_delete"),

    # Kanban JSON
    path("app/api/kanban/board/", views.kanban_board_json, name="kanban_board_json"),
    path("app/api/kanban/columns/create/", views.kanban_column_create, name="kanban_column_create"),
    path("app/api/kanban/columns/update/<int:column_id>/", views.kanban_column_update, name="kanban_column_update"),
    path("app/api/kanban/columns/delete/<int:column_id>/", views.kanban_column_delete, name="kanban_column_delete"),
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

    # Financeiro
    path("app/financeiro/", views.financeiro_dashboard, name="financeiro_dashboard"),
    path("app/financeiro/contratos/", views.financeiro_contratos, name="financeiro_contratos"),
    path("app/financeiro/contratos/novo/", views.financeiro_contrato_create, name="financeiro_contrato_create"),
    path("app/financeiro/contratos/<int:agreement_id>/", views.financeiro_contrato_detail, name="financeiro_contrato_detail"),
    path("app/financeiro/faturas/", views.financeiro_faturas, name="financeiro_faturas"),
    path("app/financeiro/faturas/create/", views.financeiro_fatura_create, name="financeiro_fatura_create"),
    path("app/financeiro/faturas/<int:invoice_id>/pagamento/", views.financeiro_fatura_registrar_pagamento, name="financeiro_fatura_registrar_pagamento"),
    path("app/financeiro/despesas/", views.financeiro_despesas, name="financeiro_despesas"),
    path("app/financeiro/despesas/create/", views.financeiro_despesa_create, name="financeiro_despesa_create"),
    path("app/financeiro/despesas/<int:expense_id>/update/", views.financeiro_despesa_update, name="financeiro_despesa_update"),
    path("app/financeiro/despesas/<int:expense_id>/delete/", views.financeiro_despesa_delete, name="financeiro_despesa_delete"),
    path("app/financeiro/despesas/<int:expense_id>/detail/", views.financeiro_despesa_detail, name="financeiro_despesa_detail"),

    # Documentos
    path("app/documentos/dashboard/", views.documentos_dashboard, name="documentos_dashboard"),
    path("app/documentos/", views.documentos, name="documentos"),
    path("app/documentos/upload/", views.documento_upload, name="documento_upload"),
    path("app/documentos/<int:document_id>/", views.documento_detail, name="documento_detail"),
    path("app/documentos/<int:document_id>/download/", views.documento_download, name="documento_download"),
    path("app/documentos/<int:document_id>/delete/", views.documento_delete, name="documento_delete"),
    path("app/documentos/<int:document_id>/version/", views.documento_version_create, name="documento_version_create"),
    path("app/documentos/version/<int:version_id>/download/", views.documento_version_download, name="documento_version_download"),
    path("app/documentos/<int:document_id>/share/", views.documento_share_create, name="documento_share_create"),
    path("app/documentos/share/<int:share_id>/delete/", views.documento_share_delete, name="documento_share_delete"),
    path("app/documentos/<int:document_id>/comment/", views.documento_comment_create, name="documento_comment_create"),
    path("app/pastas/", views.pastas, name="pastas"),
    path("app/pastas/create/", views.pasta_create, name="pasta_create"),
    path("app/pastas/<int:folder_id>/delete/", views.pasta_delete, name="pasta_delete"),

    # Publicações Judiciais
    path("app/publicacoes/", views.publicacoes, name="publicacoes"),
    path("app/publicacoes/dashboard/", views.publicacoes_dashboard, name="publicacoes_dashboard"),
    path("app/publicacoes/importar/", views.publicacao_import, name="publicacao_import"),
    path("app/publicacoes/<int:pub_id>/", views.publicacao_detail, name="publicacao_detail"),
    path("app/publicacoes/evento/<int:event_id>/assign/", views.evento_assign, name="evento_assign"),
    path("app/publicacoes/evento/<int:event_id>/status/", views.evento_status, name="evento_status"),
    path("app/publicacoes/regras/", views.publicacao_rules, name="publicacao_rules"),
    path("app/publicacoes/regras/create/", views.publicacao_rule_create, name="publicacao_rule_create"),
    path("app/publicacoes/filtros/", views.publicacao_filters, name="publicacao_filters"),
    path("app/publicacoes/filtros/create/", views.publicacao_filter_create, name="publicacao_filter_create"),

    # Processos — edit, partes, notas, prazos, docs
    path("app/processos/<int:process_id>/editar/", views.processo_edit, name="processo_edit"),
    path("app/processos/<int:process_id>/party/add/", views.processo_party_add, name="processo_party_add"),
    path("app/processos/<int:process_id>/party/<int:party_id>/remove/", views.processo_party_remove, name="processo_party_remove"),
    path("app/processos/<int:process_id>/note/add/", views.processo_note_add, name="processo_note_add"),
    path("app/processos/<int:process_id>/note/<int:note_id>/delete/", views.processo_note_delete, name="processo_note_delete"),
    path("app/processos/<int:process_id>/prazo/add/", views.processo_prazo_add, name="processo_prazo_add"),
    path("app/processos/<int:process_id>/prazo/<int:deadline_id>/complete/", views.processo_prazo_complete, name="processo_prazo_complete"),
    path("app/processos/<int:process_id>/documento/upload/", views.processo_documento_upload, name="processo_documento_upload"),
    path("app/api/processos/buscar-contatos/", views.processo_buscar_contatos, name="processo_buscar_contatos"),

    # Contatos — pipeline e relacionamentos
    path("app/contatos/pipeline/", views.contatos_pipeline, name="contatos_pipeline"),
    path("app/contatos/<int:customer_id>/pipeline/move/", views.contato_pipeline_move, name="contato_pipeline_move"),
    path("app/contatos/<int:customer_id>/next-action/", views.contato_next_action, name="contato_next_action"),
    path("app/contatos/<int:customer_id>/relationship/add/", views.contato_relationship_add, name="contato_relationship_add"),
    path("app/contatos/<int:customer_id>/relationship/<int:rel_id>/remove/", views.contato_relationship_remove, name="contato_relationship_remove"),
    path("app/contatos/<int:customer_id>/documento/upload/", views.contato_document_upload, name="contato_document_upload"),

    # Financeiro — Propostas
    path("app/financeiro/propostas/", views.financeiro_propostas, name="financeiro_propostas"),
    path("app/financeiro/propostas/nova/", views.financeiro_proposta_create, name="financeiro_proposta_create"),
    path("app/financeiro/propostas/<int:proposal_id>/", views.financeiro_proposta_detail, name="financeiro_proposta_detail"),
    path("app/financeiro/propostas/<int:proposal_id>/status/", views.financeiro_proposta_status, name="financeiro_proposta_status"),
    path("app/financeiro/propostas/<int:proposal_id>/converter/", views.financeiro_proposta_converter, name="financeiro_proposta_converter"),
]
