"""
Dashboard principal do portal — usa cache para métricas.
"""
from django.shortcuts import render

from apps.processes.models import Process
from apps.portal.decorators import require_portal_access
from apps.portal.cache import get_dashboard_counts


@require_portal_access()
def dashboard(request):
    office = request.office

    # Métricas cacheadas (5 min TTL)
    counts = get_dashboard_counts(office)

    latest_processes = Process.objects.filter(
        organization=request.organization,
        office=office,
    ).order_by("-created_at")[:5]

    return render(request, "portal/dashboard.html", {
        "counts": counts,
        "latest_processes": latest_processes,
        "active_page": "dashboard",
    })