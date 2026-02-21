"""
Views do módulo Relatórios — dashboard analítico do portal.
"""
import json
from datetime import date, timedelta

from django.db.models import Count, Sum, Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from apps.portal.decorators import require_portal_access, require_portal_json
from apps.portal.permissions import require_role


# ==================== HELPERS ====================

def _daterange_from_request(request, default_days=30):
    today = date.today()
    try:
        end_str = request.GET.get("fim") or request.GET.get("end")
        start_str = request.GET.get("inicio") or request.GET.get("start")
        end = date.fromisoformat(end_str) if end_str else today
        start = date.fromisoformat(start_str) if start_str else (today - timedelta(days=default_days))
    except ValueError:
        end = today
        start = today - timedelta(days=default_days)
    return start, end


def _build_metrics(org, office, start=None, end=None):
    """Coleta todas as métricas de um office para o período."""
    today = date.today()
    if start is None:
        start = today - timedelta(days=30)
    if end is None:
        end = today

    from apps.processes.models import Process
    from apps.deadlines.models import Deadline
    from apps.customers.models import Customer

    # ---- PROCESSOS ----
    processes_qs = Process.objects.filter(organization=org, office=office)

    process_by_status = list(
        processes_qs.values("status").annotate(count=Count("id")).order_by("status")
    )
    process_by_phase = list(
        processes_qs.values("phase").annotate(count=Count("id")).order_by("phase")
    )
    process_by_area = list(
        processes_qs.values("area").annotate(count=Count("id")).order_by("-count")
    )
    process_total = processes_qs.count()

    # ---- PRAZOS ----
    deadlines_qs = Deadline.objects.filter(organization=org, office=office)
    deadline_by_status = list(
        deadlines_qs.values("status").annotate(count=Count("id"))
    )
    deadlines_overdue = deadlines_qs.filter(
        status="pending", due_date__lt=today
    ).count()
    deadlines_upcoming = deadlines_qs.filter(
        status="pending",
        due_date__gte=today,
        due_date__lte=today + timedelta(days=7),
    ).order_by("due_date").values("id", "title", "due_date", "priority")[:10]
    deadlines_critical = list(deadlines_upcoming)

    # ---- PIPELINE / CRM ----
    try:
        pipeline_qs = Customer.objects.filter(
            organization=org, office=office, is_deleted=False,
            status__in=["lead", "prospect"],
        )
        pipeline_by_stage = list(
            pipeline_qs.values("pipeline_stage").annotate(
                count=Count("id"),
                total_value=Sum("estimated_value"),
            ).order_by("pipeline_stage")
        )
        # Conversão: quantos viraram "client" no período
        converted = Customer.objects.filter(
            organization=org, office=office, is_deleted=False,
            status="client",
            updated_at__date__gte=start,
            updated_at__date__lte=end,
        ).count()
        total_leads_period = Customer.objects.filter(
            organization=org, office=office, is_deleted=False,
            created_at__date__gte=start,
            created_at__date__lte=end,
        ).count()
        conversion_rate = round((converted / total_leads_period * 100), 1) if total_leads_period else 0
    except Exception:
        pipeline_by_stage = []
        converted = 0
        total_leads_period = 0
        conversion_rate = 0

    # ---- FINANCEIRO ----
    try:
        from apps.finance.models import Invoice, Payment, FeeAgreement
        from django.db.models.functions import TruncMonth

        invoices_qs = Invoice.objects.filter(organization=org, office=office)
        invoices_by_status = list(
            invoices_qs.values("status").annotate(
                count=Count("id"), total=Sum("amount")
            )
        )
        # Receita por mês (últimos 6 meses)
        six_months_ago = today - timedelta(days=180)
        payments_qs = Payment.objects.filter(
            organization=org, office=office,
            paid_at__date__gte=six_months_ago,
        )
        payments_by_month = list(
            payments_qs.annotate(month=TruncMonth("paid_at"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )
        revenue_months = [
            {
                "month": row["month"].strftime("%b/%y") if row["month"] else "",
                "total": float(row["total"] or 0),
            }
            for row in payments_by_month
        ]

        # Despesas por mês
        from apps.finance.models import Expense
        expenses_qs = Expense.objects.filter(
            organization=org, office=office,
            date__gte=six_months_ago,
        )
        expenses_by_month = list(
            expenses_qs.annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )
        expense_months = [
            {
                "month": row["month"].strftime("%b/%y") if row["month"] else "",
                "total": float(row["total"] or 0),
            }
            for row in expenses_by_month
        ]

        # Receita total do mês atual
        first_of_month = today.replace(day=1)
        revenue_this_month = Payment.objects.filter(
            organization=org, office=office,
            paid_at__date__gte=first_of_month,
        ).aggregate(total=Sum("amount"))["total"] or 0

        expenses_this_month = Expense.objects.filter(
            organization=org, office=office,
            date__gte=first_of_month,
        ).aggregate(total=Sum("amount"))["total"] or 0

        pending_invoices_total = invoices_qs.filter(
            status__in=["issued", "sent"]
        ).aggregate(total=Sum("amount"))["total"] or 0

        finance_ok = True
    except Exception:
        invoices_by_status = []
        revenue_months = []
        expense_months = []
        revenue_this_month = 0
        expenses_this_month = 0
        pending_invoices_total = 0
        finance_ok = False

    return {
        # Processos
        "process_total": process_total,
        "process_by_status": process_by_status,
        "process_by_phase": process_by_phase,
        "process_by_area": process_by_area,
        # Prazos
        "deadline_by_status": deadline_by_status,
        "deadlines_overdue": deadlines_overdue,
        "deadlines_critical": deadlines_critical,
        # Pipeline
        "pipeline_by_stage": pipeline_by_stage,
        "pipeline_converted": converted,
        "pipeline_total_leads": total_leads_period,
        "pipeline_conversion_rate": conversion_rate,
        # Financeiro
        "finance_ok": finance_ok,
        "invoices_by_status": invoices_by_status,
        "revenue_months": revenue_months,
        "expense_months": expense_months,
        "revenue_this_month": float(revenue_this_month),
        "expenses_this_month": float(expenses_this_month),
        "pending_invoices_total": float(pending_invoices_total),
        # Alertas
        "alerts": _build_alerts(org, office, today),
    }


def _build_alerts(org, office, today):
    """Constrói lista de alertas para o dashboard."""
    alerts = []

    from apps.deadlines.models import Deadline
    urgent = Deadline.objects.filter(
        organization=org, office=office,
        status="pending",
        due_date__lte=today + timedelta(days=3),
        due_date__gte=today,
    ).order_by("due_date")[:5]
    for d in urgent:
        days = (d.due_date - today).days
        alerts.append({
            "icon": "fas fa-clock",
            "color": "warning",
            "text": f'Prazo "{d.title}" vence em {days}d',
            "url": "/app/prazos/",
        })

    overdue = Deadline.objects.filter(
        organization=org, office=office,
        status="pending", due_date__lt=today,
    ).count()
    if overdue:
        alerts.append({
            "icon": "fas fa-exclamation-triangle",
            "color": "danger",
            "text": f"{overdue} prazo(s) vencido(s) sem conclusão",
            "url": "/app/prazos/",
        })

    try:
        from apps.customers.models import Customer
        stale = Customer.objects.filter(
            organization=org, office=office, is_deleted=False,
            status__in=["lead", "prospect"],
        ).filter(
            Q(next_action_date__lt=today) | Q(next_action_date__isnull=True)
        ).count()
        if stale:
            alerts.append({
                "icon": "fas fa-user-clock",
                "color": "warning",
                "text": f"{stale} lead(s) sem próxima ação definida",
                "url": "/app/contatos/pipeline/",
            })
    except Exception:
        pass

    try:
        from apps.finance.models import Invoice
        overdue_inv = Invoice.objects.filter(
            organization=org, office=office,
            status__in=["issued", "sent"],
            due_date__lt=today,
        ).count()
        if overdue_inv:
            alerts.append({
                "icon": "fas fa-file-invoice-dollar",
                "color": "danger",
                "text": f"{overdue_inv} fatura(s) vencida(s) sem pagamento",
                "url": "/app/financeiro/faturas/",
            })
    except Exception:
        pass

    return alerts


# ==================== VIEWS ====================

@require_portal_access()
@require_role("manager")
def relatorios_dashboard(request):
    start, end = _daterange_from_request(request, default_days=30)
    metrics = _build_metrics(request.organization, request.office, start, end)

    # Serializa para JSON seguro no template
    metrics_json = json.dumps({
        k: v for k, v in metrics.items()
        if not isinstance(v, (type(None),))
    }, default=str)

    return render(request, "portal/relatorios_dashboard.html", {
        "active_page": "relatorios",
        "metrics": metrics,
        "metrics_json": metrics_json,
        "date_start": start.isoformat(),
        "date_end": end.isoformat(),
    })


@require_portal_json()
@require_role("manager")
def relatorios_json(request):
    start, end = _daterange_from_request(request, default_days=30)
    metrics = _build_metrics(request.organization, request.office, start, end)
    return JsonResponse(metrics, safe=False)


@require_portal_access()
@require_role("manager")
def relatorios_export(request):
    """Exporta dados para CSV simples."""
    tipo = request.GET.get("tipo", "processos")
    org = request.organization
    office = request.office

    import csv
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="relatorio_{tipo}.csv"'
    writer = csv.writer(response)

    if tipo == "processos":
        from apps.processes.models import Process
        writer.writerow(["Número", "Assunto", "Área", "Fase", "Status", "Responsável", "Criado em"])
        for p in Process.objects.filter(organization=org, office=office).select_related("responsible"):
            writer.writerow([
                p.number or "", p.subject or "", p.area or "", p.phase or "",
                p.status or "",
                p.responsible.get_full_name() if p.responsible else "",
                p.created_at.strftime("%d/%m/%Y") if p.created_at else "",
            ])

    elif tipo == "prazos":
        from apps.deadlines.models import Deadline
        writer.writerow(["Título", "Tipo", "Prioridade", "Status", "Vencimento", "Responsável"])
        for d in Deadline.objects.filter(organization=org, office=office).select_related("responsible"):
            writer.writerow([
                d.title, d.type, d.priority, d.status,
                d.due_date.strftime("%d/%m/%Y") if d.due_date else "",
                d.responsible.get_full_name() if d.responsible else "",
            ])

    elif tipo == "financeiro":
        try:
            from apps.finance.models import Invoice
            writer.writerow(["Contrato", "Cliente", "Valor", "Status", "Vencimento"])
            for inv in Invoice.objects.filter(organization=org, office=office).select_related("agreement__customer"):
                writer.writerow([
                    str(inv.agreement) if inv.agreement else "",
                    inv.agreement.customer.name if inv.agreement and inv.agreement.customer else "",
                    float(inv.amount or 0),
                    inv.status,
                    inv.due_date.strftime("%d/%m/%Y") if inv.due_date else "",
                ])
        except Exception:
            writer.writerow(["Erro ao exportar dados financeiros"])

    else:
        writer.writerow(["Tipo de relatório desconhecido"])

    return response
