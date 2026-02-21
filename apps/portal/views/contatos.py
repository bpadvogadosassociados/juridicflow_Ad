"""
Views de Contatos / CRM.
"""
import csv
import io

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_http_methods
from openpyxl import Workbook

from apps.customers.models import Customer, CustomerInteraction, CustomerDocument
from apps.finance.models import FeeAgreement
from apps.processes.models import ProcessParty
from apps.portal.decorators import require_portal_access, require_portal_json
from apps.portal.forms import CustomerForm
from apps.portal.views._helpers import log_activity, parse_json_body

from apps.portal.permissions import require_role, require_action
from apps.portal.audit import audited

def _collect_tags(qs):
    """Coleta tags de um queryset sem carregar objetos inteiros."""
    tags = set()
    for tags_str in qs.exclude(tags="").values_list("tags", flat=True):
        tags.update(t.strip() for t in tags_str.split(",") if t.strip())
    return tags


def _count_tags(qs, limit=10):
    """Conta tags e retorna as top N como lista de tuplas."""
    counts: dict[str, int] = {}
    for tags_str in qs.exclude(tags="").values_list("tags", flat=True):
        for tag in (t.strip() for t in tags_str.split(",") if t.strip()):
            counts[tag] = counts.get(tag, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]


# ==================== DASHBOARD ====================

@require_portal_access()
def contatos_dashboard(request):
    office = request.office
    base_qs = Customer.objects.filter(office=office, is_deleted=False)

    total = base_qs.count()
    by_status = list(base_qs.values("status").annotate(count=Count("id")))
    by_type = list(base_qs.values("type").annotate(count=Count("id")))
    by_origin = list(base_qs.values("origin").annotate(count=Count("id")).order_by("-count")[:5])

    leads = base_qs.filter(status="lead").count()
    clients = base_qs.filter(status="client").count()
    conversion_rate = (clients / leads * 100) if leads > 0 else 0

    recent = base_qs.order_by("-created_at")[:10]
    recent_interactions = (
        CustomerInteraction.objects.filter(office=office)
        .select_related("customer", "created_by")
        .order_by("-date")[:10]
    )
    top_tags = _count_tags(base_qs)

    return render(request, "portal/contatos_dashboard.html", {
        "total": total,
        "by_status": by_status,
        "by_type": by_type,
        "by_origin": by_origin,
        "leads": leads,
        "clients": clients,
        "conversion_rate": conversion_rate,
        "recent": recent,
        "recent_interactions": recent_interactions,
        "top_tags": top_tags,
        "active_page": "contatos",
    })


# ==================== LISTA ====================

@require_portal_access()
def contatos(request):
    search = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")
    type_filter = request.GET.get("type", "")
    origin_filter = request.GET.get("origin", "")
    tag_filter = request.GET.get("tag", "")

    qs = Customer.objects.filter(
        office=request.office, is_deleted=False
    ).select_related("responsible")

    if search:
        qs = qs.filter(
            Q(name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
            | Q(document__icontains=search)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)
    if type_filter:
        qs = qs.filter(type=type_filter)
    if origin_filter:
        qs = qs.filter(origin=origin_filter)
    if tag_filter:
        qs = qs.filter(tags__icontains=tag_filter)

    qs = qs.order_by("-created_at")

    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    customers = paginator.get_page(request.GET.get("page", 1))

    all_tags = _collect_tags(
        Customer.objects.filter(office=request.office, is_deleted=False)
    )

    return render(request, "portal/contatos.html", {
        "customers": customers,
        "search": search,
        "status_filter": status_filter,
        "type_filter": type_filter,
        "origin_filter": origin_filter,
        "tag_filter": tag_filter,
        "status_choices": Customer.STATUS_CHOICES,
        "type_choices": Customer.TYPE_CHOICES,
        "origin_choices": Customer.ORIGIN_CHOICES,
        "all_tags": sorted(all_tags),
        "active_page": "contatos",
    })


# ==================== CREATE / EDIT ====================

@require_portal_access()
@require_role("assistant")
@require_http_methods(["GET", "POST"])
def contato_create(request):
    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.organization = request.organization
            customer.office = request.office
            customer.responsible = request.user
            customer.first_contact_date = timezone.now().date()
            try:
                customer.save()
                log_activity(request, "customer_create", f"Novo contato: {customer.name}")
                messages.success(request, f"Contato {customer.name} criado com sucesso!")
                return redirect("portal:contato_detail", customer.id)
            except Exception as e:
                messages.error(request, f"Erro ao criar contato: {e}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    label = form.fields[field].label or field
                    messages.error(request, f"{label}: {error}")
    else:
        form = CustomerForm()

    return render(request, "portal/contato_form.html", {
        "form": form,
        "status_choices": Customer.STATUS_CHOICES,
        "type_choices": Customer.TYPE_CHOICES,
        "origin_choices": Customer.ORIGIN_CHOICES,
        "active_page": "contatos",
    })


@require_portal_access()
def contato_detail(request, customer_id):
    customer = get_object_or_404(
        Customer.objects.select_related("responsible"),
        id=customer_id,
        organization=request.organization,
        office=request.office,
        is_deleted=False,
    )
    interactions = customer.interactions.select_related("created_by").order_by("-date")[:20]
    documents = customer.customer_documents.select_related("uploaded_by").order_by("-created_at")
    process_parties = ProcessParty.objects.filter(customer=customer).select_related("process")
    agreements = FeeAgreement.objects.filter(
        customer=customer, office=request.office
    ).order_by("-created_at")

    return render(request, "portal/contato_detail.html", {
        "customer": customer,
        "interactions": interactions,
        "documents": documents,
        "process_parties": process_parties,
        "agreements": agreements,
        "interaction_type_choices": CustomerInteraction.TYPE_CHOICES,
        "document_type_choices": CustomerDocument.TYPE_CHOICES,
        "active_page": "contatos",
    })


@require_portal_access()
@require_role("lawyer")
@require_http_methods(["GET", "POST"])
def contato_edit(request, customer_id):
    customer = get_object_or_404(
        Customer,
        id=customer_id,
        organization=request.organization,
        office=request.office,
        is_deleted=False,
    )
    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, "Contato atualizado com sucesso!")
            return redirect("portal:contato_detail", customer.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    label = form.fields[field].label or field
                    messages.error(request, f"{label}: {error}")
    else:
        form = CustomerForm(instance=customer)

    return render(request, "portal/contato_form.html", {
        "form": form,
        "customer": customer,
        "status_choices": Customer.STATUS_CHOICES,
        "type_choices": Customer.TYPE_CHOICES,
        "origin_choices": Customer.ORIGIN_CHOICES,
        "active_page": "contatos",
    })


@require_portal_json()
@require_role("manager")
@audited(action="delete", model_name="Customer")
@require_http_methods(["POST"])
def contato_delete(request, customer_id):
    customer = get_object_or_404(
        Customer,
        id=customer_id,
        organization=request.organization,
        office=request.office,
    )
    name = customer.name
    customer.soft_delete()
    log_activity(request, "customer_delete", f"Contato deletado: {name}")
    return JsonResponse({"ok": True})


# ==================== INTERAÇÕES ====================

@require_portal_json()
@require_role("intern")
@require_http_methods(["POST"])
def contato_interaction_create(request, customer_id):
    customer = get_object_or_404(
        Customer,
        id=customer_id,
        organization=request.organization,
        office=request.office,
        is_deleted=False,
    )
    payload = parse_json_body(request)
    date_str = payload.get("date", "")
    time_str = payload.get("time", "12:00")
    date = parse_datetime(f"{date_str}T{time_str}") if date_str else None

    interaction = CustomerInteraction.objects.create(
        organization=request.organization,
        office=request.office,
        customer=customer,
        type=payload.get("type", "note"),
        date=date or timezone.now(),
        subject=payload.get("subject", "").strip(),
        description=payload.get("description", "").strip(),
        created_by=request.user,
    )
    customer.last_interaction_date = timezone.now().date()
    customer.save(update_fields=["last_interaction_date"])

    return JsonResponse({
        "ok": True,
        "interaction": {
            "id": interaction.id,
            "type": interaction.get_type_display(),
            "date": interaction.date.strftime("%d/%m/%Y %H:%M"),
            "subject": interaction.subject,
        },
    })


# ==================== IMPORT / EXPORT ====================

@require_portal_access()
@require_role("lawyer")
@audited(action="export", model_name="Customer")
def contatos_export(request):
    customers = Customer.objects.filter(
        office=request.office, is_deleted=False
    ).order_by("name")

    wb = Workbook()
    ws = wb.active
    ws.title = "Contatos"
    headers = [
        "Nome", "CPF/CNPJ", "Tipo", "Status", "Email", "Telefone",
        "Endereço", "Cidade", "Estado", "CEP", "Origem", "Tags", "Criado em",
    ]
    ws.append(headers)

    for c in customers:
        ws.append([
            c.name, c.document, c.get_type_display(), c.get_status_display(),
            c.email, c.phone, c.full_address, c.address_city,
            c.address_state, c.address_zipcode, c.get_origin_display(),
            c.tags, c.created_at.strftime("%d/%m/%Y"),
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=contatos.xlsx"
    wb.save(response)
    return response


@require_portal_json()
@require_role("manager")
@audited(action="import", model_name="Customer")
@require_http_methods(["POST"])
def contatos_import(request):
    if "file" not in request.FILES:
        return JsonResponse({"error": "Nenhum arquivo enviado"}, status=400)

    try:
        decoded = request.FILES["file"].read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded))
        created = 0
        errors = []

        for row in reader:
            try:
                Customer.objects.create(
                    organization=request.organization,
                    office=request.office,
                    name=row.get("nome", "").strip(),
                    document=row.get("cpf_cnpj", "").strip(),
                    type=row.get("tipo", "PF"),
                    email=row.get("email", "").strip(),
                    phone=row.get("telefone", "").strip(),
                    status="lead",
                    responsible=request.user,
                )
                created += 1
            except Exception as e:
                errors.append(f"Linha {reader.line_num}: {e}")

        return JsonResponse({"ok": True, "created": created, "errors": errors})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)