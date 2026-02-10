"""
Endpoints JSON do Portal — busca global, notificações.
"""
from django.db.models import Q
from django.http import JsonResponse

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

    # Processos
    processes = Process.objects.filter(
        organization=org, office=office
    ).filter(
        Q(number__icontains=q) | Q(subject__icontains=q)
    )[:5]
    for p in processes:
        results.append({
            "type": "process",
            "id": p.id,
            "title": p.number,
            "subtitle": p.subject or "",
            "url": f"/app/processos/{p.id}/",
        })

    # Contatos
    customers = Customer.objects.filter(
        organization=org, office=office, is_deleted=False
    ).filter(
        Q(name__icontains=q) | Q(email__icontains=q) | Q(document__icontains=q)
    )[:5]
    for c in customers:
        results.append({
            "type": "customer",
            "id": c.id,
            "title": c.name,
            "subtitle": c.email or c.phone or "",
            "url": f"/app/contatos/{c.id}/",
        })

    # Prazos
    deadlines = Deadline.objects.filter(
        organization=org, office=office
    ).filter(
        Q(title__icontains=q) | Q(description__icontains=q)
    )[:5]
    for d in deadlines:
        results.append({
            "type": "deadline",
            "id": d.id,
            "title": d.title,
            "subtitle": d.due_date.isoformat() if d.due_date else "",
            "url": f"/app/prazos/",
        })

    # Documentos
    documents = Document.objects.filter(
        organization=org, office=office
    ).filter(
        Q(title__icontains=q) | Q(description__icontains=q)
    )[:5]
    for doc in documents:
        results.append({
            "type": "document",
            "id": doc.id,
            "title": doc.title,
            "subtitle": doc.category or "",
            "url": f"/app/documentos/{doc.id}/",
        })

    return JsonResponse({"results": results})


# ==================== NOTIFICAÇÕES ====================

@require_portal_json()
def notifications_json(request):
    notifications = Notification.objects.filter(
        organization=request.organization,
        office=request.office,
        user=request.user,
    ).order_by("-created_at")[:20]

    data = [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "is_read": n.is_read,
            "url": n.url or "",
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

    return JsonResponse({"notifications": data, "unread_count": unread})