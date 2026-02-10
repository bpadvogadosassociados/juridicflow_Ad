"""
Dashboard principal do portal.
"""
from django.shortcuts import render

from apps.customers.models import Customer
from apps.memberships.models import Membership
from apps.processes.models import Process
from apps.portal.models import KanbanBoard, KanbanColumn, KanbanCard
from apps.portal.decorators import require_portal_access


@require_portal_access()
def dashboard(request):
    office = request.office
    org = request.organization

    customers_count = Customer.objects.for_request(request).filter(office=office).count()
    processes_count = Process.objects.for_request(request).filter(office=office).count()
    team_count = Membership.objects.filter(organization=org, office=office, is_active=True).count()

    board, _ = KanbanBoard.objects.get_or_create(organization=org, office=office)
    done_cols = KanbanColumn.objects.filter(
        board=board, title__iregex=r"^(done|conclu[ií]do|finalizado)$"
    )
    pending_tasks = KanbanCard.objects.filter(board=board).exclude(column__in=done_cols).count()

    counts = {
        "customers": customers_count,
        "processes": processes_count,
        "team": team_count,
        "pending_tasks": pending_tasks,
    }
    latest_processes = Process.objects.for_request(request).filter(office=office).order_by("-id")[:5]

    return render(request, "portal/dashboard.html", {
        "counts": counts,
        "latest_processes": latest_processes,
        "active_page": "dashboard",
    })