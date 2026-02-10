from __future__ import annotations
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.db.models.functions import TruncMonth
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, HttpRequest, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from apps.portal.decorators import require_portal_access, require_portal_json
from apps.documents.models import Document, DocumentVersion, DocumentShare, DocumentComment, Folder, DocumentFolder
from apps.portal.forms import PortalLoginForm, SupportTicketForm
from apps.portal.models import (
    OfficePreference, ActivityLog, SupportTicket,
    CalendarEntry, CalendarEventTemplate,
    KanbanBoard, KanbanColumn, KanbanCard,
    ChatThread, ChatMember, ChatMessage,
)
from apps.finance.models import FeeAgreement, Invoice, Payment, Expense
from apps.customers.models import Customer, CustomerInteraction, CustomerDocument
from apps.processes.models import Process, ProcessParty
from apps.memberships.models import Membership
from apps.offices.models import Office
from apps.accounts.models import User
from apps.publications.models import (
    Publication, JudicialEvent, PublicationRule,
    PublicationImport, PublicationFilter
)
from datetime import timedelta
import csv
import json
import io
from django.http import HttpResponse
from openpyxl import Workbook

#logger = logging.getLogger(__name__)

def landing(request):
    if request.user.is_authenticated and not (request.user.is_staff or request.user.is_superuser):
        return redirect("portal:dashboard")
    return render(request, "portal/landing.html")

@require_http_methods(["GET", "POST"])
def portal_login(request):
    if request.user.is_authenticated:
        return redirect("portal:dashboard")
    form = PortalLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.cleaned_data["user"]
        login(request, user)
        return redirect("portal:dashboard")
    return render(request, "portal/login.html", {"form": form})

@login_required
def portal_logout(request):
    logout(request)
    return redirect("portal:login")

def _ensure_portal_user(request: HttpRequest):
    if not request.user.is_authenticated:
        return redirect("portal:login")
    if request.user.is_staff or request.user.is_superuser:
        return HttpResponseForbidden("Conta administrativa não pode acessar o portal.")
    return None

def _ensure_office(request: HttpRequest):
    # org_admin sem office selecionado deve escolher
    membership = getattr(request, "membership", None)
    if membership and membership.role == "org_admin" and getattr(request, "office", None) is None:
        offices = list(request.organization.offices.all().order_by("name"))
        return render(request, "portal/choose_office.html", {"offices": offices, "active_page": ""})
    if getattr(request, "office", None) is None:
        return HttpResponseForbidden("Sem escritório no contexto.")
    return None

@login_required
def set_office(request, office_id: int):
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    org = getattr(request, "organization", None)
    office = get_object_or_404(Office, id=office_id, organization=org)
    request.session["office_id"] = office.id
    return redirect("portal:dashboard")

@login_required
def dashboard(request):
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    office = request.office

    customers_qs = Customer.objects.for_request(request).filter(office=office)
    processes_qs = Process.objects.for_request(request).filter(office=office)
    team_qs = Membership.objects.filter(organization=request.organization, office=office, is_active=True)
    # tarefas pendentes = cards fora de colunas "Done"/"Concluído"
    board, _ = KanbanBoard.objects.get_or_create(organization=request.organization, office=office)
    done_cols = KanbanColumn.objects.filter(board=board, title__iregex=r"^(done|conclu[ií]do|finalizado)$")
    pending_tasks = KanbanCard.objects.filter(board=board).exclude(column__in=done_cols).count()

    counts = {
        "customers": customers_qs.count(),
        "processes": processes_qs.count(),
        "team": team_qs.count(),
        "pending_tasks": pending_tasks,
    }
    latest_processes = processes_qs.order_by("-id")[:5]
    return render(request, "portal/dashboard.html", {"counts": counts, "latest_processes": latest_processes, "active_page":"dashboard"})




# Views Processos
@login_required
def processos(request):
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    # Filtros
    search = request.GET.get('search', '')
    phase = request.GET.get('phase', '')
    status = request.GET.get('status', '')
    
    qs = Process.objects.for_request(request).filter(office=request.office)
    
    if search:
        qs = qs.filter(
            models.Q(number__icontains=search) |
            models.Q(subject__icontains=search) |
            models.Q(court__icontains=search)
        )
    
    if phase:
        qs = qs.filter(phase=phase)
    
    if status:
        qs = qs.filter(status=status)
    
    qs = qs.order_by('-created_at')
    
    # Paginação
    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    page = request.GET.get('page', 1)
    processes = paginator.get_page(page)
    
    # Choices para filtros
    phase_choices = [
        ('initial', 'Inicial'),
        ('instruction', 'Instrução'),
        ('sentence', 'Sentença'),
        ('appeal', 'Recurso'),
        ('execution', 'Execução'),
        ('archived', 'Arquivado'),
    ]
    
    status_choices = [
        ('active', 'Ativo'),
        ('suspended', 'Suspenso'),
        ('finished', 'Finalizado'),
    ]
    
    return render(request, "portal/processos.html", {
        "processes": processes,
        "search": search,
        "phase": phase,
        "status": status,
        "phase_choices": phase_choices,
        "status_choices": status_choices,
        "active_page": "processos"
    })

@login_required
@require_http_methods(["GET", "POST"])
def processo_create(request):
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    from apps.processes.forms import ProcessForm
    
    if request.method == "POST":
        form = ProcessForm(request.POST)
        
        if form.is_valid():
            process = form.save(commit=False)
            process.organization = request.organization
            process.office = request.office
            
            try:
                process.save()
                
                ActivityLog.objects.create(
                    organization=request.organization,
                    office=request.office,
                    actor=request.user,
                    verb="process_create",
                    description=f"Novo processo: {process.number}"
                )
                
                messages.success(request, f"Processo {process.number} criado com sucesso!")
                return redirect('portal:processo_detail', process.id)
                
            except Exception as e:
                messages.error(request, f"Erro ao salvar processo: {str(e)}")
        else:
            # Mostra erros do form
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
    else:
        form = ProcessForm()
    
    return render(request, "portal/processo_form.html", {
        "form": form,
        "active_page": "processos"
    })

@login_required
def processo_detail(request, process_id):
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    process = get_object_or_404(Process, id=process_id, office=request.office)
    parties = process.parties.select_related('customer').all()   

    # Prazos relacionados
    from apps.deadlines.models import Deadline
    from django.contrib.contenttypes.models import ContentType
    ct = ContentType.objects.get_for_model(Process)
    deadlines = Deadline.objects.filter(
        office=request.office,
        content_type=ct,
        object_id=process.id
    ).order_by('due_date')
    
    # Documentos relacionados
    from apps.documents.models import Document
    ct_doc = ContentType.objects.get_for_model(Process)
    documents = Document.objects.filter(
        office=request.office
    )[:10]  # Simplificado
    
    return render(request, "portal/processo_detail.html", {
        "process": process,
        "parties": parties,
        "deadlines": deadlines,
        "documents": documents,
        "active_page": "processos"
    })

@login_required
@require_http_methods(["POST"])
def processo_delete(request, process_id):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    process = get_object_or_404(Process, id=process_id, office=request.office)
    number = process.number
    process.delete()
    
    ActivityLog.objects.create(
        organization=request.organization,
        office=request.office,
        actor=request.user,
        verb="process_delete",
        description=f"Processo deletado: {number}"
    )
    
    return JsonResponse({"ok": True})

# Fim Views processos


# Contatos Views
# ==================== DASHBOARD CONTATOS ====================

@login_required
def contatos_dashboard(request):
    """Dashboard CRM com estatísticas"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    office = request.office
    
    # Estatísticas
    total = Customer.objects.filter(office=office, is_deleted=False).count()
    by_status = Customer.objects.filter(office=office, is_deleted=False).values('status').annotate(count=Count('id'))
    by_type = Customer.objects.filter(office=office, is_deleted=False).values('type').annotate(count=Count('id'))
    by_origin = Customer.objects.filter(office=office, is_deleted=False).values('origin').annotate(count=Count('id')).order_by('-count')[:5]
    
    # Conversões (lead -> cliente)
    leads = Customer.objects.filter(office=office, status='lead', is_deleted=False).count()
    clients = Customer.objects.filter(office=office, status='client', is_deleted=False).count()
    conversion_rate = (clients / leads * 100) if leads > 0 else 0
    
    # Recentes
    recent = Customer.objects.filter(office=office, is_deleted=False).order_by('-created_at')[:10]
    
    # Interações recentes
    recent_interactions = CustomerInteraction.objects.filter(
        office=office
    ).select_related('customer', 'created_by').order_by('-date')[:10]
    
    # Top tags
    all_customers = Customer.objects.filter(office=office, is_deleted=False).exclude(tags='')
    tags_count = {}
    for c in all_customers:
        for tag in c.tag_list:
            tags_count[tag] = tags_count.get(tag, 0) + 1
    top_tags = sorted(tags_count.items(), key=lambda x: x[1], reverse=True)[:10]
    
    context = {
        'total': total,
        'by_status': list(by_status),
        'by_type': list(by_type),
        'by_origin': list(by_origin),
        'leads': leads,
        'clients': clients,
        'conversion_rate': conversion_rate,
        'recent': recent,
        'recent_interactions': recent_interactions,
        'top_tags': top_tags,
        'active_page': 'contatos'
    }
    
    return render(request, 'portal/contatos_dashboard.html', context)


# ==================== LISTA E CRUD ====================

@login_required
def contatos(request):
    """Lista de contatos com filtros avançados"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    # Filtros
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    type_filter = request.GET.get('type', '')
    origin_filter = request.GET.get('origin', '')
    tag_filter = request.GET.get('tag', '')
    
    qs = Customer.objects.filter(office=request.office, is_deleted=False).select_related('responsible')
    
    if search:
        qs = qs.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search) |
            Q(document__icontains=search)
        )
    
    if status_filter:
        qs = qs.filter(status=status_filter)
    
    if type_filter:
        qs = qs.filter(type=type_filter)
    
    if origin_filter:
        qs = qs.filter(origin=origin_filter)
    
    if tag_filter:
        qs = qs.filter(tags__icontains=tag_filter)
    
    qs = qs.order_by('-created_at')
    
    # Paginação
    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    page = request.GET.get('page', 1)
    customers = paginator.get_page(page)
    
    # Todas as tags para filtro
    all_tags = set()
    for c in Customer.objects.filter(office=request.office, is_deleted=False).exclude(tags=''):
        all_tags.update(c.tag_list)
    
    context = {
        'customers': customers,
        'search': search,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'origin_filter': origin_filter,
        'tag_filter': tag_filter,
        'status_choices': Customer.STATUS_CHOICES,
        'type_choices': Customer.TYPE_CHOICES,
        'origin_choices': Customer.ORIGIN_CHOICES,
        'all_tags': sorted(all_tags),
        'active_page': 'contatos'
    }
    
    return render(request, 'portal/contatos.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def contato_create(request):
    """Criar contato"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    if request.method == "POST":
        data = request.POST
        
        try:
            customer = Customer.objects.create(
                organization=request.organization,
                office=request.office,
                name=data.get('name', '').strip(),
                document=data.get('document', '').strip(),
                type=data.get('type', 'PF'),
                status=data.get('status', 'lead'),
                email=data.get('email', '').strip(),
                phone=data.get('phone', '').strip(),
                phone_secondary=data.get('phone_secondary', '').strip(),
                whatsapp=data.get('whatsapp', '').strip(),
                address_street=data.get('address_street', '').strip(),
                address_number=data.get('address_number', '').strip(),
                address_complement=data.get('address_complement', '').strip(),
                address_neighborhood=data.get('address_neighborhood', '').strip(),
                address_city=data.get('address_city', '').strip(),
                address_state=data.get('address_state', '').strip(),
                address_zipcode=data.get('address_zipcode', '').strip(),
                profession=data.get('profession', '').strip(),
                company_name=data.get('company_name', '').strip(),
                origin=data.get('origin', 'other'),
                referral_name=data.get('referral_name', '').strip(),
                tags=data.get('tags', '').strip(),
                notes=data.get('notes', '').strip(),
                responsible=request.user,
                first_contact_date=timezone.now().date()
            )
            
            ActivityLog.objects.create(
                organization=request.organization,
                office=request.office,
                actor=request.user,
                verb="customer_create",
                description=f"Novo contato: {customer.name}"
            )
            
            messages.success(request, f"Contato {customer.name} criado com sucesso!")
            return redirect('portal:contato_detail', customer.id)
            
        except Exception as e:
            messages.error(request, f"Erro ao criar contato: {str(e)}")
    
    context = {
        'status_choices': Customer.STATUS_CHOICES,
        'type_choices': Customer.TYPE_CHOICES,
        'origin_choices': Customer.ORIGIN_CHOICES,
        'active_page': 'contatos'
    }
    
    return render(request, 'portal/contato_form.html', context)


@login_required
def contato_detail(request, customer_id):
    """Detalhes do contato"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    customer = get_object_or_404(
        Customer.objects.select_related('responsible'),
        id=customer_id,
        office=request.office,
        is_deleted=False
    )
    
    # Interações
    interactions = customer.interactions.select_related('created_by').order_by('-date')[:20]
    
    # Documentos
    documents = customer.customer_documents.select_related('uploaded_by').order_by('-created_at')
    
    # Processos vinculados
    from apps.processes.models import ProcessParty
    process_parties = ProcessParty.objects.filter(customer=customer).select_related('process')
    
    # Contratos
    from apps.finance.models import FeeAgreement
    agreements = FeeAgreement.objects.filter(customer=customer, office=request.office).order_by('-created_at')
    
    context = {
        'customer': customer,
        'interactions': interactions,
        'documents': documents,
        'process_parties': process_parties,
        'agreements': agreements,
        'interaction_type_choices': CustomerInteraction.TYPE_CHOICES,
        'document_type_choices': CustomerDocument.TYPE_CHOICES,
        'active_page': 'contatos'
    }
    
    return render(request, 'portal/contato_detail.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def contato_edit(request, customer_id):
    """Editar contato"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    customer = get_object_or_404(Customer, id=customer_id, office=request.office, is_deleted=False)
    
    if request.method == "POST":
        data = request.POST
        
        try:
            customer.name = data.get('name', '').strip()
            customer.document = data.get('document', '').strip()
            customer.type = data.get('type', 'PF')
            customer.status = data.get('status', 'lead')
            customer.email = data.get('email', '').strip()
            customer.phone = data.get('phone', '').strip()
            customer.phone_secondary = data.get('phone_secondary', '').strip()
            customer.whatsapp = data.get('whatsapp', '').strip()
            customer.address_street = data.get('address_street', '').strip()
            customer.address_number = data.get('address_number', '').strip()
            customer.address_complement = data.get('address_complement', '').strip()
            customer.address_neighborhood = data.get('address_neighborhood', '').strip()
            customer.address_city = data.get('address_city', '').strip()
            customer.address_state = data.get('address_state', '').strip()
            customer.address_zipcode = data.get('address_zipcode', '').strip()
            customer.profession = data.get('profession', '').strip()
            customer.company_name = data.get('company_name', '').strip()
            customer.origin = data.get('origin', 'other')
            customer.referral_name = data.get('referral_name', '').strip()
            customer.tags = data.get('tags', '').strip()
            customer.notes = data.get('notes', '').strip()
            customer.internal_notes = data.get('internal_notes', '').strip()
            
            customer.save()
            
            messages.success(request, "Contato atualizado com sucesso!")
            return redirect('portal:contato_detail', customer.id)
            
        except Exception as e:
            messages.error(request, f"Erro ao atualizar: {str(e)}")
    
    context = {
        'customer': customer,
        'status_choices': Customer.STATUS_CHOICES,
        'type_choices': Customer.TYPE_CHOICES,
        'origin_choices': Customer.ORIGIN_CHOICES,
        'active_page': 'contatos'
    }
    
    return render(request, 'portal/contato_form.html', context)


@login_required
@require_http_methods(["POST"])
def contato_delete(request, customer_id):
    """Deletar (soft delete) contato"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    customer = get_object_or_404(Customer, id=customer_id, office=request.office)
    name = customer.name
    customer.soft_delete()
    
    ActivityLog.objects.create(
        organization=request.organization,
        office=request.office,
        actor=request.user,
        verb="customer_delete",
        description=f"Contato deletado: {name}"
    )
    
    return JsonResponse({"ok": True})


# ==================== INTERAÇÕES ====================

@login_required
@require_http_methods(["POST"])
def contato_interaction_create(request, customer_id):
    """Criar interação (JSON)"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    customer = get_object_or_404(Customer, id=customer_id, office=request.office, is_deleted=False)
    
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    
    from django.utils.dateparse import parse_datetime
    date = parse_datetime(payload.get('date') + 'T' + payload.get('time', '12:00'))
    
    interaction = CustomerInteraction.objects.create(
        organization=request.organization,
        office=request.office,
        customer=customer,
        type=payload.get('type', 'note'),
        date=date or timezone.now(),
        subject=payload.get('subject', '').strip(),
        description=payload.get('description', '').strip(),
        created_by=request.user
    )
    
    # Atualiza última interação
    customer.last_interaction_date = timezone.now().date()
    customer.save(update_fields=['last_interaction_date'])
    
    return JsonResponse({
        "ok": True,
        "interaction": {
            "id": interaction.id,
            "type": interaction.get_type_display(),
            "date": interaction.date.strftime('%d/%m/%Y %H:%M'),
            "subject": interaction.subject
        }
    })


# ==================== IMPORTAÇÃO/EXPORTAÇÃO ====================

@login_required
def contatos_export(request):
    """Exportar contatos para Excel"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    customers = Customer.objects.filter(office=request.office, is_deleted=False).order_by('name')
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Contatos"
    
    # Cabeçalhos
    headers = [
        'Nome', 'CPF/CNPJ', 'Tipo', 'Status', 'Email', 'Telefone',
        'Endereço', 'Cidade', 'Estado', 'CEP', 'Origem', 'Tags', 'Criado em'
    ]
    ws.append(headers)
    
    # Dados
    for c in customers:
        ws.append([
            c.name,
            c.document,
            c.get_type_display(),
            c.get_status_display(),
            c.email,
            c.phone,
            c.full_address,
            c.address_city,
            c.address_state,
            c.address_zipcode,
            c.get_origin_display(),
            c.tags,
            c.created_at.strftime('%d/%m/%Y')
        ])
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=contatos.xlsx'
    wb.save(response)
    
    return response


@login_required
@require_http_methods(["POST"])
def contatos_import(request):
    """Importar contatos de CSV"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    if 'file' not in request.FILES:
        return JsonResponse({"error": "Nenhum arquivo enviado"}, status=400)
    
    file = request.FILES['file']
    
    try:
        decoded_file = file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        created = 0
        errors = []
        
        for row in reader:
            try:
                Customer.objects.create(
                    organization=request.organization,
                    office=request.office,
                    name=row.get('nome', '').strip(),
                    document=row.get('cpf_cnpj', '').strip(),
                    type=row.get('tipo', 'PF'),
                    email=row.get('email', '').strip(),
                    phone=row.get('telefone', '').strip(),
                    status='lead',
                    responsible=request.user
                )
                created += 1
            except Exception as e:
                errors.append(f"Linha {reader.line_num}: {str(e)}")
        
        return JsonResponse({
            "ok": True,
            "created": created,
            "errors": errors
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

# Fim Contatos Views

@login_required
def agenda(request):
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    templates = CalendarEventTemplate.objects.filter(office=request.office, is_active=True).order_by("title")
    return render(request, "portal/agenda.html", {"templates": templates, "active_page":"agenda"})

#Tarefas e Kanban

@login_required
def kanban(request):
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    return render(request, "portal/tasks_kanban.html", {"active_page":"kanban"})

@login_required
def task_list(request):
    """
    Lista de Tarefas — view principal (usa KanbanCards como backend por ora).
    """
    forbid = _ensure_portal_user(request)
    if forbid:
        return forbid
    must = _ensure_office(request)
    if must:
        return must

    from django.core.paginator import Paginator
    from django.db import models as django_models

    search   = request.GET.get("search", "").strip()
    status_f = request.GET.get("status", "")

    board, _ = KanbanBoard.objects.get_or_create(
        organization=request.organization,
        office=request.office,
    )

    cards_qs = KanbanCard.objects.filter(board=board).select_related("column")

    if search:
        cards_qs = cards_qs.filter(
            django_models.Q(title__icontains=search) |
            django_models.Q(body_md__icontains=search)
        )

    STATUS_MAP = {
        "backlog":      "todo",
        "to do":        "todo",
        "a fazer":      "todo",
        "in progress":  "doing",
        "em andamento": "doing",
        "fazendo":      "doing",
        "done":         "done",
        "concluído":    "done",
        "finalizado":   "done",
        "blocked":      "blocked",
        "bloqueado":    "blocked",
    }

    card_list = []
    for c in cards_qs.order_by("column__order", "order"):
        col_key    = c.column.title.lower().strip()
        c._status      = STATUS_MAP.get(col_key, "todo")
        c._column_name = c.column.title
        if status_f and c._status != status_f:
            continue
        card_list.append(c)

    paginator = Paginator(card_list, settings.PORTAL_PAGINATION_SIZE)
    page      = request.GET.get("page", 1)
    tasks     = paginator.get_page(page)

    STATUS_CHOICES = [
        ("todo",    "A fazer"),
        ("doing",   "Em andamento"),
        ("blocked", "Bloqueada"),
        ("done",    "Concluída"),
    ]

    return render(request, "portal/tasks_list.html", {
        "tasks":          tasks,
        "search":         search,
        "status_f":       status_f,
        "priority_f":     "",
        "assigned_f":     "",
        "due_filter":     "",
        "status_choices": STATUS_CHOICES,
        "priority_choices": [],
        "members":        [],
        "active_page":    "tarefas",   # ← "tarefas", não "kanban"
        "today":          __import__("django.utils.timezone", fromlist=["timezone"]).timezone.now().date(),
    })

# Fim Tarefas e Kanban

@login_required
@require_http_methods(["GET", "POST"])
def support_new(request):
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must

    if request.method == "POST":
        form = SupportTicketForm(request.POST)
        if form.is_valid():
            membership = request.membership
            # roteamento
            if membership.role in ("lawyer", "staff", "finance"):
                target = "office_admin"
            elif membership.role == "office_admin":
                target = "org_admin"
            else:
                target = "platform_admin"
            SupportTicket.objects.create(
                organization=request.organization,
                office=request.office,
                created_by=request.user,
                target=target,
                subject=form.cleaned_data["subject"],
                message=form.cleaned_data["message"],
            )
            messages.success(request, "Chamado enviado.")
            return redirect("portal:support_new")
    return render(request, "portal/support_new.html", {"active_page":"support"})

@login_required
def support_inbox(request):
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must

    membership = request.membership
    if membership.role == "office_admin":
        qs = SupportTicket.objects.filter(office=request.office, target="office_admin")
    elif membership.role == "org_admin":
        qs = SupportTicket.objects.filter(organization=request.organization, target="org_admin")
    else:
        qs = SupportTicket.objects.none()
    return render(request, "portal/support_inbox.html", {"tickets": qs[:200], "active_page":"support_inbox"})

@login_required
@require_http_methods(["GET", "POST"])
def settings_view(request):
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must

    tab = request.GET.get("tab", "appearance")
    office = request.office
    pref, _ = OfficePreference.objects.get_or_create(office=office)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "theme":
            theme = request.POST.get("theme", "default")
            if theme not in ("default","dark","light"):
                theme = "default"
            pref.theme = theme
            pref.save()
            messages.success(request, "Tema atualizado.")
            return redirect(f"{request.path}?tab=appearance")

    return render(request, "portal/settings.html", {"tab": tab, "theme": pref.theme, "active_page":"settings"})

# ---------------------------
# JSON endpoints
# ---------------------------

@login_required
def global_search(request):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    must = _ensure_office(request)
    if must and not isinstance(must, HttpResponseForbidden):
        return JsonResponse({"error":"office_required"}, status=400)
    
    q = (request.GET.get("q") or "").strip()
    results = []
    
    if not q:
        return JsonResponse({"results": []})
    
    office = request.office
    
    # ✅ Processos (com ID na URL)
    for p in Process.objects.for_request(request).filter(office=office, number__icontains=q)[:5]:
        results.append({
            "type": "processo",
            "label": p.number,
            "icon": "fas fa-balance-scale",
            "url": f"/app/processos/{p.id}/"  # ✅ Agora inclui o ID
        })
    
    # Contatos
    for c in Customer.objects.for_request(request).filter(office=office, name__icontains=q)[:5]:
        results.append({
            "type": "contato",
            "label": c.name,
            "icon": "fas fa-users",
            "url": "/app/contatos/"
        })
    
    # Tarefas
    for t in KanbanCard.objects.filter(board__office=office, title__icontains=q)[:5]:
        results.append({
            "type": "tarefa",
            "label": f"#{t.number} {t.title}",
            "icon": "fas fa-tasks",
            "url": "/app/tarefas/"
        })
    
    return JsonResponse({"results": results[:12]})

@login_required
def notifications_json(request):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    must = _ensure_office(request)
    if must and not isinstance(must, HttpResponseForbidden):
        return JsonResponse({"error":"office_required"}, status=400)
    office = request.office
    items = []
    logs = ActivityLog.objects.filter(office=office).order_by("-created_at")[:6]
    for l in logs:
        items.append({"text": l.description, "when": l.created_at.strftime("%H:%M")})
    return JsonResponse({"count": len(items), "items": items})

# Calendar events
@login_required
def calendar_events_json(request):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse([], safe=False, status=403)
    must = _ensure_office(request)
    if must and not isinstance(must, HttpResponseForbidden):
        return JsonResponse([], safe=False, status=400)
    office = request.office
    evs = CalendarEntry.objects.filter(office=office)
    out = []
    for e in evs:
        out.append({
            "id": e.id,
            "title": e.title,
            "start": e.start.isoformat(),
            "end": e.end.isoformat() if e.end else None,
            "allDay": e.all_day,
            "backgroundColor": e.color,
            "borderColor": e.color,
        })
    return JsonResponse(out, safe=False)

@login_required
@require_http_methods(["POST"])
def calendar_event_create(request):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error":"office_required"}, status=400)
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    title = (payload.get("title") or "").strip()[:120]
    start = payload.get("start")
    all_day = bool(payload.get("all_day"))
    color = (payload.get("color") or "#3c8dbc")[:24]
    if not title or not start:
        return JsonResponse({"error":"invalid"}, status=400)
    from django.utils.dateparse import parse_datetime
    from datetime import datetime
    dt = parse_datetime(start)
    if dt is None:
        # date-only
        from django.utils.dateparse import parse_date
        d = parse_date(start)
        if not d: return JsonResponse({"error":"invalid_date"}, status=400)
        dt = datetime.combine(d, datetime.min.time())
    CalendarEntry.objects.create(
        organization=request.organization,
        office=request.office,
        title=title,
        start=dt,
        all_day=all_day,
        color=color,
        created_by=request.user,
    )
    ActivityLog.objects.create(organization=request.organization, office=request.office, actor=request.user, verb="calendar_create", description=f"Novo evento: {title}")
    return JsonResponse({"ok": True})

@login_required
@require_http_methods(["POST"])
def calendar_event_update(request, event_id: int):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error":"office_required"}, status=400)
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    e = get_object_or_404(CalendarEntry, id=event_id, office=request.office)
    from django.utils.dateparse import parse_datetime
    start = parse_datetime(payload.get("start") or "") if payload.get("start") else None
    end = parse_datetime(payload.get("end") or "") if payload.get("end") else None
    if start: e.start = start
    e.end = end
    e.all_day = bool(payload.get("all_day"))
    e.save()
    return JsonResponse({"ok": True})

@login_required
@require_http_methods(["POST"])
def calendar_event_delete(request, event_id: int):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error":"office_required"}, status=400)
    e = get_object_or_404(CalendarEntry, id=event_id, office=request.office)
    e.delete()
    return JsonResponse({"ok": True})

# Calendar templates
@login_required
def calendar_templates_list(request):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error":"office_required"}, status=400)
    items = [{"id":t.id,"title":t.title,"color":t.color} for t in CalendarEventTemplate.objects.filter(office=request.office, is_active=True)]
    return JsonResponse({"items": items})

@login_required
@require_http_methods(["POST"])
def calendar_template_create(request):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error":"office_required"}, status=400)
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    title = (payload.get("title") or "").strip()[:120]
    color = (payload.get("color") or "#3c8dbc")[:24]
    if not title:
        return JsonResponse({"error":"invalid"}, status=400)
    CalendarEventTemplate.objects.create(organization=request.organization, office=request.office, title=title, color=color)
    return JsonResponse({"ok": True})

@login_required
@require_http_methods(["POST"])
def calendar_template_delete(request, tpl_id: int):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error":"office_required"}, status=400)
    t = get_object_or_404(CalendarEventTemplate, id=tpl_id, office=request.office)
    t.delete()
    return JsonResponse({"ok": True})

# Kanban JSON
@login_required
def kanban_board_json(request):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error":"office_required"}, status=400)
    board, _ = KanbanBoard.objects.get_or_create(organization=request.organization, office=request.office)
    # seed default columns
    if board.columns.count() == 0:
        KanbanColumn.objects.bulk_create([
            KanbanColumn(board=board, title="Backlog", order=0),
            KanbanColumn(board=board, title="To Do", order=1),
            KanbanColumn(board=board, title="In Progress", order=2),
            KanbanColumn(board=board, title="Done", order=3),
        ])
    columns = []
    for col in board.columns.all():
        cards = []
        for c in col.cards.all().order_by("order","id"):
            preview = (c.body_md or "").replace("\n"," ")
            if len(preview) > 140: preview = preview[:140] + "…"
            cards.append({"id": c.id, "number": c.number, "title": c.title, "body_preview": preview})
        columns.append({"id": col.id, "title": col.title, "cards": cards})
    return JsonResponse({"board_id": board.id, "columns": columns})

@login_required
@require_http_methods(["POST"])
def kanban_column_create(request):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error":"office_required"}, status=400)
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    title = (payload.get("title") or "").strip()[:120]
    if not title:
        return JsonResponse({"error":"invalid"}, status=400)
    board, _ = KanbanBoard.objects.get_or_create(organization=request.organization, office=request.office)
    order = board.columns.count()
    KanbanColumn.objects.create(board=board, title=title, order=order)
    return JsonResponse({"ok": True})

@login_required
@require_http_methods(["POST"])
def kanban_column_update(request, col_id: int):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error":"office_required"}, status=400)
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    title = (payload.get("title") or "").strip()[:120]
    col = get_object_or_404(KanbanColumn, id=col_id, board__office=request.office)
    col.title = title
    col.save()
    return JsonResponse({"ok": True})

@login_required
@require_http_methods(["POST"])
def kanban_column_delete(request, col_id: int):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error":"office_required"}, status=400)
    col = get_object_or_404(KanbanColumn, id=col_id, board__office=request.office)
    col.delete()
    return JsonResponse({"ok": True})

@login_required
@require_http_methods(["POST"])
def kanban_card_create(request):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error":"office_required"}, status=400)
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    col_id = int(payload.get("column_id"))
    title = (payload.get("title") or "").strip()[:120]
    number = int(payload.get("number"))
    body_md = (payload.get("body_md") or "")
    col = get_object_or_404(KanbanColumn, id=col_id, board__office=request.office)
    board = col.board
    order = col.cards.count()
    try:
        KanbanCard.objects.create(board=board, column=col, title=title, number=number, body_md=body_md, order=order, created_by=request.user)
    except Exception as e:
        return JsonResponse({"error":"duplicate_or_invalid"}, status=400)
    ActivityLog.objects.create(organization=request.organization, office=request.office, actor=request.user, verb="task_create", description=f"Nova tarefa: #{number} {title}")
    return JsonResponse({"ok": True})

@login_required
@require_http_methods(["POST"])
def kanban_card_update(request, card_id: int):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error":"office_required"}, status=400)
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    card = get_object_or_404(KanbanCard, id=card_id, board__office=request.office)
    title = (payload.get("title") or "").strip()[:120]
    number = int(payload.get("number"))
    body_md = payload.get("body_md") or ""
    card.title = title
    card.number = number
    card.body_md = body_md
    try:
        card.save()
    except Exception:
        return JsonResponse({"error":"duplicate_or_invalid"}, status=400)
    return JsonResponse({"ok": True})

@login_required
@require_http_methods(["POST"])
def kanban_card_move(request):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error":"office_required"}, status=400)
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    card = get_object_or_404(KanbanCard, id=int(payload.get("card_id")), board__office=request.office)
    col = get_object_or_404(KanbanColumn, id=int(payload.get("column_id")), board=card.board)
    card.column = col
    card.order = int(payload.get("order") or 0)
    card.save()
    return JsonResponse({"ok": True})

@login_required
def kanban_card_detail(request, card_id: int):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error":"office_required"}, status=400)
    card = get_object_or_404(KanbanCard, id=card_id, board__office=request.office)
    return JsonResponse({"id": card.id, "title": card.title, "number": card.number, "body_md": card.body_md})

# Chat
@login_required
def chat_threads(request):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error":"office_required"}, status=400)
    threads = ChatThread.objects.filter(organization=request.organization, members__user=request.user).distinct().order_by("-created_at")[:50]
    data = []
    for t in threads:
        title = t.title or "Chat"
        if t.type == "direct" and not t.title:
            others = t.members.exclude(user=request.user).select_related("user")
            if others.exists():
                title = others.first().user.get_full_name() or others.first().user.email
        data.append({"id": t.id, "title": title})
    return JsonResponse({"threads": data})

@login_required
@require_http_methods(["POST"])
def chat_thread_create(request):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error":"office_required"}, status=400)
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    title = (payload.get("title") or "").strip()[:120]
    emails = payload.get("emails") or []
    # restringe ao mesmo escritório atual
    users = list(User.objects.filter(email__in=emails, memberships__office=request.office, memberships__is_active=True).distinct())
    thread = ChatThread.objects.create(organization=request.organization, office=request.office, type="group", title=title or "Grupo", created_by=request.user)
    ChatMember.objects.create(thread=thread, user=request.user)
    for u in users:
        if u.id != request.user.id:
            ChatMember.objects.get_or_create(thread=thread, user=u)
    return JsonResponse({"thread_id": thread.id})

@login_required
def chat_messages(request, thread_id: int):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    thread = get_object_or_404(ChatThread, id=thread_id, organization=request.organization)
    if not ChatMember.objects.filter(thread=thread, user=request.user).exists():
        return JsonResponse({"error":"forbidden"}, status=403)
    after_id = int(request.GET.get("after_id") or 0)
    qs = thread.messages.all()
    if after_id:
        qs = qs.filter(id__gt=after_id)
    msgs = []
    for m in qs.order_by("id")[:200]:
        sender = m.sender.get_full_name() if m.sender else "Sistema"
        msgs.append({"id": m.id, "sender": sender, "when": m.created_at.strftime("%H:%M"), "body": m.body})
    return JsonResponse({"messages": msgs})

@login_required
@require_http_methods(["POST"])
def chat_send(request, thread_id: int):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error":"forbidden"}, status=403)
    thread = get_object_or_404(ChatThread, id=thread_id, organization=request.organization)
    if not ChatMember.objects.filter(thread=thread, user=request.user).exists():
        return JsonResponse({"error":"forbidden"}, status=403)
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    body = (payload.get("body") or "").strip()
    if not body:
        return JsonResponse({"error":"empty"}, status=400)
    ChatMessage.objects.create(thread=thread, sender=request.user, body=body)
    return JsonResponse({"ok": True})


# Prazos Views

from apps.deadlines.models import Deadline
from django.utils import timezone
from datetime import timedelta

@login_required
def prazos(request):
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    # Filtros
    search = request.GET.get('search', '')
    tipo = request.GET.get('type', '')
    priority = request.GET.get('priority', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    qs = Deadline.objects.for_request(request).filter(office=request.office)
    
    if search:
        qs = qs.filter(
            models.Q(title__icontains=search) |
            models.Q(description__icontains=search)
        )
    
    if tipo:
        qs = qs.filter(type=tipo)
    
    if priority:
        qs = qs.filter(priority=priority)
    
    # Status calculado (vencido, pendente, concluído)
    today = timezone.now().date()
    
    if status_filter == 'overdue':
        qs = qs.filter(due_date__lt=today)
    elif status_filter == 'today':
        qs = qs.filter(due_date=today)
    elif status_filter == 'week':
        qs = qs.filter(due_date__gte=today, due_date__lte=today + timedelta(days=7))
    
    if date_from:
        from django.utils.dateparse import parse_date
        df = parse_date(date_from)
        if df:
            qs = qs.filter(due_date__gte=df)
    
    if date_to:
        from django.utils.dateparse import parse_date
        dt = parse_date(date_to)
        if dt:
            qs = qs.filter(due_date__lte=dt)
    
    qs = qs.order_by('due_date')
    
    # Paginação
    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    page = request.GET.get('page', 1)
    deadlines = paginator.get_page(page)
    
    # Adiciona status dinâmico
    for d in deadlines:
        if d.due_date < today:
            d.status_label = 'overdue'
            d.status_text = 'Atrasado'
            d.status_class = 'danger'
        elif d.due_date == today:
            d.status_label = 'today'
            d.status_text = 'Vence hoje'
            d.status_class = 'warning'
        elif d.due_date <= today + timedelta(days=3):
            d.status_label = 'soon'
            d.status_text = 'Próximo'
            d.status_class = 'info'
        else:
            d.status_label = 'future'
            d.status_text = 'Futuro'
            d.status_class = 'secondary'
    
    type_choices = Deadline._meta.get_field('type').choices
    priority_choices = Deadline._meta.get_field('priority').choices
    
    return render(request, "portal/prazos.html", {
        "deadlines": deadlines,
        "search": search,
        "tipo": tipo,
        "priority": priority,
        "status_filter": status_filter,
        "date_from": date_from,
        "date_to": date_to,
        "type_choices": type_choices,
        "priority_choices": priority_choices,
        "active_page": "prazos"
    })

@login_required
@require_http_methods(["POST"])
def prazo_create(request):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    
    title = (payload.get('title') or '').strip()
    due_date = payload.get('due_date')
    tipo = payload.get('type', 'task')
    priority = payload.get('priority', 'medium')
    description = payload.get('description', '')
    process_id = payload.get('process_id')
    responsible_id = payload.get('responsible_id')
    
    if not title or not due_date:
        return JsonResponse({"error": "Título e data são obrigatórios"}, status=400)
    
    from django.utils.dateparse import parse_date
    due_date_obj = parse_date(due_date)
    if not due_date_obj:
        return JsonResponse({"error": "Data inválida"}, status=400)
    
    deadline = Deadline.objects.create(
        organization=request.organization,
        office=request.office,
        title=title,
        due_date=due_date_obj,
        type=tipo,
        priority=priority,
        description=description
    )
    
    # Vincula a processo se fornecido
    if process_id:
        try:
            from django.contrib.contenttypes.models import ContentType
            process = Process.objects.get(id=process_id, office=request.office)
            ct = ContentType.objects.get_for_model(Process)
            deadline.content_type = ct
            deadline.object_id = process.id
            deadline.save()
        except Process.DoesNotExist:
            pass  # Ignora se processo não existe
    
    # Atribui responsável
    if responsible_id:
        try:
            from apps.accounts.models import User
            user = User.objects.get(id=responsible_id)
            deadline.responsible = user
            deadline.save()
        except:
            pass
    
    ActivityLog.objects.create(
        organization=request.organization,
        office=request.office,
        actor=request.user,
        verb="deadline_create",
        description=f"Novo prazo: {title}"
    )
    
    return JsonResponse({
        "ok": True,
        "deadline": {
            "id": deadline.id,
            "title": deadline.title,
            "due_date": deadline.due_date.isoformat()
        }
    })

@login_required
@require_http_methods(["POST"])
def prazo_update(request, prazo_id):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    deadline = get_object_or_404(Deadline, id=prazo_id, office=request.office)
    
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    
    title = (payload.get('title') or '').strip()
    due_date = payload.get('due_date')
    tipo = payload.get('type')
    priority = payload.get('priority')
    description = payload.get('description')
    process_id = payload.get('process_id')
    responsible_id = payload.get('responsible_id')
    
    if title:
        deadline.title = title
    if due_date:
        from django.utils.dateparse import parse_date
        due_date_obj = parse_date(due_date)
        if due_date_obj:
            deadline.due_date = due_date_obj
    if tipo:
        deadline.type = tipo
    if priority:
        deadline.priority = priority
    if description is not None:
        deadline.description = description
    
    # ✅ Atualiza vinculação com processo
    if 'process_id' in payload:
        if process_id:
            try:
                from django.contrib.contenttypes.models import ContentType
                process = Process.objects.get(id=process_id, office=request.office)
                ct = ContentType.objects.get_for_model(Process)
                deadline.content_type = ct
                deadline.object_id = process.id
            except Process.DoesNotExist:
                pass
        else:
            # Remove vinculação se process_id for null
            deadline.content_type = None
            deadline.object_id = None

    # Atualiza responsável
    if 'responsible_id' in payload:
        if responsible_id:
            try:
                from apps.accounts.models import User
                deadline.responsible = User.objects.get(id=responsible_id)
            except User.DoesNotExist:
                pass
        else:
            deadline.responsible = None
    
    deadline.save()
    
    return JsonResponse({"ok": True})

@login_required
@require_http_methods(["POST"])
def prazo_delete(request, prazo_id):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    deadline = get_object_or_404(Deadline, id=prazo_id, office=request.office)
    title = deadline.title
    deadline.delete()
    
    ActivityLog.objects.create(
        organization=request.organization,
        office=request.office,
        actor=request.user,
        verb="deadline_delete",
        description=f"Prazo deletado: {title}"
    )
    
    return JsonResponse({"ok": True})

@login_required
def prazo_detail(request, prazo_id):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    deadline = get_object_or_404(Deadline, id=prazo_id, office=request.office)
    
    # ✅ Retorna process_id se vinculado
    process_id = None
    if deadline.content_type and deadline.object_id:
        from django.contrib.contenttypes.models import ContentType
        ct_process = ContentType.objects.get_for_model(Process)
        if deadline.content_type == ct_process:
            process_id = deadline.object_id
    
    return JsonResponse({
        "id": deadline.id,
        "title": deadline.title,
        "due_date": deadline.due_date.isoformat(),
        "type": deadline.type,
        "priority": deadline.priority,
        "description": deadline.description or "",
        "responsible_id": deadline.responsible_id,
        "process_id": process_id  # ✅ Adiciona process_id
    })

@login_required
def prazos_calendar(request):
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    return render(request, "portal/prazos_calendar.html", {
        "active_page": "prazos"
    })

@login_required
def prazos_calendar_json(request):
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse([], safe=False, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse([], safe=False, status=400)
    
    deadlines = Deadline.objects.for_request(request).filter(office=request.office)
    
    today = timezone.now().date()
    events = []
    
    for d in deadlines:
        # Cor baseada em prioridade e status
        if d.due_date < today:
            color = '#dc3545'  # Vermelho (atrasado)
        elif d.priority == 'urgent':
            color = '#dc3545'  # Vermelho
        elif d.priority == 'high':
            color = '#fd7e14'  # Laranja
        elif d.priority == 'medium':
            color = '#ffc107'  # Amarelo
        else:
            color = '#28a745'  # Verde
        
        events.append({
            "id": d.id,
            "title": d.title,
            "start": d.due_date.isoformat(),
            "backgroundColor": color,
            "borderColor": color,
            "extendedProps": {
                "type": d.type,
                "priority": d.priority
            }
        })
    
    return JsonResponse(events, safe=False)


# Fim prazos views

# Finance Views

# ==================== DASHBOARD FINANCEIRO ====================

@login_required
def financeiro_dashboard(request):
    """Dashboard financeiro com KPIs e gráficos"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    office = request.office
    today = timezone.now().date()
    
    # Período do filtro (padrão: mês atual)
    period = request.GET.get('period', 'month')
    
    if period == 'month':
        start_date = today.replace(day=1)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    elif period == 'quarter':
        quarter = (today.month - 1) // 3
        start_date = today.replace(month=quarter * 3 + 1, day=1)
        end_date = (start_date + timedelta(days=93)).replace(day=1) - timedelta(days=1)
    elif period == 'year':
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
    else:  # all
        start_date = None
        end_date = None
    
    # Receitas (faturas pagas)
    invoices_qs = Invoice.objects.filter(office=office)
    if start_date:
        invoices_qs = invoices_qs.filter(issue_date__gte=start_date, issue_date__lte=end_date)
    
    total_invoiced = invoices_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_received = Payment.objects.filter(
        invoice__office=office,
        paid_at__gte=start_date if start_date else today.replace(year=2000)
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Despesas
    expenses_qs = Expense.objects.filter(office=office, status='paid')
    if start_date:
        expenses_qs = expenses_qs.filter(date__gte=start_date, date__lte=end_date)
    
    total_expenses = expenses_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Lucro
    profit = total_received - total_expenses
    profit_margin = (profit / total_received * 100) if total_received > 0 else 0
    
    # A receber (faturas pendentes)
    pending_invoices = Invoice.objects.filter(
        office=office,
        status__in=['issued', 'sent', 'overdue']
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # Vencidas
    overdue_invoices = Invoice.objects.filter(
        office=office,
        status='overdue'
    ).count()
    
    # Gráfico mensal (últimos 6 meses)
    six_months_ago = today - timedelta(days=180)
    monthly_data = Payment.objects.filter(
        invoice__office=office,
        paid_at__gte=six_months_ago
    ).annotate(
        month=TruncMonth('paid_at')
    ).values('month').annotate(
        receitas=Sum('amount')
    ).order_by('month')
    
    monthly_expenses = Expense.objects.filter(
        office=office,
        status='paid',
        date__gte=six_months_ago
    ).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        despesas=Sum('amount')
    ).order_by('month')
    
    # Combinar dados mensais
    months_dict = {}
    for item in monthly_data:
        key = item['month'].strftime('%Y-%m')
        months_dict[key] = {
            'month': item['month'].strftime('%b/%y'),
            'receitas': float(item['receitas']),
            'despesas': 0
        }
    
    for item in monthly_expenses:
        key = item['month'].strftime('%Y-%m')
        if key in months_dict:
            months_dict[key]['despesas'] = float(item['despesas'])
        else:
            months_dict[key] = {
                'month': item['month'].strftime('%b/%y'),
                'receitas': 0,
                'despesas': float(item['despesas'])
            }
    
    chart_data = list(months_dict.values())
    
    # Top clientes
    top_customers = FeeAgreement.objects.filter(
        office=office,
        status='active'
    ).values('customer__name').annotate(
        total=Sum('amount')
    ).order_by('-total')[:5]
    
    # Despesas por categoria
    expenses_by_category = Expense.objects.filter(
        office=office,
        status='paid'
    ).values('category').annotate(
        total=Sum('amount')
    ).order_by('-total')[:5]
    
    context = {
        'period': period,
        'total_invoiced': total_invoiced,
        'total_received': total_received,
        'total_expenses': total_expenses,
        'profit': profit,
        'profit_margin': profit_margin,
        'pending_invoices': pending_invoices,
        'overdue_invoices': overdue_invoices,
        'chart_data_json': json.dumps(chart_data),
        'top_customers': top_customers,
        'expenses_by_category': expenses_by_category,
        'active_page': 'financeiro'
    }
    
    return render(request, 'portal/financeiro_dashboard.html', context)


# ==================== CONTRATOS ====================

@login_required
def financeiro_contratos(request):
    """Lista de contratos de honorários"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    # Filtros
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    billing_type = request.GET.get('billing_type', '')
    
    qs = FeeAgreement.objects.filter(office=request.office).select_related('customer', 'process')
    
    if search:
        qs = qs.filter(
            Q(title__icontains=search) |
            Q(customer__name__icontains=search) |
            Q(description__icontains=search)
        )
    
    if status_filter:
        qs = qs.filter(status=status_filter)
    
    if billing_type:
        qs = qs.filter(billing_type=billing_type)
    
    qs = qs.order_by('-created_at')
    
    # Paginação
    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    page = request.GET.get('page', 1)
    agreements = paginator.get_page(page)
    
    # Adiciona dados computados
    for agr in agreements:
        agr.total_received_amount = agr.total_received
        agr.balance_amount = agr.balance
    
    context = {
        'agreements': agreements,
        'search': search,
        'status_filter': status_filter,
        'billing_type': billing_type,
        'status_choices': FeeAgreement.STATUS_CHOICES,
        'billing_type_choices': FeeAgreement.BILLING_TYPE_CHOICES,
        'active_page': 'financeiro'
    }
    
    return render(request, 'portal/financeiro_contratos.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def financeiro_contrato_create(request):
    """Criar contrato de honorários"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    if request.method == "POST":
        data = request.POST
        
        # Validações básicas
        customer_id = data.get('customer_id')
        title = data.get('title', '').strip()
        amount = data.get('amount')
        
        if not customer_id or not title or not amount:
            messages.error(request, "Cliente, título e valor são obrigatórios")
            return redirect('portal:financeiro_contrato_create')
        
        try:
            customer = Customer.objects.get(id=customer_id, office=request.office)
            
            agreement = FeeAgreement.objects.create(
                organization=request.organization,
                office=request.office,
                customer=customer,
                title=title,
                description=data.get('description', ''),
                amount=Decimal(amount),
                billing_type=data.get('billing_type', 'one_time'),
                installments=int(data.get('installments', 1)),
                status=data.get('status', 'draft'),
                notes=data.get('notes', ''),
                responsible=request.user
            )
            
            # Vincula processo se informado
            process_id = data.get('process_id')
            if process_id:
                try:
                    process = Process.objects.get(id=process_id, office=request.office)
                    agreement.process = process
                    agreement.save()
                except Process.DoesNotExist:
                    pass
            
            ActivityLog.objects.create(
                organization=request.organization,
                office=request.office,
                actor=request.user,
                verb="agreement_create",
                description=f"Novo contrato: {title}"
            )
            
            messages.success(request, "Contrato criado com sucesso!")
            return redirect('portal:financeiro_contrato_detail', agreement.id)
            
        except Exception as e:
            messages.error(request, f"Erro ao criar contrato: {str(e)}")
    
    # GET - buscar clientes para dropdown
    customers = Customer.objects.filter(office=request.office).order_by('name')
    
    context = {
        'customers': customers,
        'billing_type_choices': FeeAgreement.BILLING_TYPE_CHOICES,
        'status_choices': FeeAgreement.STATUS_CHOICES,
        'active_page': 'financeiro'
    }
    
    return render(request, 'portal/financeiro_contrato_form.html', context)


@login_required
def financeiro_contrato_detail(request, agreement_id):
    """Detalhes do contrato"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    agreement = get_object_or_404(
        FeeAgreement.objects.select_related('customer', 'process'),
        id=agreement_id,
        office=request.office
    )
    
    # Faturas do contrato
    invoices = agreement.invoices.order_by('-issue_date')
    
    # Totais
    total_invoiced = agreement.total_invoiced
    total_received = agreement.total_received
    balance = agreement.balance
    
    context = {
        'agreement': agreement,
        'invoices': invoices,
        'total_invoiced': total_invoiced,
        'total_received': total_received,
        'balance': balance,
        'active_page': 'financeiro'
    }
    
    return render(request, 'portal/financeiro_contrato_detail.html', context)


# ==================== FATURAS ====================

@login_required
def financeiro_faturas(request):
    """Lista de faturas"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    # Filtros
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    qs = Invoice.objects.filter(office=request.office).select_related('agreement__customer')
    
    if search:
        qs = qs.filter(
            Q(number__icontains=search) |
            Q(agreement__customer__name__icontains=search) |
            Q(description__icontains=search)
        )
    
    if status_filter:
        qs = qs.filter(status=status_filter)
    
    if date_from:
        from django.utils.dateparse import parse_date
        df = parse_date(date_from)
        if df:
            qs = qs.filter(issue_date__gte=df)
    
    if date_to:
        from django.utils.dateparse import parse_date
        dt = parse_date(date_to)
        if dt:
            qs = qs.filter(issue_date__lte=dt)
    
    qs = qs.order_by('-issue_date')
    
    # Marca vencidas automaticamente
    today = timezone.now().date()
    for inv in qs.filter(status__in=['issued', 'sent'], due_date__lt=today):
        if inv.status != 'overdue':
            inv.status = 'overdue'
            inv.save(update_fields=['status'])
    
    # Paginação
    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    page = request.GET.get('page', 1)
    invoices = paginator.get_page(page)
    
    # Adiciona dados computados
    for inv in invoices:
        inv.paid_amount_value = inv.paid_amount
        inv.balance_value = inv.balance
    
    context = {
        'invoices': invoices,
        'search': search,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': Invoice.STATUS_CHOICES,
        'active_page': 'financeiro'
    }
    
    return render(request, 'portal/financeiro_faturas.html', context)


@login_required
@require_http_methods(["POST"])
def financeiro_fatura_create(request):
    """Criar fatura (JSON)"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    payload = json.loads(request.body.decode("utf-8") or "{}")
    
    agreement_id = payload.get('agreement_id')
    number = payload.get('number', '').strip()
    issue_date = payload.get('issue_date')
    due_date = payload.get('due_date')
    amount = payload.get('amount')
    
    if not all([agreement_id, number, issue_date, due_date, amount]):
        return JsonResponse({"error": "Campos obrigatórios faltando"}, status=400)
    
    try:
        agreement = FeeAgreement.objects.get(id=agreement_id, office=request.office)
        
        from django.utils.dateparse import parse_date
        issue_date_obj = parse_date(issue_date)
        due_date_obj = parse_date(due_date)
        
        invoice = Invoice.objects.create(
            organization=request.organization,
            office=request.office,
            agreement=agreement,
            number=number,
            issue_date=issue_date_obj,
            due_date=due_date_obj,
            amount=Decimal(amount),
            discount=Decimal(payload.get('discount', '0.00')),
            status=payload.get('status', 'draft'),
            description=payload.get('description', ''),
            notes=payload.get('notes', '')
        )
        
        ActivityLog.objects.create(
            organization=request.organization,
            office=request.office,
            actor=request.user,
            verb="invoice_create",
            description=f"Nova fatura: {number}"
        )
        
        return JsonResponse({
            "ok": True,
            "invoice": {
                "id": invoice.id,
                "number": invoice.number
            }
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def financeiro_fatura_registrar_pagamento(request, invoice_id):
    """Registrar pagamento de fatura"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    invoice = get_object_or_404(Invoice, id=invoice_id, office=request.office)
    
    payload = json.loads(request.body.decode("utf-8") or "{}")
    
    amount = payload.get('amount')
    paid_at = payload.get('paid_at')
    method = payload.get('method', 'pix')
    
    if not all([amount, paid_at]):
        return JsonResponse({"error": "Valor e data são obrigatórios"}, status=400)
    
    try:
        from django.utils.dateparse import parse_date
        paid_at_obj = parse_date(paid_at)
        
        payment = Payment.objects.create(
            organization=request.organization,
            office=request.office,
            invoice=invoice,
            amount=Decimal(amount),
            paid_at=paid_at_obj,
            method=method,
            reference=payload.get('reference', ''),
            notes=payload.get('notes', ''),
            recorded_by=request.user
        )
        
        # Atualiza status da fatura
        if invoice.balance <= 0:
            invoice.status = 'paid'
            invoice.save(update_fields=['status'])
        
        ActivityLog.objects.create(
            organization=request.organization,
            office=request.office,
            actor=request.user,
            verb="payment_create",
            description=f"Pagamento registrado: R$ {amount} - Fatura {invoice.number}"
        )
        
        return JsonResponse({"ok": True})
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ==================== DESPESAS ====================

@login_required
def financeiro_despesas(request):
    """Lista de despesas"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    # Filtros
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    qs = Expense.objects.filter(office=request.office)
    
    if search:
        qs = qs.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(supplier__icontains=search)
        )
    
    if category:
        qs = qs.filter(category=category)
    
    if status_filter:
        qs = qs.filter(status=status_filter)
    
    if date_from:
        from django.utils.dateparse import parse_date
        df = parse_date(date_from)
        if df:
            qs = qs.filter(date__gte=df)
    
    if date_to:
        from django.utils.dateparse import parse_date
        dt = parse_date(date_to)
        if dt:
            qs = qs.filter(date__lte=dt)
    
    qs = qs.order_by('-date')
    
    # Paginação
    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    page = request.GET.get('page', 1)
    expenses = paginator.get_page(page)
    
    context = {
        'expenses': expenses,
        'search': search,
        'category': category,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'category_choices': Expense.CATEGORY_CHOICES,
        'status_choices': Expense.STATUS_CHOICES,
        'active_page': 'financeiro'
    }
    
    return render(request, 'portal/financeiro_despesas.html', context)


@login_required
@require_http_methods(["POST"])
def financeiro_despesa_create(request):
    """Criar despesa (JSON)"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    payload = json.loads(request.body.decode("utf-8") or "{}")
    
    title = payload.get('title', '').strip()
    amount = payload.get('amount')
    date = payload.get('date')
    category = payload.get('category', 'other')
    
    if not all([title, amount, date]):
        return JsonResponse({"error": "Título, valor e data são obrigatórios"}, status=400)
    
    try:
        from django.utils.dateparse import parse_date
        date_obj = parse_date(date)
        
        expense = Expense.objects.create(
            organization=request.organization,
            office=request.office,
            title=title,
            description=payload.get('description', ''),
            category=category,
            date=date_obj,
            amount=Decimal(amount),
            status=payload.get('status', 'pending'),
            supplier=payload.get('supplier', ''),
            reference=payload.get('reference', ''),
            notes=payload.get('notes', ''),
            responsible=request.user
        )
        
        ActivityLog.objects.create(
            organization=request.organization,
            office=request.office,
            actor=request.user,
            verb="expense_create",
            description=f"Nova despesa: {title}"
        )
        
        return JsonResponse({
            "ok": True,
            "expense": {
                "id": expense.id,
                "title": expense.title
            }
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def financeiro_despesa_update(request, expense_id):
    """Atualizar despesa (JSON)"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    expense = get_object_or_404(Expense, id=expense_id, office=request.office)
    
    payload = json.loads(request.body.decode("utf-8") or "{}")
    
    if 'title' in payload:
        expense.title = payload['title'].strip()
    if 'amount' in payload:
        expense.amount = Decimal(payload['amount'])
    if 'date' in payload:
        from django.utils.dateparse import parse_date
        expense.date = parse_date(payload['date'])
    if 'category' in payload:
        expense.category = payload['category']
    if 'status' in payload:
        expense.status = payload['status']
    if 'description' in payload:
        expense.description = payload['description']
    if 'supplier' in payload:
        expense.supplier = payload['supplier']
    if 'reference' in payload:
        expense.reference = payload['reference']
    if 'notes' in payload:
        expense.notes = payload['notes']
    
    expense.save()
    
    return JsonResponse({"ok": True})


@login_required
@require_http_methods(["POST"])
def financeiro_despesa_delete(request, expense_id):
    """Deletar despesa"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    expense = get_object_or_404(Expense, id=expense_id, office=request.office)
    title = expense.title
    expense.delete()
    
    ActivityLog.objects.create(
        organization=request.organization,
        office=request.office,
        actor=request.user,
        verb="expense_delete",
        description=f"Despesa deletada: {title}"
    )
    
    return JsonResponse({"ok": True})


@login_required
def financeiro_despesa_detail(request, expense_id):
    """Detalhes da despesa (JSON)"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    expense = get_object_or_404(Expense, id=expense_id, office=request.office)
    
    return JsonResponse({
        "id": expense.id,
        "title": expense.title,
        "description": expense.description or "",
        "category": expense.category,
        "date": expense.date.isoformat(),
        "amount": str(expense.amount),
        "status": expense.status,
        "supplier": expense.supplier or "",
        "reference": expense.reference or "",
        "notes": expense.notes or ""
    })

# Fim finance Views

#



# ==================== DASHBOARD DOCUMENTOS ====================

@login_required
def documentos_dashboard(request):
    """Dashboard de documentos"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    office = request.office
    
    # Estatísticas
    total = Document.objects.filter(office=office).count()
    by_category = Document.objects.filter(office=office).values('category').annotate(count=Count('id')).order_by('-count')[:10]
    by_status = Document.objects.filter(office=office).values('status').annotate(count=Count('id'))
    
    # Tamanho total
    total_size = sum([d.file_size for d in Document.objects.filter(office=office)])
    total_size_mb = round(total_size / (1024 * 1024), 2)
    
    # Recentes
    recent = Document.objects.filter(office=office).select_related('uploaded_by').order_by('-created_at')[:10]
    
    # Vencidos
    from django.utils import timezone
    expired = Document.objects.filter(
        office=office,
        expiry_date__lt=timezone.now().date()
    ).order_by('expiry_date')[:10]
    
    # Templates
    templates = Document.objects.filter(office=office, is_template=True).order_by('title')[:10]
    
    # Top tags
    all_docs = Document.objects.filter(office=office).exclude(tags='')
    tags_count = {}
    for d in all_docs:
        for tag in d.tag_list:
            tags_count[tag] = tags_count.get(tag, 0) + 1
    top_tags = sorted(tags_count.items(), key=lambda x: x[1], reverse=True)[:10]
    
    context = {
        'total': total,
        'total_size_mb': total_size_mb,
        'by_category': list(by_category),
        'by_status': list(by_status),
        'recent': recent,
        'expired': expired,
        'templates': templates,
        'top_tags': top_tags,
        'active_page': 'documentos'
    }
    
    return render(request, 'portal/documentos_dashboard.html', context)


# ==================== LISTA E CRUD ====================

@login_required
def documentos(request):
    """Lista de documentos com filtros"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    # Filtros
    search = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    tag_filter = request.GET.get('tag', '')
    folder_id = request.GET.get('folder', '')
    
    qs = Document.objects.filter(office=request.office).select_related('uploaded_by', 'process', 'customer')
    
    if search:
        qs = qs.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(tags__icontains=search)
        )
    
    if category_filter:
        qs = qs.filter(category=category_filter)
    
    if status_filter:
        qs = qs.filter(status=status_filter)
    
    if tag_filter:
        qs = qs.filter(tags__icontains=tag_filter)
    
    if folder_id:
        qs = qs.filter(folder_links__folder_id=folder_id)
    
    qs = qs.order_by('-created_at')
    
    # Paginação
    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    page = request.GET.get('page', 1)
    documents = paginator.get_page(page)
    
    # Pastas
    folders = Folder.objects.filter(office=request.office, parent__isnull=True).order_by('name')
    
    # Tags
    all_tags = set()
    for d in Document.objects.filter(office=request.office).exclude(tags=''):
        all_tags.update(d.tag_list)
    
    context = {
        'documents': documents,
        'folders': folders,
        'search': search,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'tag_filter': tag_filter,
        'folder_id': folder_id,
        'category_choices': Document.CATEGORY_CHOICES,
        'status_choices': Document.STATUS_CHOICES,
        'all_tags': sorted(all_tags),
        'active_page': 'documentos'
    }
    
    return render(request, 'portal/documentos.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def documento_upload(request):
    """Upload de documento"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    if request.method == "POST":
        if 'file' not in request.FILES:
            messages.error(request, "Nenhum arquivo selecionado.")
            return redirect('portal:documento_upload')
        
        file = request.FILES['file']
        data = request.POST
        
        try:
            document = Document.objects.create(
                organization=request.organization,
                office=request.office,
                title=data.get('title', file.name).strip(),
                description=data.get('description', '').strip(),
                category=data.get('category', 'other'),
                status=data.get('status', 'draft'),
                file=file,
                tags=data.get('tags', '').strip(),
                is_confidential=data.get('is_confidential') == 'on',
                is_template=data.get('is_template') == 'on',
                uploaded_by=request.user
            )
            
            # Vincular processo
            if data.get('process_id'):
                from apps.processes.models import Process
                try:
                    process = Process.objects.get(id=data.get('process_id'), office=request.office)
                    document.process = process
                    document.save()
                except Process.DoesNotExist:
                    pass
            
            # Vincular cliente
            if data.get('customer_id'):
                from apps.customers.models import Customer
                try:
                    customer = Customer.objects.get(id=data.get('customer_id'), office=request.office)
                    document.customer = customer
                    document.save()
                except Customer.DoesNotExist:
                    pass
            
            # Adicionar a pasta
            if data.get('folder_id'):
                try:
                    folder = Folder.objects.get(id=data.get('folder_id'), office=request.office)
                    DocumentFolder.objects.create(
                        document=document,
                        folder=folder,
                        added_by=request.user
                    )
                except Folder.DoesNotExist:
                    pass
            
            ActivityLog.objects.create(
                organization=request.organization,
                office=request.office,
                actor=request.user,
                verb="document_upload",
                description=f"Upload: {document.title}"
            )
            
            messages.success(request, f"Documento {document.title} enviado com sucesso!")
            return redirect('portal:documento_detail', document.id)
            
        except Exception as e:
            messages.error(request, f"Erro ao enviar documento: {str(e)}")
    
    # GET
    folders = Folder.objects.filter(office=request.office).order_by('name')
    
    context = {
        'category_choices': Document.CATEGORY_CHOICES,
        'status_choices': Document.STATUS_CHOICES,
        'folders': folders,
        'active_page': 'documentos'
    }
    
    return render(request, 'portal/documento_upload.html', context)


@login_required
def documento_detail(request, document_id):
    """Detalhes do documento"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    document = get_object_or_404(
        Document.objects.select_related('uploaded_by', 'process', 'customer'),
        id=document_id,
        office=request.office
    )
    
    # Versões
    versions = document.versions.select_related('created_by').order_by('-version_number')
    
    # Compartilhamentos
    shares = document.shares.select_related('shared_with', 'shared_by').order_by('-created_at')
    
    # Comentários
    comments = document.comments.select_related('author').order_by('-created_at')
    
    # Pastas
    folders = document.folder_links.select_related('folder').all()
    
    context = {
        'document': document,
        'versions': versions,
        'shares': shares,
        'comments': comments,
        'folders': folders,
        'active_page': 'documentos'
    }
    
    return render(request, 'portal/documento_detail.html', context)


@login_required
def documento_download(request, document_id):
    """Download de documento"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    document = get_object_or_404(Document, id=document_id, office=request.office)
    
    ActivityLog.objects.create(
        organization=request.organization,
        office=request.office,
        actor=request.user,
        verb="document_download",
        description=f"Download: {document.title}"
    )
    
    return FileResponse(document.file.open('rb'), as_attachment=True, filename=document.file.name)


@login_required
@require_http_methods(["POST"])
def documento_delete(request, document_id):
    """Deletar documento"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    document = get_object_or_404(Document, id=document_id, office=request.office)
    title = document.title
    
    # Deletar arquivo físico
    if document.file:
        document.file.delete()
    
    document.delete()
    
    ActivityLog.objects.create(
        organization=request.organization,
        office=request.office,
        actor=request.user,
        verb="document_delete",
        description=f"Documento deletado: {title}"
    )
    
    return JsonResponse({"ok": True})


# ==================== VERSÕES ====================

@login_required
@require_http_methods(["POST"])
def documento_version_create(request, document_id):
    """Criar nova versão"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    document = get_object_or_404(Document, id=document_id, office=request.office)
    
    if 'file' not in request.FILES:
        return JsonResponse({"error": "Arquivo não enviado"}, status=400)
    
    file = request.FILES['file']
    changes = request.POST.get('changes_description', '').strip()
    
    # Próximo número de versão
    last_version = document.versions.order_by('-version_number').first()
    next_version = (last_version.version_number + 1) if last_version else 1
    
    version = DocumentVersion.objects.create(
        document=document,
        version_number=next_version,
        file=file,
        changes_description=changes,
        created_by=request.user
    )
    
    return JsonResponse({
        "ok": True,
        "version": {
            "id": version.id,
            "version_number": version.version_number,
            "created_at": version.created_at.strftime('%d/%m/%Y %H:%M')
        }
    })


@login_required
def documento_version_download(request, version_id):
    """Download de versão específica"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    version = get_object_or_404(
        DocumentVersion.objects.select_related('document'),
        id=version_id,
        document__office=request.office
    )
    
    return FileResponse(version.file.open('rb'), as_attachment=True, filename=version.file.name)


# ==================== COMPARTILHAMENTO ====================

@login_required
@require_http_methods(["POST"])
def documento_share_create(request, document_id):
    """Compartilhar documento"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    document = get_object_or_404(Document, id=document_id, office=request.office)
    
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    
    user_id = payload.get('user_id')
    can_edit = payload.get('can_edit', False)
    can_download = payload.get('can_download', True)
    
    from apps.accounts.models import User
    try:
        user = User.objects.get(id=user_id)
        
        share, created = DocumentShare.objects.get_or_create(
            organization=request.organization,
            office=request.office,
            document=document,
            shared_with=user,
            defaults={
                'shared_by': request.user,
                'can_edit': can_edit,
                'can_download': can_download
            }
        )
        
        if not created:
            share.can_edit = can_edit
            share.can_download = can_download
            share.save()
        
        return JsonResponse({"ok": True, "created": created})
        
    except User.DoesNotExist:
        return JsonResponse({"error": "Usuário não encontrado"}, status=404)


@login_required
@require_http_methods(["POST"])
def documento_share_delete(request, share_id):
    """Remover compartilhamento"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    share = get_object_or_404(DocumentShare, id=share_id, office=request.office)
    share.delete()
    
    return JsonResponse({"ok": True})


# ==================== COMENTÁRIOS ====================

@login_required
@require_http_methods(["POST"])
def documento_comment_create(request, document_id):
    """Criar comentário"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    document = get_object_or_404(Document, id=document_id, office=request.office)
    
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    
    comment_text = payload.get('comment', '').strip()
    
    if not comment_text:
        return JsonResponse({"error": "Comentário vazio"}, status=400)
    
    comment = DocumentComment.objects.create(
        organization=request.organization,
        office=request.office,
        document=document,
        author=request.user,
        comment=comment_text
    )
    
    return JsonResponse({
        "ok": True,
        "comment": {
            "id": comment.id,
            "author": comment.author.get_full_name() or comment.author.email,
            "comment": comment.comment,
            "created_at": comment.created_at.strftime('%d/%m/%Y %H:%M')
        }
    })


# ==================== PASTAS ====================

@login_required
def pastas(request):
    """Gestão de pastas"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    folders = Folder.objects.filter(office=request.office, parent__isnull=True).prefetch_related('subfolders').order_by('name')
    
    context = {
        'folders': folders,
        'active_page': 'documentos'
    }
    
    return render(request, 'portal/pastas.html', context)


@login_required
@require_http_methods(["POST"])
def pasta_create(request):
    """Criar pasta"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    
    name = payload.get('name', '').strip()
    parent_id = payload.get('parent_id')
    
    if not name:
        return JsonResponse({"error": "Nome obrigatório"}, status=400)
    
    parent = None
    if parent_id:
        try:
            parent = Folder.objects.get(id=parent_id, office=request.office)
        except Folder.DoesNotExist:
            pass
    
    folder = Folder.objects.create(
        organization=request.organization,
        office=request.office,
        name=name,
        parent=parent,
        created_by=request.user
    )
    
    return JsonResponse({
        "ok": True,
        "folder": {
            "id": folder.id,
            "name": folder.name,
            "full_path": folder.full_path
        }
    })


@login_required
@require_http_methods(["POST"])
def pasta_delete(request, folder_id):
    """Deletar pasta"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    folder = get_object_or_404(Folder, id=folder_id, office=request.office)
    
    # Verifica se tem documentos ou subpastas
    if folder.documents.exists() or folder.subfolders.exists():
        return JsonResponse({"error": "Pasta não está vazia"}, status=400)
    
    folder.delete()
    return JsonResponse({"ok": True})

    # Publicações
# ==================== DASHBOARD ====================

@login_required
def publicacoes_dashboard(request):
    """Dashboard MVP: contadores + listas simples"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    office = request.office
    
    # Contadores
    events = JudicialEvent.objects.filter(office=office)
    total_new = events.filter(status='new').count()
    total_urgent = events.filter(urgency__in=['urgent', 'critical']).count()
    total_unassigned = events.filter(assigned_to__isnull=True, status='new').count()
    
    # Prazos próximos (< 7 dias)
    from datetime import timedelta
    week_later = timezone.now().date() + timedelta(days=7)
    events_with_deadline = events.filter(deadline__isnull=False, deadline__due_date__lte=week_later).select_related('publication', 'deadline')
    
    # Publicações recentes
    recent_pubs = Publication.objects.filter(office=office).select_related('imported_by').order_by('-publication_date')[:10]
    
    # Não atribuídas
    unassigned = events.filter(assigned_to__isnull=True, status='new').select_related('publication')[:10]
    
    context = {
        'total_new': total_new,
        'total_urgent': total_urgent,
        'total_unassigned': total_unassigned,
        'events_with_deadline': events_with_deadline,
        'recent_pubs': recent_pubs,
        'unassigned': unassigned,
        'active_page': 'publicacoes'
    }
    
    return render(request, 'portal/publicacoes_dashboard.html', context)


# ==================== LISTA ====================

@login_required
def publicacoes(request):
    """Lista de eventos jurídicos (não publicações brutas)"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    # Filtros
    search = request.GET.get('search', '')
    event_type = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')
    urgency_filter = request.GET.get('urgency', '')
    assigned_filter = request.GET.get('assigned', '')
    
    qs = JudicialEvent.objects.filter(office=request.office).select_related(
        'publication', 'process', 'assigned_to', 'deadline'
    )
    
    if search:
        qs = qs.filter(
            Q(publication__raw_text__icontains=search) |
            Q(publication__process_cnj__icontains=search) |
            Q(notes__icontains=search)
        )
    
    if event_type:
        qs = qs.filter(event_type=event_type)
    
    if status_filter:
        qs = qs.filter(status=status_filter)
    
    if urgency_filter:
        qs = qs.filter(urgency=urgency_filter)
    
    if assigned_filter:
        if assigned_filter == 'unassigned':
            qs = qs.filter(assigned_to__isnull=True)
        else:
            qs = qs.filter(assigned_to_id=assigned_filter)
    
    qs = qs.order_by('-created_at')
    
    # Paginação
    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    page = request.GET.get('page', 1)
    events = paginator.get_page(page)
    
    # Usuários para filtro
    from apps.accounts.models import User
    users = User.objects.filter(memberships__office=request.office, memberships__is_active=True).distinct()
    
    context = {
        'events': events,
        'search': search,
        'event_type': event_type,
        'status_filter': status_filter,
        'urgency_filter': urgency_filter,
        'assigned_filter': assigned_filter,
        'type_choices': JudicialEvent.TYPE_CHOICES,
        'status_choices': JudicialEvent.STATUS_CHOICES,
        'urgency_choices': JudicialEvent.URGENCY_CHOICES,
        'users': users,
        'active_page': 'publicacoes'
    }
    
    return render(request, 'portal/publicacoes.html', context)


# ==================== IMPORTAÇÃO ====================

@login_required
@require_http_methods(["GET", "POST"])
def publicacao_import(request):
    """Importação manual (texto colado - MVP)"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    if request.method == "POST":
        raw_text = request.POST.get('raw_text', '').strip()
        pub_date = request.POST.get('publication_date', '')
        source = request.POST.get('source', 'manual')
        
        if not raw_text or not pub_date:
            messages.error(request, "Texto e data são obrigatórios.")
            return redirect('portal:publicacao_import')
        
        from datetime import datetime
        try:
            pub_date_obj = datetime.strptime(pub_date, '%Y-%m-%d').date()
        except:
            messages.error(request, "Data inválida.")
            return redirect('portal:publicacao_import')
        
        # Cria log de importação
        import_log = PublicationImport.objects.create(
            organization=request.organization,
            office=request.office,
            source=source,
            imported_by=request.user,
            total_found=1
        )
        
        try:
            # Cria publicação
            pub = Publication.objects.create(
                organization=request.organization,
                office=request.office,
                source=source,
                raw_text=raw_text,
                publication_date=pub_date_obj,
                imported_by=request.user
            )
            
            # Processa publicação
            from apps.publications.services import PublicationProcessor
            event = PublicationProcessor.process(pub, auto_create_event=True)
            
            # Atualiza log
            import_log.total_imported = 1
            import_log.status = 'success'
            import_log.summary = f"Publicação importada com sucesso. Evento criado: {event.get_event_type_display() if event else 'Nenhum'}"
            import_log.finished_at = timezone.now()
            import_log.save()
            
            messages.success(request, f"Publicação importada! Tipo detectado: {event.get_event_type_display() if event else 'Indefinido'}")
            return redirect('portal:publicacao_detail', pub.id)
            
        except Exception as e:
            import_log.total_errors = 1
            import_log.status = 'failed'
            import_log.error_log = str(e)
            import_log.finished_at = timezone.now()
            import_log.save()
            
            messages.error(request, f"Erro ao importar: {str(e)}")
    
    # GET: últimas importações
    recent_imports = PublicationImport.objects.filter(office=request.office).order_by('-started_at')[:10]
    
    context = {
        'recent_imports': recent_imports,
        'source_choices': Publication.SOURCE_CHOICES,
        'active_page': 'publicacoes'
    }
    
    return render(request, 'portal/publicacao_import.html', context)


# ==================== DETALHES ====================

@login_required
def publicacao_detail(request, pub_id):
    """Detalhes da publicação + eventos"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    pub = get_object_or_404(
        Publication.objects.select_related('imported_by'),
        id=pub_id,
        office=request.office
    )
    
    # Eventos jurídicos dessa publicação
    events = pub.events.select_related('process', 'assigned_to', 'deadline').order_by('-created_at')
    
    context = {
        'publication': pub,
        'events': events,
        'active_page': 'publicacoes'
    }
    
    return render(request, 'portal/publicacao_detail.html', context)


# ==================== AÇÕES JSON ====================

@login_required
@require_http_methods(["POST"])
def evento_assign(request, event_id):
    """Atribuir responsável — restrito a membros do mesmo office."""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)

    event = get_object_or_404(JudicialEvent, id=event_id, office=request.office)

    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    user_id = payload.get('user_id')

    if not user_id:
        return JsonResponse({"error": "user_id obrigatório"}, status=400)

    from apps.accounts.models import User
    # Segurança: valida que o usuário pertence ao mesmo office via memberships
    try:
        user = User.objects.filter(
            id=user_id,
            memberships__office=request.office,
            memberships__is_active=True,
        ).distinct().get()
    except User.DoesNotExist:
        return JsonResponse({"error": "Usuário não encontrado neste escritório"}, status=404)

    event.assigned_to = user
    event.assigned_at = timezone.now()
    event.status = 'assigned'
    event.save(update_fields=['assigned_to', 'assigned_at', 'status'])

    return JsonResponse({"ok": True})


@login_required
@require_http_methods(["POST"])
def evento_status(request, event_id):
    """Alterar status"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    event = get_object_or_404(JudicialEvent, id=event_id, office=request.office)
    
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    new_status = payload.get('status')
    
    if new_status not in dict(JudicialEvent.STATUS_CHOICES):
        return JsonResponse({"error": "Status inválido"}, status=400)
    
    event.status = new_status
    if new_status == 'resolved':
        event.resolved_at = timezone.now()
    event.save()
    
    return JsonResponse({"ok": True})


# ==================== REGRAS ====================

@login_required
def publicacao_rules(request):
    """Configuração de regras de prazo"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    rules = PublicationRule.objects.filter(office=request.office).order_by('-priority', 'event_type')
    
    context = {
        'rules': rules,
        'active_page': 'publicacoes'
    }
    
    return render(request, 'portal/publicacao_rules.html', context)


@login_required
@require_http_methods(["POST"])
def publicacao_rule_create(request):
    """Criar regra"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    
    try:
        rule = PublicationRule.objects.create(
            organization=request.organization,
            office=request.office,
            event_type=payload.get('event_type'),
            description=payload.get('description', ''),
            base_legal=payload.get('base_legal', ''),
            days=int(payload.get('days', 15)),
            business_days=payload.get('business_days', True),
            auto_create_deadline=payload.get('auto_create_deadline', True),
            auto_urgency=payload.get('auto_urgency', 'normal'),
        )
        
        return JsonResponse({"ok": True, "rule_id": rule.id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# ==================== FILTROS ====================

@login_required
def publicacao_filters(request):
    """Gestão de filtros/keywords"""
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    filters = PublicationFilter.objects.filter(office=request.office).order_by('filter_type', 'value')
    
    context = {
        'filters': filters,
        'filter_types': PublicationFilter.TYPE_CHOICES,
        'active_page': 'publicacoes'
    }
    
    return render(request, 'portal/publicacao_filters.html', context)


@login_required
@require_http_methods(["POST"])
def publicacao_filter_create(request):
    """Criar filtro"""
    forbid = _ensure_portal_user(request)
    if forbid: return JsonResponse({"error": "forbidden"}, status=403)
    must = _ensure_office(request)
    if must: return JsonResponse({"error": "office_required"}, status=400)
    
    import json
    payload = json.loads(request.body.decode("utf-8") or "{}")
    
    filter_obj = PublicationFilter.objects.create(
        organization=request.organization,
        office=request.office,
        filter_type=payload.get('filter_type'),
        value=payload.get('value', '').strip(),
        description=payload.get('description', ''),
    )
    
    return JsonResponse({"ok": True, "filter_id": filter_obj.id})