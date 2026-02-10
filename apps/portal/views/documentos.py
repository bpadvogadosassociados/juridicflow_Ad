"""
Views de Documentos — upload, versionamento, compartilhamento, pastas.
"""
import mimetypes

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q, F
from django.http import FileResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.documents.models import Document, DocumentVersion, DocumentShare, DocumentComment, Folder
from apps.customers.models import Customer
from apps.processes.models import Process
from apps.portal.decorators import require_portal_access, require_portal_json
from apps.portal.forms import DocumentUploadForm
from apps.portal.views._helpers import parse_json_body, log_activity


def _collect_doc_tags(qs, limit=10):
    """Conta tags de documentos sem carregar objetos inteiros."""
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

    # Phase 1 fix: aggregate em vez de sum() em Python
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
    if tag_filter:
        qs = qs.filter(tags__icontains=tag_filter)
    if folder_id:
        qs = qs.filter(folder_id=folder_id)

    qs = qs.order_by("-created_at")

    paginator = Paginator(qs, settings.PORTAL_PAGINATION_SIZE)
    documents_page = paginator.get_page(request.GET.get("page", 1))

    all_tags = set()
    for tags_str in Document.objects.filter(
        office=request.office
    ).exclude(tags="").values_list("tags", flat=True):
        all_tags.update(t.strip() for t in tags_str.split(",") if t.strip())

    folders = Folder.objects.filter(office=request.office).order_by("name")

    return render(request, "portal/documentos.html", {
        "documents": documents_page,
        "search": search,
        "category": category,
        "tag_filter": tag_filter,
        "folder_id": folder_id,
        "all_tags": sorted(all_tags),
        "folders": folders,
        "active_page": "documentos",
    })


# ==================== UPLOAD ====================

@require_portal_access()
@require_http_methods(["GET", "POST"])
def documento_upload(request):
    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.organization = request.organization
            doc.office = request.office
            doc.uploaded_by = request.user

            # Metadados do arquivo
            uploaded_file = request.FILES.get("file")
            if uploaded_file:
                doc.original_filename = uploaded_file.name
                doc.file_size = uploaded_file.size
                doc.mime_type = (
                    uploaded_file.content_type
                    or mimetypes.guess_type(uploaded_file.name)[0]
                    or "application/octet-stream"
                )

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

            if folder_id:
                try:
                    doc.folder = Folder.objects.get(
                        id=folder_id, organization=request.organization, office=request.office
                    )
                except Folder.DoesNotExist:
                    pass

            try:
                doc.save()
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
        "active_page": "documentos",
    })


# ==================== DETAIL / DOWNLOAD ====================

@require_portal_access()
def documento_detail(request, document_id):
    doc = get_object_or_404(
        Document.objects.select_related("uploaded_by", "process", "customer", "folder"),
        id=document_id,
        organization=request.organization,
        office=request.office,
    )
    versions = doc.versions.select_related("uploaded_by").order_by("-version_number")
    shares = doc.shares.select_related("shared_with").order_by("-created_at")
    comments = doc.comments.select_related("author").order_by("-created_at")

    return render(request, "portal/documento_detail.html", {
        "document": doc,
        "versions": versions,
        "shares": shares,
        "comments": comments,
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

    response = FileResponse(doc.file.open("rb"), content_type=doc.mime_type or "application/octet-stream")
    filename = doc.original_filename or doc.title
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
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

    response = FileResponse(
        version.file.open("rb"),
        content_type=version.mime_type or "application/octet-stream",
    )
    filename = version.original_filename or f"v{version.version_number}_{version.document.title}"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# ==================== DELETE ====================

@require_portal_json()
@require_http_methods(["POST"])
def documento_delete(request, document_id):
    doc = get_object_or_404(
        Document,
        id=document_id,
        organization=request.organization,
        office=request.office,
    )
    title = doc.title
    doc.delete()
    log_activity(request, "document_delete", f"Documento deletado: {title}")
    return JsonResponse({"ok": True})


# ==================== VERSIONS ====================

@require_portal_json()
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

    # Usa F() para evitar race condition no version_number
    from django.db.models import Max
    max_version = doc.versions.aggregate(max_v=Max("version_number"))["max_v"] or 0
    next_version = max_version + 1

    version = DocumentVersion.objects.create(
        document=doc,
        organization=request.organization,
        office=request.office,
        file=uploaded_file,
        version_number=next_version,
        original_filename=uploaded_file.name,
        file_size=uploaded_file.size,
        mime_type=uploaded_file.content_type or "application/octet-stream",
        uploaded_by=request.user,
        change_summary=request.POST.get("change_summary", "").strip(),
    )

    # Atualiza o documento principal com o novo arquivo
    doc.file = uploaded_file
    doc.file_size = uploaded_file.size
    doc.save(update_fields=["file", "file_size", "updated_at"])

    log_activity(request, "document_version", f"Nova versão v{next_version} de '{doc.title}'")
    return JsonResponse({
        "ok": True,
        "version": {
            "id": version.id,
            "version_number": version.version_number,
            "filename": version.original_filename,
        },
    })


# ==================== SHARES ====================

@require_portal_json()
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
        document=doc,
        shared_with=target_user,
        defaults={
            "organization": request.organization,
            "office": request.office,
            "shared_by": request.user,
            "permission": payload.get("permission", "view"),
        },
    )
    return JsonResponse({"ok": True, "created": created, "share_id": share.id})


@require_portal_json()
@require_http_methods(["POST"])
def documento_share_delete(request, share_id):
    share = get_object_or_404(
        DocumentShare,
        id=share_id,
        organization=request.organization,
        office=request.office,
    )
    share.delete()
    return JsonResponse({"ok": True})


# ==================== COMMENTS ====================

@require_portal_json()
@require_http_methods(["POST"])
def documento_comment_create(request, document_id):
    doc = get_object_or_404(
        Document,
        id=document_id,
        organization=request.organization,
        office=request.office,
    )
    payload = parse_json_body(request)
    text = payload.get("text", "").strip()
    if not text:
        return JsonResponse({"error": "Texto obrigatório"}, status=400)

    comment = DocumentComment.objects.create(
        document=doc,
        organization=request.organization,
        office=request.office,
        author=request.user,
        text=text,
    )
    return JsonResponse({
        "ok": True,
        "comment": {
            "id": comment.id,
            "text": comment.text,
            "author": comment.author.get_full_name() or comment.author.email,
            "created_at": comment.created_at.isoformat(),
        },
    })


# ==================== PASTAS ====================

@require_portal_access()
def pastas(request):
    folders = Folder.objects.filter(
        organization=request.organization,
        office=request.office,
    ).annotate(doc_count=Count("documents")).order_by("name")

    return render(request, "portal/pastas.html", {
        "folders": folders,
        "active_page": "documentos",
    })


@require_portal_json()
@require_http_methods(["POST"])
def pasta_create(request):
    payload = parse_json_body(request)
    name = payload.get("name", "").strip()
    if not name:
        return JsonResponse({"error": "Nome obrigatório"}, status=400)

    folder = Folder.objects.create(
        organization=request.organization,
        office=request.office,
        name=name,
        description=payload.get("description", "").strip(),
        color=payload.get("color", ""),
    )
    return JsonResponse({
        "ok": True,
        "folder": {"id": folder.id, "name": folder.name},
    })


@require_portal_json()
@require_http_methods(["POST"])
def pasta_delete(request, folder_id):
    folder = get_object_or_404(
        Folder,
        id=folder_id,
        organization=request.organization,
        office=request.office,
    )
    name = folder.name
    # Desvincula documentos (não deleta)
    folder.documents.update(folder=None)
    folder.delete()
    log_activity(request, "folder_delete", f"Pasta deletada: {name}")
    return JsonResponse({"ok": True})