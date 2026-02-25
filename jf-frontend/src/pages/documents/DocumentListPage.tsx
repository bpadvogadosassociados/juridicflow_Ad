import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, Search, FileText, Download, Trash2, Eye, SlidersHorizontal } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { PageHeader } from '@/components/layout/PageHeader'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { documentsApi, type Document } from '@/api/documents'
import { formatDate, formatRelative, truncate } from '@/lib/utils'
import { useDebounce } from '@/hooks/useDebounce'
import { usePagination } from '@/hooks/usePagination'
import { cn } from '@/lib/utils'

const CATEGORY_LABELS: Record<string, string> = {
  contract: 'Contrato', petition: 'Petição', decision: 'Decisão/Sentença',
  power_of_attorney: 'Procuração', certificate: 'Certidão', minutes: 'Ata',
  opinion: 'Parecer', appeal: 'Recurso', evidence: 'Prova',
  correspondence: 'Correspondência', internal: 'Interno', other: 'Outro',
}

const CATEGORY_ICONS: Record<string, string> = {
  contract: '📋', petition: '⚖️', decision: '🔨', power_of_attorney: '✍️',
  certificate: '📜', minutes: '📝', opinion: '💡', appeal: '📣',
  evidence: '🔍', correspondence: '✉️', internal: '🏢', other: '📄',
}

const EXT_COLORS: Record<string, string> = {
  pdf: 'bg-red-100 text-red-600',
  doc: 'bg-blue-100 text-blue-600', docx: 'bg-blue-100 text-blue-600',
  xls: 'bg-emerald-100 text-emerald-600', xlsx: 'bg-emerald-100 text-emerald-600',
  jpg: 'bg-amber-100 text-amber-600', jpeg: 'bg-amber-100 text-amber-600',
  png: 'bg-violet-100 text-violet-600',
}

function getExt(url: string | null): string {
  if (!url) return 'arq'
  return url.split('.').pop()?.toLowerCase() ?? 'arq'
}

function formatBytes(bytes: number): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(0)}KB`
  return `${(bytes / 1048576).toFixed(1)}MB`
}

export function DocumentListPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { page, setPage, reset } = usePagination()
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Document | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null)
  const debouncedSearch = useDebounce(search, 300)

  const { data, isLoading } = useQuery({
    queryKey: ['documents', { page, search: debouncedSearch, category: categoryFilter }],
    queryFn: () => documentsApi.list({
      page,
      search: debouncedSearch || undefined,
      category: categoryFilter || undefined,
    }),
    staleTime: 30_000,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => documentsApi.delete(id),
    onSuccess: () => {
      toast.success('Documento excluído.')
      queryClient.invalidateQueries({ queryKey: ['documents'] })
      setDeleteTarget(null)
    },
    onError: () => toast.error('Erro ao excluir.'),
  })

  const docs = data?.results ?? []
  const hasFilters = !!(categoryFilter)

  return (
    <div className="max-w-7xl mx-auto page-enter">
      <PageHeader
        title="Documentos"
        subtitle={data ? `${data.count} documento${data.count !== 1 ? 's' : ''}` : undefined}
        breadcrumbs={[{ label: 'JuridicFlow' }, { label: 'Documentos' }]}
        actions={
          <Button onClick={() => setUploadOpen(true)} className="bg-blue-600 hover:bg-blue-700 gap-2 h-9">
            <Upload size={15} /> Enviar Documento
          </Button>
        }
      />

      {/* Search + filter bar */}
      <div className="flex gap-3 mb-5">
        <div className="relative flex-1 max-w-md">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <Input
            placeholder="Buscar por título…"
            value={search}
            onChange={e => { setSearch(e.target.value); reset() }}
            className="pl-9 h-9 bg-white border-slate-200 text-sm"
          />
        </div>
        <Button
          variant="outline" size="sm"
          onClick={() => setShowFilters(!showFilters)}
          className={cn('gap-2 h-9', hasFilters ? 'border-blue-300 text-blue-600 bg-blue-50' : '')}
        >
          <SlidersHorizontal size={14} /> Categoria
          {hasFilters && <span className="w-4 h-4 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center">1</span>}
        </Button>
      </div>

      {showFilters && (
        <div className="flex flex-wrap gap-3 mb-5 p-4 bg-slate-50 rounded-xl border border-slate-200">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-500">Categoria</label>
            <Select value={categoryFilter || 'all'} onValueChange={v => { setCategoryFilter(v === 'all' ? '' : v); reset() }}>
              <SelectTrigger className="h-9 w-48 bg-white text-sm border-slate-200"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                {Object.entries(CATEGORY_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          {hasFilters && <div className="flex items-end"><Button variant="ghost" size="sm" className="h-9 text-xs text-slate-500" onClick={() => { setCategoryFilter(''); reset() }}>Limpar</Button></div>}
        </div>
      )}

      {/* Document grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-40 bg-slate-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : docs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400">
          <FileText size={40} className="mb-3 opacity-30" />
          <p className="text-sm font-medium">Nenhum documento encontrado</p>
          <p className="text-xs mt-1 mb-4">Envie o primeiro documento do escritório.</p>
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700 gap-2" onClick={() => setUploadOpen(true)}>
            <Upload size={14} /> Enviar Documento
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {docs.map(doc => {
            const ext = getExt(doc.file_url)
            const extColor = EXT_COLORS[ext] ?? 'bg-slate-100 text-slate-500'
            return (
              <div
                key={doc.id}
                className="bg-white border border-slate-200 rounded-xl p-4 hover:shadow-md hover:border-slate-300 transition-all group cursor-pointer"
                onClick={() => navigate(`/app/documentos/${doc.id}`)}
              >
                {/* File type badge + actions */}
                <div className="flex items-start justify-between mb-3">
                  <span className={cn('text-[10px] font-bold px-2 py-1 rounded-md uppercase tracking-wide', extColor)}>
                    {ext}
                  </span>
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity" onClick={e => e.stopPropagation()}>
                    {doc.file_url && (
                      <a href={doc.file_url} target="_blank" rel="noreferrer"
                        className="p-1.5 text-slate-400 hover:text-blue-500 transition-colors rounded"
                        title="Download">
                        <Download size={13} />
                      </a>
                    )}
                    <button
                      onClick={() => setEditTarget(doc)}
                      className="p-1.5 text-slate-400 hover:text-slate-600 transition-colors rounded"
                      title="Editar"
                    >
                      <Eye size={13} />
                    </button>
                    <button
                      onClick={() => setDeleteTarget(doc)}
                      className="p-1.5 text-slate-400 hover:text-red-500 transition-colors rounded"
                      title="Excluir"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>

                {/* Title */}
                <p className="text-sm font-semibold text-slate-900 leading-tight mb-1 line-clamp-2">
                  {doc.title}
                </p>
                {doc.description && (
                  <p className="text-[11px] text-slate-400 line-clamp-2 mb-2">{doc.description}</p>
                )}

                {/* Footer */}
                <div className="flex items-center justify-between mt-auto pt-2 border-t border-slate-50">
                  <span className="text-[10px] text-slate-400">{formatRelative(doc.created_at)}</span>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Pagination */}
      {data && data.count > 25 && (
        <div className="flex items-center justify-between mt-5">
          <p className="text-xs text-slate-400">{data.count} documentos</p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={!data.previous} onClick={() => setPage(p => p - 1)}>Anterior</Button>
            <Button variant="outline" size="sm" disabled={!data.next} onClick={() => setPage(p => p + 1)}>Próximo</Button>
          </div>
        </div>
      )}

      {/* Upload modal */}
      <UploadModal
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ['documents'] })
          setUploadOpen(false)
        }}
      />

      {/* Edit modal */}
      {editTarget && (
        <EditModal
          doc={editTarget}
          onClose={() => setEditTarget(null)}
          onSaved={() => {
            queryClient.invalidateQueries({ queryKey: ['documents'] })
            setEditTarget(null)
          }}
        />
      )}

      {/* Delete confirm */}
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={v => { if (!v) setDeleteTarget(null) }}
        title="Excluir documento?"
        description={`"${deleteTarget?.title}" será excluído permanentemente.`}
        confirmLabel="Excluir"
        variant="destructive"
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        loading={deleteMutation.isPending}
      />
    </div>
  )
}

// ── Upload Modal ─────────────────────────────────────────────────────────────

function UploadModal({ open, onOpenChange, onSaved }: { open: boolean; onOpenChange: (v: boolean) => void; onSaved: () => void }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const mutation = useMutation({
    mutationFn: () => {
      const fd = new FormData()
      fd.append('title', title || file?.name || 'Documento')
      fd.append('description', description)
      if (file) fd.append('file', file)
      return documentsApi.upload(fd)
    },
    onSuccess: () => { toast.success('Documento enviado!'); onSaved(); setTitle(''); setDescription(''); setFile(null) },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Erro ao enviar documento.'),
  })

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) { setFile(f); if (!title) setTitle(f.name.replace(/\.[^.]+$/, '')) }
  }

  return (
    <Dialog open={open} onOpenChange={v => { onOpenChange(v); if (!v) { setFile(null); setTitle(''); setDescription('') } }}>
      <DialogContent className="max-w-md">
        <DialogHeader><DialogTitle className="text-base">Enviar Documento</DialogTitle></DialogHeader>
        <div className="space-y-4 py-1">
          {/* Drop zone */}
          <div
            className={cn(
              'border-2 border-dashed rounded-xl p-6 text-center transition-colors cursor-pointer',
              dragOver ? 'border-blue-400 bg-blue-50' : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50',
            )}
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
          >
            <input ref={inputRef} type="file" className="hidden" onChange={e => {
              const f = e.target.files?.[0]
              if (f) { setFile(f); if (!title) setTitle(f.name.replace(/\.[^.]+$/, '')) }
            }} />
            {file ? (
              <div>
                <p className="text-sm font-medium text-blue-700">{file.name}</p>
                <p className="text-xs text-slate-400 mt-1">{formatBytes(file.size)}</p>
              </div>
            ) : (
              <div>
                <Upload size={24} className="mx-auto text-slate-300 mb-2" />
                <p className="text-sm text-slate-500">Arraste ou clique para selecionar</p>
                <p className="text-xs text-slate-400 mt-1">PDF, Word, Excel, imagens…</p>
              </div>
            )}
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-slate-600">Título</Label>
            <Input value={title} onChange={e => setTitle(e.target.value)} placeholder="Nome do documento" className="text-sm" />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-slate-600">Descrição</Label>
            <Textarea value={description} onChange={e => setDescription(e.target.value)} rows={2} className="resize-none text-sm" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>Cancelar</Button>
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700" disabled={!file || mutation.isPending}
            onClick={() => mutation.mutate()}>
            {mutation.isPending ? 'Enviando…' : 'Enviar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Edit Modal ───────────────────────────────────────────────────────────────

function EditModal({ doc, onClose, onSaved }: { doc: Document; onClose: () => void; onSaved: () => void }) {
  const [title, setTitle] = useState(doc.title)
  const [description, setDescription] = useState(doc.description ?? '')
  const mutation = useMutation({
    mutationFn: () => documentsApi.update(doc.id, { title, description }),
    onSuccess: () => { toast.success('Documento atualizado.'); onSaved() },
    onError: () => toast.error('Erro ao atualizar.'),
  })
  return (
    <Dialog open onOpenChange={v => { if (!v) onClose() }}>
      <DialogContent className="max-w-sm">
        <DialogHeader><DialogTitle className="text-base">Editar Documento</DialogTitle></DialogHeader>
        <div className="space-y-4 py-1">
          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-slate-600">Título</Label>
            <Input value={title} onChange={e => setTitle(e.target.value)} className="text-sm" />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-slate-600">Descrição</Label>
            <Textarea value={description} onChange={e => setDescription(e.target.value)} rows={3} className="resize-none text-sm" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>Cancelar</Button>
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700" disabled={!title || mutation.isPending}
            onClick={() => mutation.mutate()}>
            {mutation.isPending ? 'Salvando…' : 'Salvar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
