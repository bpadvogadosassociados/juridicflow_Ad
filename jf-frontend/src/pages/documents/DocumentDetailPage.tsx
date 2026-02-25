import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Download, Trash2, FileText, AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { PageHeader } from '@/components/layout/PageHeader'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { documentsApi } from '@/api/documents'
import { formatDate, formatRelative } from '@/lib/utils'

export function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [deleteOpen, setDeleteOpen] = useState(false)

  const { data: doc, isLoading, isError } = useQuery({
    queryKey: ['document', Number(id)],
    queryFn: () => documentsApi.get(Number(id)),
    enabled: !!id,
  })

  const deleteMutation = useMutation({
    mutationFn: () => documentsApi.delete(Number(id)),
    onSuccess: () => {
      toast.success('Documento excluído.')
      navigate('/app/documentos')
    },
    onError: () => toast.error('Erro ao excluir.'),
  })

  if (isLoading) return <div className="h-64 bg-slate-100 rounded-xl animate-pulse max-w-2xl mx-auto" />
  if (isError || !doc) return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 text-slate-400">
      <AlertTriangle size={32} />
      <p className="text-sm">Documento não encontrado.</p>
      <Button variant="outline" size="sm" onClick={() => navigate('/app/documentos')}>
        <ArrowLeft size={14} className="mr-2" /> Voltar
      </Button>
    </div>
  )

  const ext = doc.file_url ? doc.file_url.split('.').pop()?.toLowerCase() : null
  const isPDF = ext === 'pdf'

  return (
    <div className="max-w-3xl mx-auto page-enter">
      <PageHeader
        title={doc.title}
        breadcrumbs={[{ label: 'Documentos', href: '/app/documentos' }, { label: doc.title }]}
        actions={
          <div className="flex gap-2">
            {doc.file_url && (
              <Button variant="outline" size="sm" asChild className="gap-2">
                <a href={doc.file_url} target="_blank" rel="noreferrer" download>
                  <Download size={14} /> Download
                </a>
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={() => setDeleteOpen(true)} className="gap-2 text-red-600 border-red-200 hover:bg-red-50">
              <Trash2 size={14} /> Excluir
            </Button>
          </div>
        }
      />

      {/* PDF preview */}
      {isPDF && doc.file_url && (
        <div className="mb-5 rounded-xl overflow-hidden border border-slate-200 shadow-sm">
          <iframe src={doc.file_url} className="w-full h-[600px]" title={doc.title} />
        </div>
      )}

      {/* Non-PDF: icon + download prompt */}
      {!isPDF && (
        <Card className="border-slate-200 shadow-sm mb-5">
          <CardContent className="p-8 flex flex-col items-center gap-3">
            <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center">
              <FileText size={28} className="text-slate-400" />
            </div>
            <p className="text-sm font-medium text-slate-700">{doc.title}</p>
            {ext && <span className="text-xs uppercase font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-500">{ext}</span>}
            {doc.file_url && (
              <Button size="sm" className="bg-blue-600 hover:bg-blue-700 gap-2 mt-2" asChild>
                <a href={doc.file_url} target="_blank" rel="noreferrer" download>
                  <Download size={14} /> Baixar arquivo
                </a>
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Metadata */}
      <Card className="border-slate-200 shadow-none">
        <CardContent className="p-4 space-y-2">
          {doc.description && (
            <div className="pb-2 mb-2 border-b border-slate-100">
              <p className="text-xs text-slate-500 mb-1">Descrição</p>
              <p className="text-sm text-slate-700">{doc.description}</p>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-xs text-slate-400">Enviado</span>
            <span className="text-xs text-slate-600">{formatRelative(doc.created_at)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-xs text-slate-400">Atualizado</span>
            <span className="text-xs text-slate-600">{formatRelative(doc.updated_at)}</span>
          </div>
        </CardContent>
      </Card>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Excluir documento?"
        description={`"${doc.title}" será excluído permanentemente.`}
        confirmLabel="Excluir"
        variant="destructive"
        onConfirm={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
      />
    </div>
  )
}
