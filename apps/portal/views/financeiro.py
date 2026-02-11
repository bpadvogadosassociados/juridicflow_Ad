"""
Views Financeiras — Contratos, Faturas, Despesas.
"""
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods

from apps.customers.models import Customer
from apps.finance.models import FeeAgreement, Invoice, Expense
from apps.portal.decorators import require_portal_access, require_portal_json
from apps.portal.forms import FeeAgreementForm
from apps.portal.views._helpers import parse_json_body, log_activity

from apps.portal.permissions import require_role, require_action
from apps.portal.audit import audited

# ==================== DASHBOARD ====================

@require_portal_access()
@require_role("lawyer")
def financeiro_dashboard(request):
    office = request.office
    today = timezone.now().date()
    month_start = today.replace(day=1)

    # Totais de contratos
    contracts_total = FeeAgreement.objects.filter(
        office=office
    ).aggregate(total=Sum("amount"))["total"] or 0

    active_contracts = FeeAgreement.objects.filter(
        office=office, status="active"
    ).count()

    # Receita do mês (faturas pagas)
    monthly_revenue = Invoice.objects.filter(
        office=office, status="paid", paid_date__gte=month_start
    ).aggregate(total=Sum("amount"))["total"] or 0

    # Despesas do mês
    monthly_expenses = Expense.objects.filter(
        office=office, date__gte=month_start
    ).aggregate(total=Sum("amount"))["total"] or 0

    # Faturas pendentes
    pending_invoices = Invoice.objects.filter(
        office=office, status__in=["issued", "sent"]
    ).aggregate(total=Sum("amount"))["total"] or 0

    overdue_invoices = Invoice.objects.filter(
        office=office, status="overdue"
    ).aggregate(total=Sum("amount"))["total"] or 0

    # Últimas transações
    recent_invoices = Invoice.objects.filter(
        office=office
    ).select_related("fee_agreement__customer").order_by("-created_at")[:5]

    recent_expenses = Expense.objects.filter(
        office=office
    ).order_by("-date")[:5]

    return render(request, "portal/financeiro_dashboard.html", {
        "contracts_total": contracts_total,
        "active_contracts": active_contracts,
        "monthly_revenue": monthly_revenue,
        "monthly_expenses": monthly_expenses,
        "pending_invoices": pending_invoices,
        "overdue_invoices": overdue_invoices,
        "recent_invoices": recent_invoices,
        "recent_expenses": recent_expenses,
        "active_page": "financeiro",
    })


# ==================== CONTRATOS ====================

@require_portal_access()
@require_role("lawyer")
def financeiro_contratos(request):
    search = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")

    qs = FeeAgreement.objects.filter(
        organization=request.organization,
        office=request.office,
    ).select_related("customer").order_by("-created_at")

    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(customer__name__icontains=search)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)

    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    contracts = paginator.get_page(request.GET.get("page", 1))

    return render(request, "portal/financeiro_contratos.html", {
        "contracts": contracts,
        "search": search,
        "status_filter": status_filter,
        "active_page": "financeiro",
    })


@require_portal_access()
@require_role("manager")
@require_http_methods(["GET", "POST"])
def financeiro_contrato_create(request):
    if request.method == "POST":
        form = FeeAgreementForm(request.POST, office=request.office)
        if form.is_valid():
            agreement = form.save(commit=False)
            agreement.organization = request.organization
            agreement.office = request.office
            try:
                agreement.save()
                log_activity(request, "contract_create", f"Contrato criado: {agreement.title}")
                messages.success(request, f"Contrato '{agreement.title}' criado com sucesso!")
                return redirect("portal:financeiro_contrato_detail", agreement.id)
            except Exception as e:
                messages.error(request, f"Erro ao salvar contrato: {e}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    label = form.fields[field].label or field
                    messages.error(request, f"{label}: {error}")
    else:
        form = FeeAgreementForm(office=request.office)

    return render(request, "portal/financeiro_contrato_form.html", {
        "form": form,
        "active_page": "financeiro",
    })


@require_portal_access()
@require_role("lawyer")
def financeiro_contrato_detail(request, contract_id):
    agreement = get_object_or_404(
        FeeAgreement.objects.select_related("customer"),
        id=contract_id,
        organization=request.organization,
        office=request.office,
    )
    invoices = agreement.invoices.order_by("-due_date")
    total_paid = invoices.filter(status="paid").aggregate(total=Sum("amount"))["total"] or 0
    total_pending = invoices.exclude(status="paid").aggregate(total=Sum("amount"))["total"] or 0

    return render(request, "portal/financeiro_contrato_detail.html", {
        "agreement": agreement,
        "invoices": invoices,
        "total_paid": total_paid,
        "total_pending": total_pending,
        "active_page": "financeiro",
    })


# ==================== FATURAS ====================

@require_portal_access()
@require_role("lawyer")
def financeiro_faturas(request):
    office = request.office
    status_filter = request.GET.get("status", "")

    # Batch update faturas vencidas (Phase 1 fix — sem loop)
    today = timezone.now().date()
    Invoice.objects.filter(
        office=office,
        status__in=["issued", "sent"],
        due_date__lt=today,
    ).update(status="overdue")

    qs = Invoice.objects.filter(
        organization=request.organization,
        office=office,
    ).select_related("fee_agreement__customer").order_by("-due_date")

    if status_filter:
        qs = qs.filter(status=status_filter)

    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    invoices = paginator.get_page(request.GET.get("page", 1))

    return render(request, "portal/financeiro_faturas.html", {
        "invoices": invoices,
        "status_filter": status_filter,
        "active_page": "financeiro",
    })


@require_portal_json()
@require_role("manager")
@require_http_methods(["POST"])
def financeiro_fatura_create(request):
    payload = parse_json_body(request)
    contract_id = payload.get("contract_id")
    if not contract_id:
        return JsonResponse({"error": "contract_id obrigatório"}, status=400)

    agreement = get_object_or_404(
        FeeAgreement,
        id=contract_id,
        organization=request.organization,
        office=request.office,
    )
    due_date = parse_date(payload.get("due_date", ""))
    if not due_date:
        return JsonResponse({"error": "due_date obrigatório"}, status=400)

    amount = payload.get("amount")
    if not amount:
        return JsonResponse({"error": "amount obrigatório"}, status=400)

    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return JsonResponse({"error": "amount inválido"}, status=400)

    invoice = Invoice.objects.create(
        organization=request.organization,
        office=request.office,
        fee_agreement=agreement,
        amount=amount,
        due_date=due_date,
        description=payload.get("description", "").strip(),
        status="issued",
    )
    log_activity(request, "invoice_create", f"Fatura #{invoice.id} criada — R${amount:.2f}")

    return JsonResponse({
        "ok": True,
        "invoice": {
            "id": invoice.id,
            "amount": str(invoice.amount),
            "due_date": invoice.due_date.isoformat(),
            "status": invoice.status,
        },
    })


@require_portal_json()
@require_role("manager")
@audited(action="payment", model_name="Invoice")
@require_http_methods(["POST"])
def financeiro_fatura_registrar_pagamento(request, invoice_id):
    invoice = get_object_or_404(
        Invoice,
        id=invoice_id,
        organization=request.organization,
        office=request.office,
    )
    payload = parse_json_body(request)
    paid_date = parse_date(payload.get("paid_date", ""))

    invoice.status = "paid"
    invoice.paid_date = paid_date or timezone.now().date()
    invoice.paid_amount = payload.get("paid_amount") or invoice.amount
    invoice.payment_method = payload.get("payment_method", "")
    invoice.save()

    log_activity(request, "invoice_pay", f"Fatura #{invoice.id} paga — R${invoice.paid_amount}")
    return JsonResponse({"ok": True, "status": "paid"})


# ==================== DESPESAS ====================

@require_portal_access()
@require_role("lawyer")
def financeiro_despesas(request):
    search = request.GET.get("search", "")
    category = request.GET.get("category", "")

    qs = Expense.objects.filter(
        organization=request.organization,
        office=request.office,
    ).order_by("-date")

    if search:
        qs = qs.filter(
            Q(description__icontains=search)
            | Q(supplier__icontains=search)
        )
    if category:
        qs = qs.filter(category=category)

    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    expenses = paginator.get_page(request.GET.get("page", 1))

    return render(request, "portal/financeiro_despesas.html", {
        "expenses": expenses,
        "search": search,
        "category": category,
        "active_page": "financeiro",
    })


@require_portal_json()
@require_role("manager")
@require_http_methods(["POST"])
def financeiro_despesa_create(request):
    payload = parse_json_body(request)
    description = payload.get("description", "").strip()
    if not description:
        return JsonResponse({"error": "Descrição obrigatória"}, status=400)

    amount = payload.get("amount")
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Valor inválido"}, status=400)

    date = parse_date(payload.get("date", "")) or timezone.now().date()

    expense = Expense.objects.create(
        organization=request.organization,
        office=request.office,
        description=description,
        amount=amount,
        date=date,
        category=payload.get("category", ""),
        supplier=payload.get("supplier", "").strip(),
        notes=payload.get("notes", "").strip(),
        created_by=request.user,
    )
    log_activity(request, "expense_create", f"Despesa criada: {description} — R${amount:.2f}")
    return JsonResponse({
        "ok": True,
        "expense": {
            "id": expense.id,
            "description": expense.description,
            "amount": str(expense.amount),
            "date": expense.date.isoformat(),
        },
    })


@require_portal_json()
@require_role("manager")
@require_http_methods(["POST"])
def financeiro_despesa_update(request, expense_id):
    expense = get_object_or_404(
        Expense,
        id=expense_id,
        organization=request.organization,
        office=request.office,
    )
    payload = parse_json_body(request)

    if "description" in payload:
        expense.description = payload["description"].strip()
    if "amount" in payload:
        try:
            expense.amount = float(payload["amount"])
        except (ValueError, TypeError):
            return JsonResponse({"error": "Valor inválido"}, status=400)
    if "date" in payload:
        expense.date = parse_date(payload["date"]) or expense.date
    if "category" in payload:
        expense.category = payload["category"]
    if "supplier" in payload:
        expense.supplier = payload["supplier"].strip()
    if "notes" in payload:
        expense.notes = payload["notes"].strip()

    expense.save()
    return JsonResponse({"ok": True})


@require_portal_json()
@require_role("admin")
@audited(action="delete", model_name="Expense")
@require_http_methods(["POST"])
def financeiro_despesa_delete(request, expense_id):
    expense = get_object_or_404(
        Expense,
        id=expense_id,
        organization=request.organization,
        office=request.office,
    )
    desc = expense.description
    expense.delete()
    log_activity(request, "expense_delete", f"Despesa deletada: {desc}")
    return JsonResponse({"ok": True})


@require_portal_json()
@require_role("lawyer")
def financeiro_despesa_detail(request, expense_id):
    expense = get_object_or_404(
        Expense,
        id=expense_id,
        organization=request.organization,
        office=request.office,
    )
    return JsonResponse({
        "id": expense.id,
        "description": expense.description,
        "amount": str(expense.amount),
        "date": expense.date.isoformat(),
        "category": expense.category,
        "supplier": expense.supplier,
        "notes": expense.notes,
        "created_at": expense.created_at.isoformat(),
    })