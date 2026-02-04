from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, HttpRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator

from apps.portal.forms import PortalLoginForm, SupportTicketForm
from apps.portal.models import (
    OfficePreference, ActivityLog, SupportTicket,
    CalendarEntry, CalendarEventTemplate,
    KanbanBoard, KanbanColumn, KanbanCard,
    ChatThread, ChatMember, ChatMessage,
)
from apps.customers.models import Customer
from apps.processes.models import Process, ProcessParty
from apps.memberships.models import Membership
from apps.offices.models import Office
from apps.accounts.models import User

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
    paginator = Paginator(qs, 25)
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
    
    if request.method == "POST":
        number = request.POST.get('number', '').strip()
        court = request.POST.get('court', '').strip()
        subject = request.POST.get('subject', '').strip()
        phase = request.POST.get('phase', 'initial')
        status = request.POST.get('status', 'active')
        
        if not number:
            messages.error(request, "Número do processo é obrigatório.")
            return redirect('portal:processo_create')
        
        process = Process.objects.create(
            organization=request.organization,
            office=request.office,
            number=number,
            court=court,
            subject=subject,
            phase=phase,
            status=status
        )
        
        # Partes (simplificado - depois pode melhorar)
        ActivityLog.objects.create(
            organization=request.organization,
            office=request.office,
            actor=request.user,
            verb="process_create",
            description=f"Novo processo: {number}"
        )
        
        messages.success(request, f"Processo {number} criado com sucesso!")
        return redirect('portal:processo_detail', process.id)
    
    phase_choices = [
        ('initial', 'Inicial'),
        ('instruction', 'Instrução'),
        ('sentence', 'Sentença'),
        ('appeal', 'Recurso'),
        ('execution', 'Execução'),
    ]
    
    return render(request, "portal/processo_form.html", {
        "phase_choices": phase_choices,
        "active_page": "processos"
    })

@login_required
def processo_detail(request, process_id):
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    
    process = get_object_or_404(Process, id=process_id, office=request.office)
    parties = process.parties.all()
    
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



@login_required
def contatos(request):
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    customers = Customer.objects.for_request(request).filter(office=request.office).order_by("-id")[:200]
    return render(request, "portal/contatos.html", {"customers": customers, "active_page":"contatos"})

@login_required
def agenda(request):
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    templates = CalendarEventTemplate.objects.filter(office=request.office, is_active=True).order_by("title")
    return render(request, "portal/agenda.html", {"templates": templates, "active_page":"agenda"})

@login_required
def kanban(request):
    forbid = _ensure_portal_user(request)
    if forbid: return forbid
    must = _ensure_office(request)
    if must: return must
    return render(request, "portal/kanban.html", {"active_page":"kanban"})

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
    # processos
    for p in Process.objects.for_request(request).filter(office=office, number__icontains=q)[:5]:
        results.append({"type":"processo","label":p.number, "icon":"fas fa-balance-scale", "url":"/app/processos/"})
    for c in Customer.objects.for_request(request).filter(office=office, name__icontains=q)[:5]:
        results.append({"type":"contato","label":c.name, "icon":"fas fa-users", "url":"/app/contatos/"})
    for t in KanbanCard.objects.filter(board__office=office, title__icontains=q)[:5]:
        results.append({"type":"tarefa","label":f"#{t.number} {t.title}", "icon":"fas fa-tasks", "url":"/app/tarefas/"})
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
