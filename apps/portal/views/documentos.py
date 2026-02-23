"""
Views de Documentos — upload, versionamento, compartilhamento, pastas.
CORRIGIDO para campos reais dos models.

Campos reais:
  Document: title, description, category, status, file, file_size, file_extension,
            tags, process, customer, uploaded_by, is_confidential, is_template,
            document_date, expiry_date
            (SEM: original_filename, mime_type, folder FK)
  DocumentVersion: document, version_number, file, file_size,
                   changes_description (não change_summary), created_by, created_at
                   (SEM: organization, office, original_filename, mime_type, uploaded_by)
  DocumentShare: document, shared_with, shared_by, can_edit, can_download,
                 expires_at, access_count, last_accessed_at
                 (SEM: permission field — usa can_edit/can_download)
  DocumentComment: document, author, comment (não text), created_at
  Folder: name, description, parent, color, icon, created_by
  DocumentFolder: document, folder, added_at, added_by (M2M join table)
"""
import os

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.http import FileResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods

from apps.documents.models import (
    Document, DocumentVersion, DocumentShare, DocumentComment,
    Folder, DocumentFolder,
)
from apps.customers.models import Customer
from apps.processes.models import Process
from apps.portal.decorators import require_portal_access, require_portal_json
from apps.portal.forms import DocumentUploadForm
from apps.portal.views._helpers import parse_json_body, log_activity

from apps.shared.permissions import require_role, require_action
from apps.portal.audit import audited


def _collect_doc_tags(qs, limit=10):
    counts: dict[str, int] = {}
    for tags_str in qs.exclude(tags="").values_list("tags", flat=True):
        for tag in (t.strip() for t in tags_str.split(",") if t.strip()):
            counts[tag] = counts.get(tag, 0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]


# ==================== DASHBOARD ====================

@require_portal_access()
def documentos_dashboard(request):
    office = request.office
    base_qs = Document.objects.filter(office=office)

    total = base_qs.count()
    by_category = list(base_qs.values("category").annotate(count=Count("id")).order_by("-count"))
    by_status = list(base_qs.values("status").annotate(count=Count("id")))

    total_size = base_qs.aggregate(total=Sum("file_size"))["total"] or 0
    total_size_mb = round(total_size / (1024 * 1024), 2)

    recent = base_qs.select_related("uploaded_by").order_by("-created_at")[:10]
    top_tags = _collect_doc_tags(base_qs)

    return render(request, "portal/documentos_dashboard.html", {
        "total": total,
        "by_category": by_category,
        "by_status": by_status,
        "total_size_mb": total_size_mb,
        "recent": recent,
        "top_tags": top_tags,
        "active_page": "documentos",
    })


# ==================== LISTA ====================

@require_portal_access()
def documentos(request):
    search = request.GET.get("search", "")
    category = request.GET.get("category", "")
    status_filter = request.GET.get("status", "")
    tag_filter = request.GET.get("tag", "")
    folder_id = request.GET.get("folder", "")

    qs = Document.objects.filter(
        organization=request.organization,
        office=request.office,
    ).select_related("uploaded_by", "process", "customer")

    if search:
        qs = qs.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )
    if category:
        qs = qs.filter(category=category)
    if status_filter:
        qs = qs.filter(status=status_filter)
    if tag_filter:
        qs = qs.filter(tags__icontains=tag_filter)
    if folder_id:
        qs = qs.filter(folder_links__folder_id=folder_id)

    qs = qs.order_by("-created_at")

    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    documents_page = paginator.get_page(request.GET.get("page", 1))

    all_tags = set()
    for tags_str in Document.objects.filter(
        office=request.office
    ).exclude(tags="").values_list("tags", flat=True):
        all_tags.update(t.strip() for t in tags_str.split(",") if t.strip())

    folders = Folder.objects.filter(
        office=request.office, parent__isnull=True
    ).order_by("name")

    return render(request, "portal/documentos.html", {
        "documents": documents_page,
        "search": search,
        "category": category,
        "status_filter": status_filter,
        "tag_filter": tag_filter,
        "folder_id": folder_id,
        "all_tags": sorted(all_tags),
        "folders": folders,
        "category_choices": Document.CATEGORY_CHOICES,
        "status_choices": Document.STATUS_CHOICES,
        "active_page": "documentos",
    })


# ==================== UPLOAD ====================

@require_portal_access()
@require_role("assistant")
@require_http_methods(["GET", "POST"])
def documento_upload(request):
    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.organization = request.organization
            doc.office = request.office
            doc.uploaded_by = request.user

            # Links opcionais
            process_id = form.cleaned_data.get("process_id")
            customer_id = form.cleaned_data.get("customer_id")
            folder_id = form.cleaned_data.get("folder_id")

            if process_id:
                try:
                    doc.process = Process.objects.get(
                        id=process_id, organization=request.organization, office=request.office
                    )
                except Process.DoesNotExist:
                    pass

            if customer_id:
                try:
                    doc.customer = Customer.objects.get(
                        id=customer_id, organization=request.organization, office=request.office
                    )
                except Customer.DoesNotExist:
                    pass

            try:
                doc.save()  # save() auto-calcula file_size e file_extension

                # Vincula a pasta via M2M (DocumentFolder)
                if folder_id:
                    try:
                        folder = Folder.objects.get(
                            id=folder_id, office=request.office
                        )
                        DocumentFolder.objects.create(
                            document=doc,
                            folder=folder,
                            added_by=request.user,
                        )
                    except Folder.DoesNotExist:
                        pass

                log_activity(request, "document_upload", f"Documento: {doc.title}")
                messages.success(request, f"Documento '{doc.title}' enviado com sucesso!")
                return redirect("portal:documento_detail", doc.id)
            except Exception as e:
                messages.error(request, f"Erro ao salvar documento: {e}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    label = form.fields.get(field, None)
                    label = label.label if label else field
                    messages.error(request, f"{label}: {error}")
    else:
        form = DocumentUploadForm()

    processes = Process.objects.filter(office=request.office).order_by("-created_at")[:50]
    customers = Customer.objects.filter(
        office=request.office, is_deleted=False
    ).order_by("name")[:50]
    folders = Folder.objects.filter(office=request.office).order_by("name")

    return render(request, "portal/documento_upload.html", {
        "form": form,
        "processes": processes,
        "customers": customers,
        "folders": folders,
        "category_choices": Document.CATEGORY_CHOICES,
        "status_choices": Document.STATUS_CHOICES,
        "active_page": "documentos",
    })


# ==================== DETAIL / DOWNLOAD ====================

@require_portal_access()
def documento_detail(request, document_id):
    doc = get_object_or_404(
        Document.objects.select_related("uploaded_by", "process", "customer"),
        id=document_id,
        organization=request.organization,
        office=request.office,
    )
    versions = doc.versions.select_related("created_by").order_by("-version_number")
    shares = doc.shares.select_related("shared_with", "shared_by").order_by("-created_at")
    comments = doc.comments.select_related("author").order_by("-created_at")
    folders = doc.folder_links.select_related("folder").all()

    return render(request, "portal/documento_detail.html", {
        "document": doc,
        "versions": versions,
        "shares": shares,
        "comments": comments,
        "folders": folders,
        "active_page": "documentos",
    })


@require_portal_access()
def documento_download(request, document_id):
    doc = get_object_or_404(
        Document,
        id=document_id,
        organization=request.organization,
        office=request.office,
    )
    if not doc.file:
        messages.error(request, "Arquivo não encontrado.")
        return redirect("portal:documento_detail", doc.id)

    filename = doc.filename or doc.title
    response = FileResponse(doc.file.open("rb"), as_attachment=True, filename=filename)
    log_activity(request, "document_download", f"Download: {doc.title}")
    return response


@require_portal_access()
def documento_version_download(request, version_id):
    version = get_object_or_404(
        DocumentVersion.objects.select_related("document"),
        id=version_id,
        document__organization=request.organization,
        document__office=request.office,
    )
    if not version.file:
        messages.error(request, "Arquivo não encontrado.")
        return redirect("portal:documento_detail", version.document_id)

    filename = os.path.basename(version.file.name) if version.file else f"v{version.version_number}"
    response = FileResponse(version.file.open("rb"), as_attachment=True, filename=filename)
    return response


# ==================== DELETE ====================

@require_portal_json()
@require_role("manager")
@audited(action="delete", model_name="Document")
@require_http_methods(["POST"])
def documento_delete(request, document_id):
    doc = get_object_or_404(
        Document,
        id=document_id,
        organization=request.organization,
        office=request.office,
    )
    title = doc.title
    if doc.file:
        doc.file.delete(save=False)
    doc.delete()
    log_activity(request, "document_delete", f"Documento deletado: {title}")
    return JsonResponse({"ok": True})


# ==================== VERSIONS ====================

@require_portal_json()
@require_role("assistant")
@require_http_methods(["POST"])
def documento_version_create(request, document_id):
    doc = get_object_or_404(
        Document,
        id=document_id,
        organization=request.organization,
        office=request.office,
    )
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return JsonResponse({"error": "Arquivo obrigatório"}, status=400)

    from django.db.models import Max
    max_version = doc.versions.aggregate(max_v=Max("version_number"))["max_v"] or 0
    next_version = max_version + 1

    version = DocumentVersion.objects.create(
        document=doc,
        version_number=next_version,
        file=uploaded_file,
        changes_description=request.POST.get("changes_description", "").strip(),
        created_by=request.user,
    )

    # Atualiza o documento principal com o novo arquivo
    doc.file = uploaded_file
    doc.save()  # save() recalcula file_size e file_extension

    log_activity(request, "document_version", f"Nova versão v{next_version} de '{doc.title}'")
    return JsonResponse({
        "ok": True,
        "version": {
            "id": version.id,
            "version_number": version.version_number,
            "created_at": version.created_at.strftime("%d/%m/%Y %H:%M"),
        },
    })


# ==================== SHARES ====================

@require_portal_json()
@require_role("lawyer")
@audited(action="share", model_name="Document")
@require_http_methods(["POST"])
def documento_share_create(request, document_id):
    doc = get_object_or_404(
        Document,
        id=document_id,
        organization=request.organization,
        office=request.office,
    )
    payload = parse_json_body(request)
    user_id = payload.get("user_id")
    if not user_id:
        return JsonResponse({"error": "user_id obrigatório"}, status=400)

    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "Usuário não encontrado"}, status=404)

    share, created = DocumentShare.objects.get_or_create(
        organization=request.organization,
        office=request.office,
        document=doc,
        shared_with=target_user,
        defaults={
            "shared_by": request.user,
            "can_edit": payload.get("can_edit", False),
            "can_download": payload.get("can_download", True),
        },
    )
    if not created:
        share.can_edit = payload.get("can_edit", share.can_edit)
        share.can_download = payload.get("can_download", share.can_download)
        share.save(update_fields=["can_edit", "can_download"])

    return JsonResponse({"ok": True, "created": created, "share_id": share.id})


@require_portal_json()
@require_role("lawyer")
@require_http_methods(["POST"])
def documento_share_delete(request, share_id):
    share = get_object_or_404(
        DocumentShare,
        id=share_id,
        document__organization=request.organization,
        document__office=request.office,
    )
    share.delete()
    return JsonResponse({"ok": True})


# ==================== COMMENTS ====================

@require_portal_json()
@require_role("intern")
@require_http_methods(["POST"])
def documento_comment_create(request, document_id):
    doc = get_object_or_404(
        Document,
        id=document_id,
        organization=request.organization,
        office=request.office,
    )
    payload = parse_json_body(request)
    comment_text = payload.get("comment", "").strip()
    if not comment_text:
        return JsonResponse({"error": "Comentário obrigatório"}, status=400)

    comment = DocumentComment.objects.create(
        organization=request.organization,
        office=request.office,
        document=doc,
        author=request.user,
        comment=comment_text,
    )
    return JsonResponse({
        "ok": True,
        "comment": {
            "id": comment.id,
            "comment": comment.comment,
            "author": comment.author.get_full_name() or comment.author.email,
            "created_at": comment.created_at.strftime("%d/%m/%Y %H:%M"),
        },
    })


# ==================== PASTAS ====================

@require_portal_access()
def pastas(request):
    folders = Folder.objects.filter(
        organization=request.organization,
        office=request.office,
        parent__isnull=True,
    ).prefetch_related("subfolders").order_by("name")

    return render(request, "portal/pastas.html", {
        "folders": folders,
        "active_page": "documentos",
    })


@require_portal_json()
@require_role("lawyer")
@require_http_methods(["POST"])
def pasta_create(request):
    payload = parse_json_body(request)
    name = payload.get("name", "").strip()
    if not name:
        return JsonResponse({"error": "Nome obrigatório"}, status=400)

    parent_id = payload.get("parent_id")
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
        description=payload.get("description", "").strip(),
        parent=parent,
        color=payload.get("color", "#007bff"),
        created_by=request.user,
    )
    return JsonResponse({
        "ok": True,
        "folder": {"id": folder.id, "name": folder.name, "full_path": folder.full_path},
    })


@require_portal_json()
@require_role("manager")
@require_http_methods(["POST"])
def pasta_delete(request, folder_id):
    folder = get_object_or_404(
        Folder,
        id=folder_id,
        organization=request.organization,
        office=request.office,
    )
    if folder.documents.exists() or folder.subfolders.exists():
        return JsonResponse({"error": "Pasta não está vazia"}, status=400)

    name = folder.name
    folder.delete()
    log_activity(request, "folder_delete", f"Pasta deletada: {name}")
    return JsonResponse({"ok": True})