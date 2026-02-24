"""
Views de Processos Judiciais — completo com partes, notas, prazos e documentos via AJAX.
"""
from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods

from apps.deadlines.models import Deadline
from apps.documents.models import Document
from apps.processes.forms import ProcessForm
from apps.processes.models import Process, ProcessParty, ProcessNote
from apps.customers.models import Customer
from apps.portal.decorators import require_portal_access, require_portal_json
from apps.portal.views._helpers import log_activity, parse_json_body

from apps.shared.permissions import require_membership_perm
from apps.portal.audit import audited


# ==================== LISTA ====================

@require_portal_access()
def processos(request):
    search = request.GET.get("search", "")
    phase = request.GET.get("phase", "")
    status = request.GET.get("status", "")
    area = request.GET.get("area", "")

    qs = Process.objects.for_request(request).filter(
        office=request.office
    ).select_related("responsible")

    if search:
        qs = qs.filter(
            Q(number__icontains=search)
            | Q(subject__icontains=search)
            | Q(court__icontains=search)
            | Q(court_unit__icontains=search)
        )
    if phase:
        qs = qs.filter(phase=phase)
    if status:
        qs = qs.filter(status=status)
    if area:
        qs = qs.filter(area=area)

    qs = qs.order_by("-created_at")
    total = qs.count()
    active_count = Process.objects.for_request(request).filter(office=request.office, status="active").count()
    suspended_count = Process.objects.for_request(request).filter(office=request.office, status="suspended").count()
    finished_count = Process.objects.for_request(request).filter(office=request.office, status="finished").count()

    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    processes_page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "portal/processos.html", {
        "processes": processes_page,
        "search": search,
        "phase": phase,
        "status": status,
        "area": area,
        "phase_choices": Process.PHASE_CHOICES,
        "status_choices": Process.STATUS_CHOICES,
        "area_choices": Process.AREA_CHOICES,
        "total": total,
        "active_count": active_count,
        "suspended_count": suspended_count,
        "finished_count": finished_count,
        "active_page": "processos",
    })


# ==================== CREATE / EDIT ====================

@require_portal_access()
@require_membership_perm("processes.add_process")
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
                    label = form.fields[field].label if field in form.fields else field
                    messages.error(request, f"{label}: {error}")
    else:
        form = ProcessForm()

    return render(request, "portal/processo_form.html", {
        "form": form,
        "active_page": "processos",
    })


@require_portal_access()
@require_membership_perm("processes.change_process")
@require_http_methods(["GET", "POST"])
def processo_edit(request, process_id):
    process = get_object_or_404(
        Process,
        id=process_id,
        organization=request.organization,
        office=request.office,
    )
    if request.method == "POST":
        form = ProcessForm(request.POST, instance=process)
        if form.is_valid():
            form.save()
            log_activity(request, "process_update", f"Processo editado: {process.number}")
            messages.success(request, "Processo atualizado com sucesso!")
            return redirect("portal:processo_detail", process.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    label = form.fields[field].label if field in form.fields else field
                    messages.error(request, f"{label}: {error}")
    else:
        form = ProcessForm(instance=process)

    return render(request, "portal/processo_form.html", {
        "form": form,
        "process": process,
        "active_page": "processos",
    })


# ==================== DETAIL ====================

@require_portal_access()
def processo_detail(request, process_id):
    process = get_object_or_404(
        Process.objects.select_related("responsible"),
        id=process_id,
        organization=request.organization,
        office=request.office,
    )
    parties = process.parties.select_related("customer").order_by("role")
    notes = process.notes.select_related("author").all()

    ct = ContentType.objects.get_for_model(Process)
    deadlines = Deadline.objects.filter(
        office=request.office, content_type=ct, object_id=process.id
    ).select_related("responsible").order_by("due_date")

    documents = Document.objects.filter(
        office=request.office, process=process
    ).order_by("-created_at")[:20]

    # Usuários para selects nos modais
    try:
        from apps.accounts.models import User
        users = User.objects.filter(
            memberships__office=request.office, is_active=True
        ).distinct()
    except Exception:
        users = []

    return render(request, "portal/processo_detail.html", {
        "process": process,
        "parties": parties,
        "notes": notes,
        "deadlines": deadlines,
        "documents": documents,
        "users": users,
        "role_choices": ProcessParty.ROLE_CHOICES,
        "priority_choices": Deadline.PRIORITY_CHOICES,
        "type_choices": Deadline.TYPE_CHOICES,
        "active_page": "processos",
    })


# ==================== DELETE ====================

@require_portal_json()
@require_membership_perm("processes.delete_process")
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


# ==================== PARTES (AJAX) ====================

@require_portal_json()
@require_membership_perm("processes.change_process")
@require_http_methods(["POST"])
def processo_party_add(request, process_id):
    process = get_object_or_404(
        Process, id=process_id,
        organization=request.organization, office=request.office
    )
    payload = parse_json_body(request)

    customer_id = payload.get("customer_id")
    customer = None
    if customer_id:
        try:
            customer = Customer.objects.get(id=customer_id, organization=request.organization)
        except Customer.DoesNotExist:
            pass

    name = payload.get("name", "").strip()
    if not customer and not name:
        return JsonResponse({"error": "Informe o contato ou o nome da parte."}, status=400)

    party = ProcessParty.objects.create(
        process=process,
        customer=customer,
        name=name if not customer else "",
        role=payload.get("role", "outro"),
        document=payload.get("document", "").strip(),
        email=payload.get("email", "").strip(),
        phone=payload.get("phone", "").strip(),
        notes=payload.get("notes", "").strip(),
    )
    log_activity(request, "party_add", f"Parte adicionada ao processo {process.number}")
    return JsonResponse({
        "ok": True,
        "party": {
            "id": party.id,
            "name": party.display_name,
            "role": party.get_role_display(),
            "document": party.document,
            "email": party.email,
        }
    })


@require_portal_json()
@require_membership_perm("processes.change_process")
@require_http_methods(["POST"])
def processo_party_remove(request, process_id, party_id):
    process = get_object_or_404(Process, id=process_id, organization=request.organization, office=request.office)
    party = get_object_or_404(ProcessParty, id=party_id, process=process)
    party.delete()
    return JsonResponse({"ok": True})


# ==================== NOTAS (AJAX) ====================

@require_portal_json()
@require_membership_perm("processes.view_process")
@require_http_methods(["POST"])
def processo_note_add(request, process_id):
    process = get_object_or_404(
        Process, id=process_id,
        organization=request.organization, office=request.office
    )
    payload = parse_json_body(request)
    text = payload.get("text", "").strip()
    if not text:
        return JsonResponse({"error": "Texto da nota não pode ser vazio."}, status=400)

    note = ProcessNote.objects.create(
        process=process,
        author=request.user,
        text=text,
        is_private=payload.get("is_private", True),
    )
    return JsonResponse({
        "ok": True,
        "note": {
            "id": note.id,
            "text": note.text,
            "author": str(request.user),
            "date": note.created_at.strftime("%d/%m/%Y %H:%M"),
            "is_private": note.is_private,
        }
    })


@require_portal_json()
@require_membership_perm("processes.change_process")
@require_http_methods(["POST"])
def processo_note_delete(request, process_id, note_id):
    process = get_object_or_404(Process, id=process_id, organization=request.organization, office=request.office)
    note = get_object_or_404(ProcessNote, id=note_id, process=process)
    note.delete()
    return JsonResponse({"ok": True})


# ==================== PRAZOS (AJAX) ====================

@require_portal_json()
@require_membership_perm("deadlines.add_deadline")
@require_http_methods(["POST"])
def processo_prazo_add(request, process_id):
    process = get_object_or_404(
        Process, id=process_id,
        organization=request.organization, office=request.office
    )
    payload = parse_json_body(request)

    title = payload.get("title", "").strip()
    due_date_str = payload.get("due_date", "")
    if not title or not due_date_str:
        return JsonResponse({"error": "Título e data são obrigatórios."}, status=400)

    due_date = parse_date(due_date_str)
    if not due_date:
        return JsonResponse({"error": "Data inválida."}, status=400)

    responsible_id = payload.get("responsible_id")
    responsible = None
    if responsible_id:
        try:
            from apps.accounts.models import User
            responsible = User.objects.get(id=responsible_id)
        except Exception:
            pass

    ct = ContentType.objects.get_for_model(Process)
    deadline = Deadline.objects.create(
        organization=request.organization,
        office=request.office,
        title=title,
        description=payload.get("description", "").strip(),
        due_date=due_date,
        type=payload.get("type", "legal"),
        priority=payload.get("priority", "medium"),
        status="pending",
        content_type=ct,
        object_id=process.id,
        responsible=responsible,
    )
    log_activity(request, "deadline_add", f"Prazo adicionado ao processo {process.number}: {title}")
    return JsonResponse({
        "ok": True,
        "deadline": {
            "id": deadline.id,
            "title": deadline.title,
            "due_date": deadline.due_date.strftime("%d/%m/%Y"),
            "priority": deadline.get_priority_display(),
            "priority_key": deadline.priority,
            "responsible": str(responsible) if responsible else "—",
        }
    })


@require_portal_json()
@require_membership_perm("deadlines.change_deadline")
@require_http_methods(["POST"])
def processo_prazo_complete(request, process_id, deadline_id):
    process = get_object_or_404(Process, id=process_id, organization=request.organization, office=request.office)
    ct = ContentType.objects.get_for_model(Process)
    deadline = get_object_or_404(Deadline, id=deadline_id, content_type=ct, object_id=process.id, office=request.office)
    deadline.status = "completed"
    deadline.save(update_fields=["status"])
    return JsonResponse({"ok": True})


# ==================== DOCUMENTOS (AJAX) ====================

@require_portal_json()
@require_membership_perm("documents.add_document")
@require_http_methods(["POST"])
def processo_documento_upload(request, process_id):
    process = get_object_or_404(
        Process, id=process_id,
        organization=request.organization, office=request.office
    )
    file = request.FILES.get("file")
    if not file:
        return JsonResponse({"error": "Nenhum arquivo enviado."}, status=400)

    title = request.POST.get("title", "").strip() or file.name

    doc = Document.objects.create(
        organization=request.organization,
        office=request.office,
        process=process,
        title=title,
        file=file,
        uploaded_by=request.user,
    )
    log_activity(request, "document_upload", f"Documento adicionado ao processo {process.number}: {title}")
    return JsonResponse({
        "ok": True,
        "document": {
            "id": doc.id,
            "title": doc.title,
            "url": doc.file.url if doc.file else "",
            "date": doc.created_at.strftime("%d/%m/%Y"),
        }
    })


# ==================== AUTOCOMPLETE CONTATOS ====================

@require_portal_json()
def processo_buscar_contatos(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})

    qs = Customer.objects.filter(
        organization=request.organization,
        office=request.office,
        is_deleted=False,
    ).filter(
        Q(name__icontains=q) | Q(document__icontains=q) | Q(email__icontains=q)
    )[:10]

    results = [{"id": c.id, "text": c.name, "document": c.document or "", "type": c.get_type_display()} for c in qs]
    return JsonResponse({"results": results})
