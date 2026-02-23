"""
Views Financeiras — Contratos, Faturas, Despesas.
CORRIGIDO para campos reais dos models.

Campos reais:
  FeeAgreement: customer, process, title, description, amount, billing_type,
                installments, status, start_date, end_date, notes, responsible
  Invoice: agreement (não fee_agreement!), number, issue_date, due_date,
           amount, discount, status, description, notes, payment_method
           (SEM: paid_date, paid_amount)
  Payment: invoice, paid_at, amount, method, reference, notes, recorded_by
  Expense: title (não description!), description, category, date, due_date,
           amount, status, payment_method, supplier, reference, notes, responsible
"""
from decimal import Decimal

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
from apps.finance.models import FeeAgreement, Invoice, Payment, Expense
from apps.portal.decorators import require_portal_access, require_portal_json
from apps.portal.forms import FeeAgreementForm
from apps.portal.views._helpers import parse_json_body, log_activity

from apps.shared.permissions import require_role, require_action
from apps.portal.audit import audited


# ==================== DASHBOARD ====================

@require_portal_access()
@require_role("lawyer")
def financeiro_dashboard(request):
    office = request.office
    today = timezone.now().date()
    month_start = today.replace(day=1)

    contracts_total = FeeAgreement.objects.filter(
        office=office
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    active_contracts = FeeAgreement.objects.filter(
        office=office, status="active"
    ).count()

    # Receita do mês (pagamentos recebidos)
    monthly_revenue = Payment.objects.filter(
        invoice__office=office,
        paid_at__gte=month_start,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    # Despesas do mês
    monthly_expenses = Expense.objects.filter(
        office=office, date__gte=month_start
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    # Faturas pendentes
    pending_invoices = Invoice.objects.filter(
        office=office, status__in=["issued", "sent"]
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    overdue_invoices = Invoice.objects.filter(
        office=office, status="overdue"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    # Últimas transações
    recent_invoices = Invoice.objects.filter(
        office=office
    ).select_related("agreement__customer").order_by("-created_at")[:5]

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
        "status_choices": FeeAgreement.STATUS_CHOICES,
        "billing_type_choices": FeeAgreement.BILLING_TYPE_CHOICES,
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
            agreement.responsible = request.user
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
def financeiro_contrato_detail(request, agreement_id):
    agreement = get_object_or_404(
        FeeAgreement.objects.select_related("customer", "process"),
        id=agreement_id,
        organization=request.organization,
        office=request.office,
    )
    invoices = agreement.invoices.order_by("-due_date")
    total_paid = Payment.objects.filter(
        invoice__agreement=agreement
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    total_pending = invoices.exclude(
        status__in=["paid", "cancelled"]
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

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

    # Batch update faturas vencidas
    today = timezone.now().date()
    Invoice.objects.filter(
        office=office,
        status__in=["issued", "sent"],
        due_date__lt=today,
    ).update(status="overdue")

    qs = Invoice.objects.filter(
        organization=request.organization,
        office=office,
    ).select_related("agreement__customer").order_by("-due_date")

    if status_filter:
        qs = qs.filter(status=status_filter)

    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    invoices = paginator.get_page(request.GET.get("page", 1))

    return render(request, "portal/financeiro_faturas.html", {
        "invoices": invoices,
        "status_filter": status_filter,
        "status_choices": Invoice.STATUS_CHOICES,
        "active_page": "financeiro",
    })


@require_portal_json()
@require_role("manager")
@require_http_methods(["POST"])
def financeiro_fatura_create(request):
    payload = parse_json_body(request)
    agreement_id = payload.get("agreement_id")
    if not agreement_id:
        return JsonResponse({"error": "agreement_id obrigatório"}, status=400)

    agreement = get_object_or_404(
        FeeAgreement,
        id=agreement_id,
        organization=request.organization,
        office=request.office,
    )

    issue_date = parse_date(payload.get("issue_date", ""))
    due_date = parse_date(payload.get("due_date", ""))
    if not issue_date or not due_date:
        return JsonResponse({"error": "issue_date e due_date obrigatórios"}, status=400)

    amount = payload.get("amount")
    if not amount:
        return JsonResponse({"error": "amount obrigatório"}, status=400)

    try:
        amount = Decimal(str(amount))
    except Exception:
        return JsonResponse({"error": "amount inválido"}, status=400)

    invoice = Invoice.objects.create(
        organization=request.organization,
        office=request.office,
        agreement=agreement,
        number=payload.get("number", "").strip(),
        issue_date=issue_date,
        due_date=due_date,
        amount=amount,
        discount=Decimal(str(payload.get("discount", "0.00"))),
        description=payload.get("description", "").strip(),
        notes=payload.get("notes", ""),
        status="issued",
    )
    log_activity(request, "invoice_create", f"Fatura {invoice.number or f'#{invoice.id}'} criada — R${amount:.2f}")

    return JsonResponse({
        "ok": True,
        "invoice": {
            "id": invoice.id,
            "number": invoice.number or "",
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

    paid_at = parse_date(payload.get("paid_at", ""))
    amount = payload.get("amount")

    if not paid_at or not amount:
        return JsonResponse({"error": "paid_at e amount obrigatórios"}, status=400)

    try:
        amount = Decimal(str(amount))
    except Exception:
        return JsonResponse({"error": "amount inválido"}, status=400)

    # Cria o Payment
    Payment.objects.create(
        organization=request.organization,
        office=request.office,
        invoice=invoice,
        paid_at=paid_at,
        amount=amount,
        method=payload.get("method", "pix"),
        reference=payload.get("reference", ""),
        notes=payload.get("notes", ""),
        recorded_by=request.user,
    )

    # Atualiza status da fatura se quitada
    if invoice.balance <= 0:
        invoice.status = "paid"
        invoice.save(update_fields=["status"])

    log_activity(request, "payment_create", f"Pagamento R${amount} na fatura {invoice.number or f'#{invoice.id}'}")
    return JsonResponse({"ok": True, "status": invoice.status})


# ==================== DESPESAS ====================

@require_portal_access()
@require_role("lawyer")
def financeiro_despesas(request):
    search = request.GET.get("search", "")
    category = request.GET.get("category", "")
    status_filter = request.GET.get("status", "")

    qs = Expense.objects.filter(
        organization=request.organization,
        office=request.office,
    ).order_by("-date")

    if search:
        qs = qs.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(supplier__icontains=search)
        )
    if category:
        qs = qs.filter(category=category)
    if status_filter:
        qs = qs.filter(status=status_filter)

    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    expenses = paginator.get_page(request.GET.get("page", 1))

    return render(request, "portal/financeiro_despesas.html", {
        "expenses": expenses,
        "search": search,
        "category": category,
        "status_filter": status_filter,
        "category_choices": Expense.CATEGORY_CHOICES,
        "status_choices": Expense.STATUS_CHOICES,
        "active_page": "financeiro",
    })


@require_portal_json()
@require_role("manager")
@require_http_methods(["POST"])
def financeiro_despesa_create(request):
    payload = parse_json_body(request)
    title = payload.get("title", "").strip()
    if not title:
        return JsonResponse({"error": "Título obrigatório"}, status=400)

    amount = payload.get("amount")
    try:
        amount = Decimal(str(amount))
    except Exception:
        return JsonResponse({"error": "Valor inválido"}, status=400)

    date = parse_date(payload.get("date", "")) or timezone.now().date()

    expense = Expense.objects.create(
        organization=request.organization,
        office=request.office,
        title=title,
        description=payload.get("description", "").strip(),
        amount=amount,
        date=date,
        category=payload.get("category", "other"),
        status=payload.get("status", "pending"),
        supplier=payload.get("supplier", "").strip(),
        reference=payload.get("reference", "").strip(),
        notes=payload.get("notes", "").strip(),
        responsible=request.user,
    )
    log_activity(request, "expense_create", f"Despesa criada: {title} — R${amount:.2f}")
    return JsonResponse({
        "ok": True,
        "expense": {
            "id": expense.id,
            "title": expense.title,
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

    if "title" in payload:
        expense.title = payload["title"].strip()
    if "description" in payload:
        expense.description = payload["description"].strip()
    if "amount" in payload:
        try:
            expense.amount = Decimal(str(payload["amount"]))
        except Exception:
            return JsonResponse({"error": "Valor inválido"}, status=400)
    if "date" in payload:
        expense.date = parse_date(payload["date"]) or expense.date
    if "category" in payload:
        expense.category = payload["category"]
    if "status" in payload:
        expense.status = payload["status"]
    if "supplier" in payload:
        expense.supplier = payload["supplier"].strip()
    if "reference" in payload:
        expense.reference = payload["reference"].strip()
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
    title = expense.title
    expense.delete()
    log_activity(request, "expense_delete", f"Despesa deletada: {title}")
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
        "title": expense.title,
        "description": expense.description,
        "amount": str(expense.amount),
        "date": expense.date.isoformat(),
        "category": expense.category,
        "status": expense.status,
        "supplier": expense.supplier,
        "reference": expense.reference,
        "notes": expense.notes,
        "created_at": expense.created_at.isoformat(),
    })

# ==================== PROPOSTAS ====================

from apps.finance.models import Proposal
from apps.processes.models import Process as _Process


@require_portal_access()
@require_role("lawyer")
def financeiro_propostas(request):
    status_filter = request.GET.get("status", "")
    search = request.GET.get("search", "")

    qs = Proposal.objects.filter(
        office=request.office
    ).select_related("customer", "responsible").order_by("-created_at")

    if status_filter:
        qs = qs.filter(status=status_filter)
    if search:
        qs = qs.filter(
            Q(title__icontains=search) | Q(customer__name__icontains=search)
        )

    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    propostas = paginator.get_page(request.GET.get("page", 1))

    return render(request, "portal/financeiro_propostas.html", {
        "propostas": propostas,
        "status_filter": status_filter,
        "search": search,
        "status_choices": Proposal.STATUS_CHOICES,
        "active_page": "financeiro",
    })


@require_portal_access()
@require_role("lawyer")
@require_http_methods(["GET", "POST"])
def financeiro_proposta_create(request):
    from apps.customers.models import Customer as _Customer
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        customer_id = request.POST.get("customer_id", "")
        amount = request.POST.get("amount", "0")
        description = request.POST.get("description", "")
        valid_until = request.POST.get("valid_until", "") or None
        notes = request.POST.get("notes", "")
        process_id = request.POST.get("process_id", "") or None

        if not title or not customer_id:
            messages.error(request, "Título e cliente são obrigatórios.")
        else:
            try:
                customer = _Customer.objects.get(id=customer_id, organization=request.organization)
                process = None
                if process_id:
                    try:
                        process = _Process.objects.get(id=process_id, organization=request.organization)
                    except _Process.DoesNotExist:
                        pass

                proposal = Proposal.objects.create(
                    organization=request.organization,
                    office=request.office,
                    title=title,
                    customer=customer,
                    amount=amount,
                    description=description,
                    valid_until=valid_until,
                    notes=notes,
                    process=process,
                    responsible=request.user,
                    issue_date=timezone.now().date(),
                    status="draft",
                )
                log_activity(request, "proposal_create", f"Proposta criada: {proposal.title}")
                messages.success(request, "Proposta criada com sucesso!")
                return redirect("portal:financeiro_proposta_detail", proposal.id)
            except Exception as e:
                messages.error(request, f"Erro: {e}")

    customers = _Customer.objects.filter(office=request.office, is_deleted=False).order_by("name")
    processes = _Process.objects.filter(office=request.office).order_by("-created_at")[:50]

    return render(request, "portal/financeiro_proposta_form.html", {
        "customers": customers,
        "processes": processes,
        "active_page": "financeiro",
    })


@require_portal_access()
@require_role("lawyer")
def financeiro_proposta_detail(request, proposal_id):
    proposal = get_object_or_404(
        Proposal,
        id=proposal_id,
        organization=request.organization,
        office=request.office,
    )
    return render(request, "portal/financeiro_proposta_detail.html", {
        "proposal": proposal,
        "status_choices": Proposal.STATUS_CHOICES,
        "active_page": "financeiro",
    })


@require_portal_json()
@require_role("lawyer")
@require_http_methods(["POST"])
def financeiro_proposta_status(request, proposal_id):
    """Muda status da proposta."""
    proposal = get_object_or_404(
        Proposal,
        id=proposal_id,
        organization=request.organization,
        office=request.office,
    )
    payload = parse_json_body(request)
    new_status = payload.get("status", "")
    valid_statuses = [s[0] for s in Proposal.STATUS_CHOICES]
    if new_status not in valid_statuses:
        return JsonResponse({"error": "Status inválido."}, status=400)
    proposal.status = new_status
    proposal.save(update_fields=["status"])
    log_activity(request, "proposal_status", f"Proposta {proposal.title} → {new_status}")
    return JsonResponse({"ok": True, "status": proposal.get_status_display()})


@require_portal_json()
@require_role("lawyer")
@require_http_methods(["POST"])
def financeiro_proposta_converter(request, proposal_id):
    """Converte proposta aceita em FeeAgreement."""
    proposal = get_object_or_404(
        Proposal,
        id=proposal_id,
        organization=request.organization,
        office=request.office,
    )
    try:
        agreement = proposal.convert_to_agreement()
        log_activity(request, "proposal_convert", f"Proposta {proposal.title} convertida em contrato #{agreement.id}")
        return JsonResponse({"ok": True, "agreement_id": agreement.id})
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
