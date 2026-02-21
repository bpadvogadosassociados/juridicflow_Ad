"""
Endpoints JSON do Portal — busca global, notificações.
"""
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.customers.models import Customer
from apps.processes.models import Process
from apps.deadlines.models import Deadline
from apps.documents.models import Document
from apps.portal.models import Notification
from apps.portal.decorators import require_portal_json


# ==================== BUSCA GLOBAL ====================

@require_portal_json()
def global_search(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})

    office = request.office
    org = request.organization
    results = []

    processes = Process.objects.filter(
        organization=org, office=office
    ).filter(Q(number__icontains=q) | Q(subject__icontains=q))[:5]
    for p in processes:
        results.append({"type": "process", "id": p.id, "title": p.number,
                        "subtitle": p.subject or "", "url": f"/app/processos/{p.id}/"})

    customers = Customer.objects.filter(
        organization=org, office=office, is_deleted=False
    ).filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(document__icontains=q))[:5]
    for c in customers:
        results.append({"type": "customer", "id": c.id, "title": c.name,
                        "subtitle": c.email or c.phone or "", "url": f"/app/contatos/{c.id}/"})

    deadlines = Deadline.objects.filter(
        organization=org, office=office
    ).filter(Q(title__icontains=q) | Q(description__icontains=q))[:5]
    for d in deadlines:
        results.append({"type": "deadline", "id": d.id, "title": d.title,
                        "subtitle": d.due_date.isoformat() if d.due_date else "", "url": "/app/prazos/"})

    documents = Document.objects.filter(
        organization=org, office=office
    ).filter(Q(title__icontains=q) | Q(description__icontains=q))[:5]
    for doc in documents:
        results.append({"type": "document", "id": doc.id, "title": doc.title,
                        "subtitle": doc.category or "", "url": f"/app/documentos/{doc.id}/"})

    return JsonResponse({"results": results})


# ==================== NOTIFICAÇÕES ====================

@require_portal_json()
def notifications_json(request):
    notifications = Notification.objects.filter(
        organization=request.organization,
        office=request.office,
        user=request.user,
    ).order_by("-created_at")[:20]

    icon_map = {
        "deadline": "fas fa-clock text-warning",
        "task": "fas fa-tasks text-info",
        "publication": "fas fa-newspaper text-primary",
        "warning": "fas fa-exclamation-triangle text-warning",
        "success": "fas fa-check-circle text-success",
        "error": "fas fa-times-circle text-danger",
        "info": "fas fa-info-circle text-info",
    }

    data = [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "icon": icon_map.get(n.type, "fas fa-bell text-muted"),
            "is_read": n.is_read,
            "url": n.url or "",
            "when": _time_ago(n.created_at),
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]
    unread = Notification.objects.filter(
        organization=request.organization,
        office=request.office,
        user=request.user,
        is_read=False,
    ).count()

    return JsonResponse({"items": data, "unread_count": unread})


@require_portal_json()
@require_http_methods(["POST"])
def notification_mark_read(request, notif_id):
    Notification.objects.filter(
        id=notif_id, user=request.user,
        organization=request.organization, office=request.office
    ).update(is_read=True)
    unread = Notification.objects.filter(
        user=request.user, organization=request.organization,
        office=request.office, is_read=False
    ).count()
    return JsonResponse({"ok": True, "unread_count": unread})


@require_portal_json()
@require_http_methods(["POST"])
def notification_mark_all_read(request):
    Notification.objects.filter(
        user=request.user, organization=request.organization,
        office=request.office, is_read=False
    ).update(is_read=True)
    return JsonResponse({"ok": True, "unread_count": 0})


def _time_ago(dt):
    from django.utils import timezone
    import math
    diff = timezone.now() - dt
    secs = int(diff.total_seconds())
    if secs < 60:
        return "agora"
    elif secs < 3600:
        return f"{secs // 60}min atrás"
    elif secs < 86400:
        return f"{secs // 3600}h atrás"
    else:
        return f"{secs // 86400}d atrás"
