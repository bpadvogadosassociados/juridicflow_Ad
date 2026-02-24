"""
Views de Publicações Judiciais.
"""
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.publications.models import (
    Publication, JudicialEvent, PublicationRule, PublicationFilter,
)
from apps.publications.services import PublicationProcessor
from apps.portal.decorators import require_portal_access, require_portal_json
from apps.portal.views._helpers import parse_json_body, log_activity

from apps.shared.permissions import require_membership_perm
from apps.portal.audit import audited

# ==================== DASHBOARD ====================

@require_portal_access()
def publicacoes_dashboard(request):
    office = request.office

    total = Publication.objects.filter(office=office).count()
    events_total = JudicialEvent.objects.filter(office=office).count()
    events_pending = JudicialEvent.objects.filter(office=office, status="pending").count()
    events_analyzed = JudicialEvent.objects.filter(office=office, status="analyzed").count()

    recent_publications = Publication.objects.filter(
        office=office
    ).order_by("-publication_date")[:10]

    recent_events = JudicialEvent.objects.filter(
        office=office
    ).select_related("publication", "process", "assigned_to").order_by("-created_at")[:10]

    by_source = list(
        Publication.objects.filter(office=office)
        .values("source")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return render(request, "portal/publicacoes_dashboard.html", {
        "total": total,
        "events_total": events_total,
        "events_pending": events_pending,
        "events_analyzed": events_analyzed,
        "recent_publications": recent_publications,
        "recent_events": recent_events,
        "by_source": by_source,
        "active_page": "publicacoes",
    })


# ==================== LISTA ====================

@require_portal_access()
def publicacoes(request):
    search = request.GET.get("search", "")
    source = request.GET.get("source", "")

    qs = Publication.objects.filter(
        organization=request.organization,
        office=request.office,
    ).order_by("-publication_date")

    if search:
        qs = qs.filter(
            Q(content__icontains=search) | Q(process_number__icontains=search)
        )
    if source:
        qs = qs.filter(source=source)

    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    publications = paginator.get_page(request.GET.get("page", 1))

    return render(request, "portal/publicacoes.html", {
        "publications": publications,
        "search": search,
        "source": source,
        "active_page": "publicacoes",
    })


# ==================== DETAIL ====================

@require_portal_access()
def publicacao_detail(request, pub_id):
    pub = get_object_or_404(
        Publication,
        id=pub_id,
        organization=request.organization,
        office=request.office,
    )
    events = pub.events.select_related(
        "process", "assigned_to"
    ).order_by("-created_at")

    return render(request, "portal/publicacao_detail.html", {
        "publication": pub,
        "events": events,
        "active_page": "publicacoes",
    })


# ==================== IMPORT ====================

@require_portal_access()
@require_membership_perm("publications.add_publication")
@require_http_methods(["GET", "POST"])
def publicacao_import(request):
    if request.method == "POST":
        text_content = request.POST.get("content", "").strip()
        source = request.POST.get("source", "manual")

        if not text_content:
            messages.error(request, "Conteúdo não pode ser vazio.")
            return render(request, "portal/publicacao_import.html", {
                "active_page": "publicacoes",
            })

        try:
            processor = PublicationProcessor(
                organization=request.organization,
                office=request.office,
            )
            result = processor.process_text(text_content, source=source)
            messages.success(
                request,
                f"Importação concluída: {result.get('publications_created', 0)} publicações, "
                f"{result.get('events_created', 0)} eventos."
            )
            return redirect("portal:publicacoes")
        except Exception as e:
            messages.error(request, f"Erro na importação: {e}")

    return render(request, "portal/publicacao_import.html", {
        "active_page": "publicacoes",
    })


# ==================== EVENTS ====================

@require_portal_json()
@require_membership_perm("publications.change_publication")
@require_http_methods(["POST"])
def evento_assign(request, event_id):
    event = get_object_or_404(
        JudicialEvent,
        id=event_id,
        organization=request.organization,
        office=request.office,
    )
    payload = parse_json_body(request)
    user_id = payload.get("user_id")
    if not user_id:
        return JsonResponse({"error": "user_id obrigatório"}, status=400)

    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "Usuário não encontrado"}, status=404)

    event.assigned_to = user
    event.save(update_fields=["assigned_to"])
    log_activity(request, "event_assign", f"Evento #{event.id} atribuído a {user.email}")
    return JsonResponse({"ok": True})


@require_portal_json()
@require_membership_perm("publications.change_publication")
@require_http_methods(["POST"])
def evento_status(request, event_id):
    event = get_object_or_404(
        JudicialEvent,
        id=event_id,
        organization=request.organization,
        office=request.office,
    )
    payload = parse_json_body(request)
    new_status = payload.get("status", "")
    if new_status not in ("pending", "analyzed", "dismissed", "acted"):
        return JsonResponse({"error": "Status inválido"}, status=400)

    event.status = new_status
    event.save(update_fields=["status"])
    log_activity(request, "event_status", f"Evento #{event.id} → {new_status}")
    return JsonResponse({"ok": True, "status": new_status})


# ==================== RULES / FILTERS ====================

@require_portal_access()
@require_membership_perm("publications.change_publication")
def publicacao_rules(request):
    rules = PublicationRule.objects.filter(
        organization=request.organization,
        office=request.office,
    ).order_by("-created_at")

    return render(request, "portal/publicacao_rules.html", {
        "rules": rules,
        "active_page": "publicacoes",
    })


@require_portal_json()
@require_membership_perm("publications.add_publication")
@require_http_methods(["POST"])
def publicacao_rule_create(request):
    payload = parse_json_body(request)

    event_type = payload.get("event_type", "").strip()
    if not event_type:
        return JsonResponse({"error": "event_type obrigatório"}, status=400)

    days = payload.get("days")
    if not days or int(days) < 1:
        return JsonResponse({"error": "days obrigatório (mínimo 1)"}, status=400)

    rule = PublicationRule.objects.create(
        organization=request.organization,
        office=request.office,
        event_type=event_type,
        description=payload.get("description", "").strip(),
        base_legal=payload.get("base_legal", "").strip(),
        days=int(days),
        business_days=payload.get("business_days", True),
        auto_create_deadline=payload.get("auto_create_deadline", True),
        auto_urgency=payload.get("auto_urgency", "normal"),
        is_active=True,
        priority=int(payload.get("priority", 0)),
    )
    return JsonResponse({"ok": True, "rule_id": rule.id})


@require_portal_access()
@require_membership_perm("publications.change_publication")
def publicacao_filters(request):
    filters = PublicationFilter.objects.filter(
        organization=request.organization,
        office=request.office,
    ).order_by("-created_at")

    return render(request, "portal/publicacao_filters.html", {
        "filters": filters,
        "active_page": "publicacoes",
    })


@require_portal_json()
@require_membership_perm("publications.add_publication")
@require_http_methods(["POST"])
def publicacao_filter_create(request):
    payload = parse_json_body(request)

    filter_type = payload.get("filter_type", "").strip()
    value = payload.get("value", "").strip()
    if not filter_type or not value:
        return JsonResponse({"error": "filter_type e value obrigatórios"}, status=400)

    pub_filter = PublicationFilter.objects.create(
        organization=request.organization,
        office=request.office,
        filter_type=filter_type,
        value=value,
        description=payload.get("description", "").strip(),
        is_active=True,
        case_sensitive=payload.get("case_sensitive", False),
    )
    return JsonResponse({"ok": True, "filter_id": pub_filter.id})