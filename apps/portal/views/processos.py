"""
Views de Processos Judiciais.
"""
from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db import models
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from apps.deadlines.models import Deadline
from apps.documents.models import Document
from apps.processes.forms import ProcessForm
from apps.processes.models import Process
from apps.portal.decorators import require_portal_access, require_portal_json
from apps.portal.views._helpers import log_activity

from apps.portal.permissions import require_role, require_action
from apps.portal.audit import audited


@require_portal_access()
def processos(request):
    search = request.GET.get("search", "")
    phase = request.GET.get("phase", "")
    status = request.GET.get("status", "")

    qs = Process.objects.for_request(request).filter(office=request.office)

    if search:
        qs = qs.filter(
            models.Q(number__icontains=search)
            | models.Q(subject__icontains=search)
            | models.Q(court__icontains=search)
        )
    if phase:
        qs = qs.filter(phase=phase)
    if status:
        qs = qs.filter(status=status)

    qs = qs.order_by("-created_at")

    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    page = request.GET.get("page", 1)
    processes_page = paginator.get_page(page)

    phase_choices = [
        ("initial", "Inicial"),
        ("instruction", "Instrução"),
        ("sentence", "Sentença"),
        ("appeal", "Recurso"),
        ("execution", "Execução"),
        ("archived", "Arquivado"),
    ]
    status_choices = [
        ("active", "Ativo"),
        ("suspended", "Suspenso"),
        ("finished", "Finalizado"),
    ]

    return render(request, "portal/processos.html", {
        "processes": processes_page,
        "search": search,
        "phase": phase,
        "status": status,
        "phase_choices": phase_choices,
        "status_choices": status_choices,
        "active_page": "processos",
    })


@require_portal_access()
@require_role("lawyer")
@require_http_methods(["GET", "POST"])
def processo_create(request):
    if request.method == "POST":
        form = ProcessForm(request.POST)
        if form.is_valid():
            process = form.save(commit=False)
            process.organization = request.organization
            process.office = request.office
            try:
                process.save()
                log_activity(request, "process_create", f"Novo processo: {process.number}")
                messages.success(request, f"Processo {process.number} criado com sucesso!")
                return redirect("portal:processo_detail", process.id)
            except Exception as e:
                messages.error(request, f"Erro ao salvar processo: {e}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
    else:
        form = ProcessForm()

    return render(request, "portal/processo_form.html", {
        "form": form,
        "active_page": "processos",
    })


@require_portal_access()
def processo_detail(request, process_id):
    process = get_object_or_404(
        Process,
        id=process_id,
        organization=request.organization,
        office=request.office,
    )
    parties = process.parties.select_related("customer").all()

    ct = ContentType.objects.get_for_model(Process)
    deadlines = Deadline.objects.filter(
        office=request.office, content_type=ct, object_id=process.id
    ).order_by("due_date")

    documents = Document.objects.filter(
        office=request.office, process=process
    ).order_by("-created_at")[:10]

    return render(request, "portal/processo_detail.html", {
        "process": process,
        "parties": parties,
        "deadlines": deadlines,
        "documents": documents,
        "active_page": "processos",
    })


@require_portal_json()
@require_role("manager")
@audited(action="delete", model_name="Process")
@require_http_methods(["POST"])
def processo_delete(request, process_id):
    process = get_object_or_404(
        Process,
        id=process_id,
        organization=request.organization,
        office=request.office,
    )
    number = process.number
    process.delete()
    log_activity(request, "process_delete", f"Processo deletado: {number}")
    return JsonResponse({"ok": True})