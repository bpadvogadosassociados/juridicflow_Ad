from django.urls import path
from .views import (
    # Feed principal
    JudicialEventFeedView,
    JudicialEventDetailView,
    JudicialEventMarkAllReadView,
    # Publicações brutas
    PublicationListCreateView,
    # Monitoramento
    ProcessMonitoringListCreateView,
    ProcessMonitoringDetailView,
    ProcessSyncView,
    ComunicaSyncView,
    # DataJud lookup
    DataJudLookupView,
    # Regras
    PublicationRuleListCreateView,
    PublicationRuleDetailView,
    # Filtros
    PublicationFilterListCreateView,
    PublicationFilterDetailView,
    # Importações
    PublicationImportListView,
)

app_name = "publications"

urlpatterns = [
    # ── Feed (andamentos – visão principal) ──────────────────────────────────
    path("feed/",                     JudicialEventFeedView.as_view(),      name="feed-list"),
    path("feed/<int:pk>/",            JudicialEventDetailView.as_view(),    name="feed-detail"),
    path("feed/mark-all-read/",       JudicialEventMarkAllReadView.as_view(), name="feed-mark-all"),

    # ── Publicações brutas ────────────────────────────────────────────────────
    path("raw/",                      PublicationListCreateView.as_view(),  name="raw-list"),

    # ── Monitoramento ─────────────────────────────────────────────────────────
    path("monitoring/",               ProcessMonitoringListCreateView.as_view(), name="monitoring-list"),
    path("monitoring/<int:pk>/",      ProcessMonitoringDetailView.as_view(),     name="monitoring-detail"),
    path("monitoring/<int:pk>/sync/", ProcessSyncView.as_view(),                 name="monitoring-sync"),

    # ── Sync Comunica (caderno diário) ────────────────────────────────────────
    path("sync-comunica/",            ComunicaSyncView.as_view(),           name="sync-comunica"),

    # ── DataJud lookup ────────────────────────────────────────────────────────
    path("datajud/",                  DataJudLookupView.as_view(),          name="datajud-lookup"),

    # ── Regras de prazo ───────────────────────────────────────────────────────
    path("rules/",                    PublicationRuleListCreateView.as_view(), name="rules-list"),
    path("rules/<int:pk>/",           PublicationRuleDetailView.as_view(),     name="rules-detail"),

    # ── Filtros de matching ───────────────────────────────────────────────────
    path("filters/",                  PublicationFilterListCreateView.as_view(), name="filters-list"),
    path("filters/<int:pk>/",         PublicationFilterDetailView.as_view(),     name="filters-detail"),

    # ── Log de importações ────────────────────────────────────────────────────
    path("imports/",                  PublicationImportListView.as_view(),   name="imports-list"),
]
