from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(name='apps.publications.tasks.sync_all_monitoring_datajud')
def sync_all_monitoring_datajud():
    """Sincroniza todos os processos monitorados via DataJud."""
    from apps.publications.models import ProcessMonitoring
    from apps.publications.services import SyncService

    monitorings = ProcessMonitoring.objects.filter(is_active=True).select_related('process')
    total = monitorings.count()
    imported = 0

    for m in monitorings:
        if 'datajud' in (m.sources or []) or 'all' in (m.sources or []):
            try:
                stats = SyncService.sync_process_datajud(m)
                imported += stats.get('imported', 0)
            except Exception as e:
                logger.error(f'Erro ao sincronizar DataJud {m.process_cnj}: {e}')

    return {'monitored': total, 'imported': imported}


@shared_task(name='apps.publications.tasks.sync_comunica_all_orgs')
def sync_comunica_all_orgs():
    """Baixa o caderno diário da Comunica API para todas as orgs ativas."""
    from django.db.models import Q
    from apps.publications.models import ProcessMonitoring
    from apps.publications.services import SyncService

    active = ProcessMonitoring.objects.filter(
        is_active=True
    ).filter(
        Q(sources__contains='comunica') | Q(sources__contains='all')
    ).values_list('organization_id', 'office_id').distinct()

    results = []
    for org_id, office_id in active:
        try:
            from apps.organizations.models import Organization
            from apps.offices.models import Office
            org = Organization.objects.get(id=org_id)
            office = Office.objects.get(id=office_id)
            stats = SyncService.sync_comunica_daily(org, office)
            results.append({'org': org_id, **stats})
        except Exception as e:
            logger.error(f'Erro Comunica org={org_id}: {e}')
            results.append({'org': org_id, 'error': str(e)})

    return results
