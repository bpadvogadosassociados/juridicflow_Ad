"""
apps.portal.views — pacote refatorado.

Re-exporta todas as views para manter compatibilidade com urls.py.
"""

# Auth
from apps.portal.views.auth import (
    landing,
    portal_login,
    portal_logout,
    set_office,
)

# Dashboard
from apps.portal.views.dashboard import dashboard

# Processos
from apps.portal.views.processos import (
    processos,
    processo_create,
    processo_detail,
    processo_delete,
)

# Contatos / CRM
from apps.portal.views.contatos import (
    contatos_dashboard,
    contatos,
    contato_create,
    contato_detail,
    contato_edit,
    contato_delete,
    contato_interaction_create,
    contatos_export,
    contatos_import,
)

# Prazos
from apps.portal.views.prazos import (
    prazos,
    prazos_calendar,
    prazos_calendar_json,
    prazo_create,
    prazo_update,
    prazo_delete,
    prazo_detail,
)

# Tarefas / Kanban
from apps.portal.views.tarefas import (
    kanban,
    task_list,
    kanban_board_json,
    kanban_column_create,
    kanban_column_update,
    kanban_column_delete,
    kanban_card_create,
    kanban_card_update,
    kanban_card_move,
    kanban_card_detail,
)

# Financeiro
from apps.portal.views.financeiro import (
    financeiro_dashboard,
    financeiro_contratos,
    financeiro_contrato_create,
    financeiro_contrato_detail,
    financeiro_faturas,
    financeiro_fatura_create,
    financeiro_fatura_registrar_pagamento,
    financeiro_despesas,
    financeiro_despesa_create,
    financeiro_despesa_update,
    financeiro_despesa_delete,
    financeiro_despesa_detail,
)

# Documentos
from apps.portal.views.documentos import (
    documentos_dashboard,
    documentos,
    documento_upload,
    documento_detail,
    documento_download,
    documento_version_download,
    documento_delete,
    documento_version_create,
    documento_share_create,
    documento_share_delete,
    documento_comment_create,
    pastas,
    pasta_create,
    pasta_delete,
)

# Publicações
from apps.portal.views.publicacoes import (
    publicacoes_dashboard,
    publicacoes,
    publicacao_detail,
    publicacao_import,
    publicacao_rules,
    publicacao_rule_create,
    publicacao_filters,
    publicacao_filter_create,
    evento_assign,
    evento_status,
)

# Agenda
from apps.portal.views.agenda import (
    agenda,
    calendar_events_json,
    calendar_event_create,
    calendar_event_update,
    calendar_event_delete,
    calendar_templates_list,
    calendar_template_create,
    calendar_template_delete,
)

# Suporte / Chat
from apps.portal.views.suporte import (
    support_new,
    support_inbox,
    chat_threads,
    chat_thread_create,
    chat_messages,
    chat_send,
)

# Configurações
from apps.portal.views.configuracoes import settings_view

# API (busca global, notificações)
from apps.portal.views._api import (
    global_search,
    notifications_json,
)

from apps.portal.permissions import require_role, require_action
from apps.portal.audit import audited
# Processos — novos endpoints
from apps.portal.views.processos import (
    processo_edit,
    processo_party_add,
    processo_party_remove,
    processo_note_add,
    processo_note_delete,
    processo_prazo_add,
    processo_prazo_complete,
    processo_documento_upload,
    processo_buscar_contatos,
)

# Contatos — pipeline e relacionamentos
from apps.portal.views.contatos import (
    contatos_pipeline,
    contato_pipeline_move,
    contato_next_action,
    contato_relationship_add,
    contato_relationship_remove,
    contato_document_upload,
)

# Financeiro — propostas
from apps.portal.views.financeiro import (
    financeiro_propostas,
    financeiro_proposta_create,
    financeiro_proposta_detail,
    financeiro_proposta_status,
    financeiro_proposta_converter,
)

# Notificações (novos endpoints)
from apps.portal.views._api import (
    notification_mark_read,
    notification_mark_all_read,
)

# Chat — users search
from apps.portal.views.suporte import chat_users_search

# Relatórios
from apps.portal.views.relatorios import (
    relatorios_dashboard,
    relatorios_json,
    relatorios_export,
)
