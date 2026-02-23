"""
Views de Agenda / Calendário — CORRIGIDO para os models reais.

Campos reais:
  CalendarEntry: organization, office, title, start, end, all_day, color, created_by, created_at
    (SEM: description, location, event_type)
  CalendarEventTemplate: organization, office, title, color, is_active, created_at
    (SEM: name, description, duration_minutes, event_type)
"""
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.http import require_http_methods

from apps.portal.models import CalendarEntry, CalendarEventTemplate
from apps.portal.decorators import require_portal_access, require_portal_json
from apps.portal.views._helpers import parse_json_body, log_activity

from apps.shared.permissions import require_role, require_action
from apps.portal.audit import audited

# ==================== HTML ====================

@require_portal_access()
def agenda(request):
    return render(request, "portal/agenda.html", {
        "active_page": "agenda",
    })


# ==================== EVENTS JSON ====================

@require_portal_json()
def calendar_events_json(request):
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")

    qs = CalendarEntry.objects.filter(
        organization=request.organization,
        office=request.office,
    )
    if start:
        qs = qs.filter(start__gte=parse_date(start[:10]))
    if end:
        qs = qs.filter(start__lte=parse_date(end[:10]))

    events = []
    for entry in qs:
        events.append({
            "id": entry.id,
            "title": entry.title,
            "start": entry.start.isoformat() if entry.start else None,
            "end": entry.end.isoformat() if entry.end else None,
            "allDay": entry.all_day,
            "color": entry.color or "#3788d8",
        })

    return JsonResponse(events, safe=False)


@require_portal_json()
@require_role("assistant")
@require_http_methods(["POST"])
def calendar_event_create(request):
    payload = parse_json_body(request)
    title = payload.get("title", "").strip()
    if not title:
        return JsonResponse({"error": "Título obrigatório"}, status=400)

    start_str = payload.get("start", "")
    if not start_str:
        return JsonResponse({"error": "Data de início obrigatória"}, status=400)

    start = parse_datetime(start_str) or parse_date(start_str)
    end_str = payload.get("end", "")
    end = parse_datetime(end_str) if end_str else None

    entry = CalendarEntry.objects.create(
        organization=request.organization,
        office=request.office,
        title=title,
        start=start,
        end=end,
        all_day=payload.get("all_day", False),
        color=payload.get("color", "#3c8dbc"),
        created_by=request.user,
    )
    log_activity(request, "calendar_create", f"Evento: {entry.title}")
    return JsonResponse({
        "ok": True,
        "event": {
            "id": entry.id,
            "title": entry.title,
            "start": entry.start.isoformat() if entry.start else None,
        },
    })


@require_portal_json()
@require_role("assistant")
@require_http_methods(["POST"])
def calendar_event_update(request, event_id):
    entry = get_object_or_404(
        CalendarEntry,
        id=event_id,
        organization=request.organization,
        office=request.office,
    )
    payload = parse_json_body(request)

    if "title" in payload:
        entry.title = payload["title"].strip()
    if "start" in payload:
        entry.start = parse_datetime(payload["start"]) or parse_date(payload["start"])
    if "end" in payload:
        end_str = payload["end"]
        entry.end = parse_datetime(end_str) if end_str else None
    if "all_day" in payload:
        entry.all_day = payload["all_day"]
    if "color" in payload:
        entry.color = payload["color"]

    entry.save()
    return JsonResponse({"ok": True})


@require_portal_json()
@require_role("lawyer")
@require_http_methods(["POST"])
def calendar_event_delete(request, event_id):
    entry = get_object_or_404(
        CalendarEntry,
        id=event_id,
        organization=request.organization,
        office=request.office,
    )
    title = entry.title
    entry.delete()
    log_activity(request, "calendar_delete", f"Evento deletado: {title}")
    return JsonResponse({"ok": True})


# ==================== TEMPLATES ====================

@require_portal_json()
def calendar_templates_list(request):
    templates = CalendarEventTemplate.objects.filter(
        organization=request.organization,
        office=request.office,
        is_active=True,
    ).order_by("title")

    data = [
        {
            "id": t.id,
            "title": t.title,
            "color": t.color or "#3c8dbc",
        }
        for t in templates
    ]
    return JsonResponse({"templates": data})


@require_portal_json()
@require_role("manager")
@require_http_methods(["POST"])
def calendar_template_create(request):
    payload = parse_json_body(request)
    title = payload.get("title", "").strip()
    if not title:
        return JsonResponse({"error": "Título obrigatório"}, status=400)

    template = CalendarEventTemplate.objects.create(
        organization=request.organization,
        office=request.office,
        title=title,
        color=payload.get("color", "#3c8dbc"),
        is_active=True,
    )
    return JsonResponse({"ok": True, "template_id": template.id})


@require_portal_json()
@require_role("manager")
@require_http_methods(["POST"])
def calendar_template_delete(request, template_id):
    template = get_object_or_404(
        CalendarEventTemplate,
        id=template_id,
        organization=request.organization,
        office=request.office,
    )
    template.delete()
    return JsonResponse({"ok": True})