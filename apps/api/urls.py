from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    # Auth
    LoginView, MeView, MembershipsView, OfficesView, PermissionsView,
    # Customers
    CustomerViewSet,
    # Processes
    ProcessViewSet,
    # Deadlines
    DeadlineViewSet,
    # Documents
    DocumentViewSet,
    # Finance
    FeeAgreementViewSet, InvoiceViewSet, PaymentViewSet,
    ExpenseViewSet, ProposalViewSet,
    # Kanban
    KanbanBoardView, KanbanColumnViewSet, KanbanCardViewSet,
    # Calendar
    CalendarEntryViewSet, CalendarTemplateViewSet,
    # Tasks
    TaskViewSet,
    # Notifications
    NotificationListView, NotificationMarkReadView,
    # Search & Dashboard
    GlobalSearchView, DashboardView,
)

# ── Activity (Atividade / Auditoria) ─────────────────────────────────────────
from apps.activity.views import (
    ActivityListView, ActivityDetailView,
    ActivitySummaryView, ActivityExportView,
)

# ── Team Management ───────────────────────────────────────────────────────────
from apps.team.views import (
    TeamMembersView, TeamMemberDetailView,
    LocalRoleListView, LocalRoleDetailView,
    PermissionGroupsView,
)

router = DefaultRouter()

# Core resources
router.register(r"customers",          CustomerViewSet,     basename="customers")
router.register(r"processes",          ProcessViewSet,      basename="processes")
router.register(r"deadlines",          DeadlineViewSet,     basename="deadlines")
router.register(r"documents",          DocumentViewSet,     basename="documents")

# Finance
router.register(r"finance/agreements", FeeAgreementViewSet, basename="agreements")
router.register(r"finance/invoices",   InvoiceViewSet,      basename="invoices")
router.register(r"finance/payments",   PaymentViewSet,      basename="payments")
router.register(r"finance/expenses",   ExpenseViewSet,      basename="expenses")
router.register(r"finance/proposals",  ProposalViewSet,     basename="proposals")

# Kanban
router.register(r"kanban/columns",     KanbanColumnViewSet, basename="kanban-columns")
router.register(r"kanban/cards",       KanbanCardViewSet,   basename="kanban-cards")

# Calendar
router.register(r"calendar/entries",   CalendarEntryViewSet,   basename="calendar-entries")
router.register(r"calendar/templates", CalendarTemplateViewSet, basename="calendar-templates")

# Tasks
router.register(r"tasks",              TaskViewSet,         basename="tasks")


urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────
    path("auth/login/",          LoginView.as_view(),          name="api-login"),
    path("auth/token/refresh/",  TokenRefreshView.as_view(),   name="token-refresh"),
    path("auth/token/verify/",   TokenVerifyView.as_view(),    name="token-verify"),
    path("auth/me/",             MeView.as_view(),              name="api-me"),
    path("auth/memberships/",    MembershipsView.as_view(),     name="api-memberships"),
    path("auth/permissions/",    PermissionsView.as_view(),     name="api-permissions"),

    # ── Org ───────────────────────────────────────────────────────────────
    path("org/offices/",         OfficesView.as_view(),         name="api-offices"),

    # ── Kanban board (singleton por office) ────────────────────────────
    path("kanban/board/",        KanbanBoardView.as_view(),     name="kanban-board"),

    # ── Notifications ─────────────────────────────────────────────────
    path("notifications/",           NotificationListView.as_view(),              name="notifications-list"),
    path("notifications/read-all/",  NotificationMarkReadView.as_view(),          name="notifications-read-all"),
    path("notifications/<int:notif_id>/read/", NotificationMarkReadView.as_view(), name="notification-read"),

    # ── Search & Dashboard ────────────────────────────────────────────
    path("search/",              GlobalSearchView.as_view(),    name="api-search"),
    path("dashboard/",           DashboardView.as_view(),       name="api-dashboard"),

    # ── Activity (Atividade / Auditoria) ─────────────────────────────
    path("activity/",            ActivityListView.as_view(),    name="activity-list"),
    path("activity/summary/",    ActivitySummaryView.as_view(), name="activity-summary"),
    path("activity/export/",     ActivityExportView.as_view(),  name="activity-export"),
    path("activity/<int:event_id>/", ActivityDetailView.as_view(), name="activity-detail"),

    # ── Team Management ───────────────────────────────────────────────
    path("team/members/",              TeamMembersView.as_view(),         name="team-members"),
    path("team/members/<int:pk>/",     TeamMemberDetailView.as_view(),    name="team-member-detail"),
    path("team/local-roles/",          LocalRoleListView.as_view(),       name="team-local-roles"),
    path("team/local-roles/<int:pk>/", LocalRoleDetailView.as_view(),     name="team-local-role-detail"),
    path("team/groups/",               PermissionGroupsView.as_view(),    name="team-groups"),

    # ── Router (todos os ViewSets) ────────────────────────────────────
    path("", include(router.urls)),
]
