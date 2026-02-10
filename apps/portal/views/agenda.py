"""
Views de Agenda / Calendário.
"""
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.http import require_http_methods

from apps.portal.models import CalendarEntry, CalendarEventTemplate
from apps.portal.decorators import require_portal_access, require_portal_json
from apps.portal.views._helpers import parse_json_body, log_activity


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
            "extendedProps": {
                "description": entry.description or "",
                "location": entry.location or "",
                "event_type": entry.event_type or "",
            },
        })

    return JsonResponse(events, safe=False)


@require_portal_json()
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
        description=payload.get("description", "").strip(),
        start=start,
        end=end,
        all_day=payload.get("all_day", False),
        color=payload.get("color", ""),
        location=payload.get("location", "").strip(),
        event_type=payload.get("event_type", ""),
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
    if "description" in payload:
        entry.description = payload["description"].strip()
    if "start" in payload:
        entry.start = parse_datetime(payload["start"]) or parse_date(payload["start"])
    if "end" in payload:
        end_str = payload["end"]
        entry.end = parse_datetime(end_str) if end_str else None
    if "all_day" in payload:
        entry.all_day = payload["all_day"]
    if "color" in payload:
        entry.color = payload["color"]
    if "location" in payload:
        entry.location = payload["location"].strip()
    if "event_type" in payload:
        entry.event_type = payload["event_type"]

    entry.save()
    return JsonResponse({"ok": True})


@require_portal_json()
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
    ).order_by("name")

    data = [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description or "",
            "duration_minutes": t.duration_minutes,
            "color": t.color or "",
            "event_type": t.event_type or "",
        }
        for t in templates
    ]
    return JsonResponse({"templates": data})


@require_portal_json()
@require_http_methods(["POST"])
def calendar_template_create(request):
    payload = parse_json_body(request)
    name = payload.get("name", "").strip()
    if not name:
        return JsonResponse({"error": "Nome obrigatório"}, status=400)

    template = CalendarEventTemplate.objects.create(
        organization=request.organization,
        office=request.office,
        name=name,
        description=payload.get("description", "").strip(),
        duration_minutes=payload.get("duration_minutes", 60),
        color=payload.get("color", ""),
        event_type=payload.get("event_type", ""),
    )
    return JsonResponse({"ok": True, "template_id": template.id})


@require_portal_json()
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