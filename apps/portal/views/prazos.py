"""
Views de Prazos (Deadlines).
CORRIGIDO: Removido created_by (não existe no model Deadline).
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods

from apps.deadlines.models import Deadline
from apps.processes.models import Process
from apps.portal.decorators import require_portal_access, require_portal_json
from apps.portal.views._helpers import parse_json_body, log_activity

from apps.portal.permissions import require_role, require_action
from apps.portal.audit import audited


# ==================== LISTA ====================

@require_portal_access()
def prazos(request):
    search = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")
    priority = request.GET.get("priority", "")

    qs = Deadline.objects.filter(
        organization=request.organization,
        office=request.office,
    ).select_related("responsible").order_by("due_date")

    if search:
        qs = qs.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)
    if priority:
        qs = qs.filter(priority=priority)

    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    deadlines = paginator.get_page(request.GET.get("page", 1))

    today = timezone.now().date()
    overdue_count = Deadline.objects.filter(
        office=request.office, status="pending", due_date__lt=today
    ).count()
    upcoming_count = Deadline.objects.filter(
        office=request.office,
        status="pending",
        due_date__gte=today,
        due_date__lte=today + timedelta(days=7),
    ).count()

    return render(request, "portal/prazos.html", {
        "deadlines": deadlines,
        "search": search,
        "status_filter": status_filter,
        "priority": priority,
        "overdue_count": overdue_count,
        "upcoming_count": upcoming_count,
        "type_choices": Deadline.TYPE_CHOICES,
        "priority_choices": Deadline.PRIORITY_CHOICES,
        "active_page": "prazos",
    })


# ==================== CALENDAR VIEW ====================

@require_portal_access()
def prazos_calendar(request):
    return render(request, "portal/prazos_calendar.html", {
        "active_page": "prazos",
    })


@require_portal_json()
def prazos_calendar_json(request):
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")

    qs = Deadline.objects.filter(
        organization=request.organization,
        office=request.office,
    )
    if start:
        qs = qs.filter(due_date__gte=parse_date(start[:10]))
    if end:
        qs = qs.filter(due_date__lte=parse_date(end[:10]))

    priority_colors = {
        "urgent": "#dc3545",
        "high": "#fd7e14",
        "medium": "#ffc107",
        "low": "#28a745",
    }

    events = []
    for d in qs:
        events.append({
            "id": d.id,
            "title": d.title,
            "start": d.due_date.isoformat() if d.due_date else None,
            "color": priority_colors.get(d.priority, "#6c757d"),
            "extendedProps": {
                "status": d.status if hasattr(d, "status") else "",
                "priority": d.priority,
            },
        })
    return JsonResponse(events, safe=False)


# ==================== CRUD JSON ====================

@require_portal_json()
@require_role("lawyer")
@require_http_methods(["POST"])
def prazo_create(request):
    payload = parse_json_body(request)
    title = payload.get("title", "").strip()
    if not title:
        return JsonResponse({"error": "Título obrigatório"}, status=400)

    due_date = parse_date(payload.get("due_date", ""))
    if not due_date:
        return JsonResponse({"error": "Data de vencimento obrigatória"}, status=400)

    # Vincula ao processo se informado
    content_type = None
    object_id = None
    process_id = payload.get("process_id")
    if process_id:
        try:
            process = Process.objects.get(
                id=process_id,
                organization=request.organization,
                office=request.office,
            )
            content_type = ContentType.objects.get_for_model(Process)
            object_id = process.id
        except Process.DoesNotExist:
            return JsonResponse({"error": "Processo não encontrado"}, status=404)

    # Responsável
    responsible = None
    responsible_id = payload.get("responsible_id")
    if responsible_id:
        from apps.accounts.models import User
        try:
            responsible = User.objects.get(id=responsible_id)
        except User.DoesNotExist:
            pass

    deadline = Deadline.objects.create(
        organization=request.organization,
        office=request.office,
        title=title,
        description=payload.get("description", "").strip(),
        due_date=due_date,
        type=payload.get("type", "legal"),
        priority=payload.get("priority", "medium"),
        status="pending",
        content_type=content_type,
        object_id=object_id,
        responsible=responsible,
    )
    log_activity(request, "deadline_create", f"Prazo criado: {deadline.title}")

    return JsonResponse({
        "ok": True,
        "deadline": {
            "id": deadline.id,
            "title": deadline.title,
            "due_date": deadline.due_date.isoformat(),
            "priority": deadline.priority,
            "status": deadline.status,
        },
    })


@require_portal_json()
@require_role("lawyer")
@require_http_methods(["POST"])
def prazo_update(request, prazo_id):
    deadline = get_object_or_404(
        Deadline,
        id=prazo_id,
        organization=request.organization,
        office=request.office,
    )
    payload = parse_json_body(request)

    if "title" in payload:
        deadline.title = payload["title"].strip()
    if "description" in payload:
        deadline.description = payload["description"].strip()
    if "due_date" in payload:
        deadline.due_date = parse_date(payload["due_date"]) or deadline.due_date
    if "type" in payload:
        deadline.type = payload["type"]
    if "priority" in payload:
        deadline.priority = payload["priority"]
    if "status" in payload:
        deadline.status = payload["status"]

    # Atualiza vinculação com processo
    if "process_id" in payload:
        process_id = payload["process_id"]
        if process_id:
            try:
                process = Process.objects.get(id=process_id, office=request.office)
                deadline.content_type = ContentType.objects.get_for_model(Process)
                deadline.object_id = process.id
            except Process.DoesNotExist:
                pass
        else:
            deadline.content_type = None
            deadline.object_id = None

    # Atualiza responsável
    if "responsible_id" in payload:
        responsible_id = payload["responsible_id"]
        if responsible_id:
            from apps.accounts.models import User
            try:
                deadline.responsible = User.objects.get(id=responsible_id)
            except User.DoesNotExist:
                pass
        else:
            deadline.responsible = None

    deadline.save()
    log_activity(request, "deadline_update", f"Prazo atualizado: {deadline.title}")

    return JsonResponse({
        "ok": True,
        "deadline": {
            "id": deadline.id,
            "title": deadline.title,
            "due_date": deadline.due_date.isoformat() if deadline.due_date else None,
            "priority": deadline.priority,
            "status": deadline.status,
        },
    })


@require_portal_json()
@require_role("manager")
@audited(action="delete", model_name="Deadline")
@require_http_methods(["POST"])
def prazo_delete(request, prazo_id):
    deadline = get_object_or_404(
        Deadline,
        id=prazo_id,
        organization=request.organization,
        office=request.office,
    )
    title = deadline.title
    deadline.delete()
    log_activity(request, "deadline_delete", f"Prazo deletado: {title}")
    return JsonResponse({"ok": True})


@require_portal_json()
def prazo_detail(request, prazo_id):
    deadline = get_object_or_404(
        Deadline,
        id=prazo_id,
        organization=request.organization,
        office=request.office,
    )

    # Retorna process_id se vinculado
    process_id = None
    if deadline.content_type and deadline.object_id:
        ct_process = ContentType.objects.get_for_model(Process)
        if deadline.content_type == ct_process:
            process_id = deadline.object_id

    return JsonResponse({
        "id": deadline.id,
        "title": deadline.title,
        "description": deadline.description,
        "due_date": deadline.due_date.isoformat() if deadline.due_date else None,
        "type": deadline.type,
        "priority": deadline.priority,
        "status": deadline.status if hasattr(deadline, "status") else "",
        "responsible_id": deadline.responsible_id,
        "process_id": process_id,
        "created_at": deadline.created_at.isoformat(),
    })