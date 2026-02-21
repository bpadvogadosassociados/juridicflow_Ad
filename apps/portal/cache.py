"""
Cache para métricas de dashboard.

Usa o cache framework do Django (funciona com qualquer backend:
memcached, redis, database, locmem para dev).

Configuração mínima em settings.py (já funciona sem nada):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

Para produção, use Redis:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": "redis://127.0.0.1:6379/1",
        }
    }
"""
import logging
from functools import wraps

from django.core.cache import cache

logger = logging.getLogger("apps.portal.cache")

# TTL padrão: 5 minutos para dashboards
DEFAULT_TTL = 300


def _make_key(prefix: str, office_id: int) -> str:
    """Gera cache key com escopo por office."""
    return f"portal:{prefix}:office:{office_id}"


def cached_metric(prefix: str, ttl: int = DEFAULT_TTL):
    """
    Decorator para cachear resultado de funções que calculam métricas.

    Uso:
        @cached_metric("dashboard_counts")
        def get_dashboard_counts(office):
            # queries pesadas aqui...
            return {"customers": 150, "processes": 42}
    
    A função DEVE receber 'office' como primeiro argumento.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(office, *args, **kwargs):
            key = _make_key(prefix, office.id)
            result = cache.get(key)
            if result is not None:
                return result
            result = func(office, *args, **kwargs)
            try:
                cache.set(key, result, ttl)
            except Exception as exc:
                logger.warning("Cache set failed for %s: %s", key, exc)
            return result
        return wrapper
    return decorator


def invalidate_dashboard(office_id: int):
    """
    Invalida todos os caches de dashboard de um office.
    Chamar após operações que alteram métricas (create, delete, etc).
    """
    prefixes = [
        "dashboard_counts",
        "contatos_dashboard",
        "financeiro_dashboard",
        "documentos_dashboard",
        "publicacoes_dashboard",
    ]
    keys = [_make_key(p, office_id) for p in prefixes]
    try:
        cache.delete_many(keys)
    except Exception as exc:
        logger.warning("Cache invalidation failed: %s", exc)


# ==================== MÉTRICAS CACHEADAS ====================

@cached_metric("dashboard_counts", ttl=300)
def get_dashboard_counts(office):
    """Contadores do dashboard principal — cacheado por 5 min."""
    from apps.customers.models import Customer
    from apps.processes.models import Process
    from apps.memberships.models import Membership
    from apps.portal.models import KanbanBoard, KanbanColumn, KanbanCard

    org = office.organization

    customers_count = Customer.objects.filter(office=office, is_deleted=False).count()
    processes_count = Process.objects.filter(office=office).count()
    team_count = Membership.objects.filter(
        organization=org, office=office, is_active=True
    ).count()

    # Tarefas pendentes
    board = KanbanBoard.objects.filter(organization=org, office=office).first()
    pending_tasks = 0
    if board:
        done_cols = KanbanColumn.objects.filter(
            board=board, title__iregex=r"^(done|conclu[ií]do|finalizado)$"
        )
        pending_tasks = KanbanCard.objects.filter(
            board=board
        ).exclude(column__in=done_cols).count()

    return {
        "customers": customers_count,
        "processes": processes_count,
        "team": team_count,
        "pending_tasks": pending_tasks,
    }


@cached_metric("contatos_dashboard", ttl=300)
def get_contatos_metrics(office):
    """Métricas do dashboard de contatos — cacheado por 5 min."""
    from django.db.models import Count
    from apps.customers.models import Customer

    base_qs = Customer.objects.filter(office=office, is_deleted=False)

    total = base_qs.count()
    leads = base_qs.filter(status="lead").count()
    clients = base_qs.filter(status="client").count()
    conversion_rate = (clients / leads * 100) if leads > 0 else 0

    by_status = list(base_qs.values("status").annotate(count=Count("id")))
    by_type = list(base_qs.values("type").annotate(count=Count("id")))
    by_origin = list(
        base_qs.values("origin").annotate(count=Count("id")).order_by("-count")[:5]
    )

    return {
        "total": total,
        "leads": leads,
        "clients": clients,
        "conversion_rate": conversion_rate,
        "by_status": by_status,
        "by_type": by_type,
        "by_origin": by_origin,
    }


@cached_metric("financeiro_dashboard", ttl=300)
def get_financeiro_metrics(office):
    """Métricas do dashboard financeiro — cacheado por 5 min."""
    from django.db.models import Sum
    from django.utils import timezone
    from apps.finance.models import FeeAgreement, Invoice, Expense, Payment

    today = timezone.now().date()
    month_start = today.replace(day=1)

    contracts_total = FeeAgreement.objects.filter(
        office=office
    ).aggregate(total=Sum("amount"))["total"] or 0

    active_contracts = FeeAgreement.objects.filter(
        office=office, status="active"
    ).count()

    monthly_revenue = Payment.objects.filter(
        invoice__office=office, status="paid", paid_at__gte=month_start
    ).aggregate(total=Sum("amount"))["total"] or 0

    monthly_expenses = Expense.objects.filter(
        office=office, date__gte=month_start
    ).aggregate(total=Sum("amount"))["total"] or 0

    pending_invoices = Invoice.objects.filter(
        office=office, status__in=["issued", "sent"]
    ).aggregate(total=Sum("amount"))["total"] or 0

    overdue_invoices = Invoice.objects.filter(
        office=office, status="overdue"
    ).aggregate(total=Sum("amount"))["total"] or 0

    return {
        "contracts_total": contracts_total,
        "active_contracts": active_contracts,
        "monthly_revenue": monthly_revenue,
        "monthly_expenses": monthly_expenses,
        "pending_invoices": pending_invoices,
        "overdue_invoices": overdue_invoices,
    }


@cached_metric("documentos_dashboard", ttl=300)
def get_documentos_metrics(office):
    """Métricas do dashboard de documentos — cacheado por 5 min."""
    from django.db.models import Sum, Count
    from apps.documents.models import Document

    base_qs = Document.objects.filter(office=office)

    total = base_qs.count()
    total_size = base_qs.aggregate(total=Sum("file_size"))["total"] or 0
    total_size_mb = round(total_size / (1024 * 1024), 2)
    by_category = list(
        base_qs.values("category").annotate(count=Count("id")).order_by("-count")
    )
    by_status = list(base_qs.values("status").annotate(count=Count("id")))

    return {
        "total": total,
        "total_size_mb": total_size_mb,
        "by_category": by_category,
        "by_status": by_status,
    }