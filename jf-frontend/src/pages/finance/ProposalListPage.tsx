import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { PageHeader } from '@/components/layout/PageHeader'
import { DataTable } from '@/components/shared/DataTable'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import api from '@/api/client'
import { formatCurrency, formatDate, truncate } from '@/lib/utils'
import { usePagination } from '@/hooks/usePagination'

// Minimal proposal type
interface Proposal {
  id: number; title: string; amount: string; status: string
  customer: number; process: number | null; responsible: number | null
  responsible_name: string | null; issue_date: string; valid_until: string | null
  notes: string; created_at: string; updated_at: string
}

const STATUS_LABELS: Record<string, string> = {
  draft: 'Rascunho', sent: 'Enviada', accepted: 'Aceita', rejected: 'Recusada', expired: 'Expirada',
}

export function ProposalListPage() {
  const { page, setPage, reset } = usePagination()
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editTarget, setEditTarget] = useState<Proposal | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Proposal | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['proposals', { page, status: statusFilter }],
    queryFn: () => api.get('/finance/proposals/', { params: { page, status: statusFilter || undefined } }).then(r => r.data),
    staleTime: 30_000,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/finance/proposals/${id}/`),
    onSuccess: () => { toast.success('Proposta excluída.'); queryClient.invalidateQueries({ queryKey: ['proposals'] }); setDeleteTarget(null) },
    onError: () => toast.error('Erro ao excluir.'),
  })

  const columns = [
    {
      key: 'title',
      header: 'Proposta',
      render: (row: Proposal) => (
        <div>
          <p className="text-sm font-medium text-slate-900">{row.title}</p>
        </div>
      ),
    },
    {
      key: 'amount',
      header: 'Valor',
      render: (row: Proposal) => <span className="text-sm font-semibold text-slate-800">{formatCurrency(row.amount)}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (row: Proposal) => (
        <span className={`text-xs px-2 py-0.5 rounded-md font-medium ${
          row.status === 'accepted' ? 'bg-emerald-50 text-emerald-700' :
          row.status === 'rejected' ? 'bg-red-50 text-red-600' :
          row.status === 'sent' ? 'bg-blue-50 text-blue-700' :
          'bg-slate-100 text-slate-600'
        }`}>{STATUS_LABELS[row.status] ?? row.status}</span>
      ),
    },
    {
      key: 'dates',
      header: 'Validade',
      render: (row: Proposal) => (
        <span className="text-xs text-slate-400">{formatDate(row.issue_date)}{row.valid_until ? ` → ${formatDate(row.valid_until)}` : ''}</span>
      ),
    },
    {
      key: 'responsible',
      header: 'Responsável',
      render: (row: Proposal) => <span className="text-xs text-slate-500">{row.responsible_name ?? '—'}</span>,
    },
    {
      key: 'actions',
      header: '',
      render: (row: Proposal) => (
        <div className="flex gap-1" onClick={e => e.stopPropagation()}>
          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-slate-500"
            onClick={() => { setEditTarget(row); setShowForm(true) }}>Editar</Button>
          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-red-400"
            onClick={() => setDeleteTarget(row)}>Excluir</Button>
        </div>
      ),
    },
  ]

  return (
    <div className="max-w-7xl mx-auto page-enter">
      <PageHeader
        title="Propostas"
        subtitle={data ? `${data.count} proposta${data.count !== 1 ? 's' : ''}` : undefined}
        breadcrumbs={[{ label: 'Financeiro', href: '/app/financeiro' }, { label: 'Propostas' }]}
        actions={
          <Button onClick={() => { setEditTarget(null); setShowForm(true) }} className="bg-blue-600 hover:bg-blue-700 gap-2 h-9">
            <Plus size={15} /> Nova Proposta
          </Button>
        }
      />

      <div className="flex gap-2 mb-5">
        {Object.entries(STATUS_LABELS).map(([k, v]) => (
          <Button key={k}
            variant={statusFilter === k ? 'default' : 'outline'}
            size="sm"
            className={`h-9 text-xs ${statusFilter === k ? 'bg-blue-600 hover:bg-blue-700' : ''}`}
            onClick={() => { setStatusFilter(statusFilter === k ? '' : k); reset() }}>
            {v}
          </Button>
        ))}
        {statusFilter && <Button variant="ghost" size="sm" className="h-9 text-xs text-slate-500" onClick={() => { setStatusFilter(''); reset() }}>Todas</Button>}
      </div>

      <DataTable
        columns={columns} data={data?.results ?? []} keyFn={r => r.id}
        isLoading={isLoading} total={data?.count} page={page} pageSize={25} onPageChange={setPage}
        emptyTitle="Nenhuma proposta encontrada" emptyDescription="Crie a primeira proposta comercial."
        emptyAction={<Button size="sm" className="bg-blue-600 hover:bg-blue-700 gap-2" onClick={() => setShowForm(true)}><Plus size={14} /> Nova Proposta</Button>}
      />

      <ProposalFormModal open={showForm} onOpenChange={v => { setShowForm(v); if (!v) setEditTarget(null) }}
        proposal={editTarget}
        onSaved={() => { queryClient.invalidateQueries({ queryKey: ['proposals'] }); setShowForm(false); setEditTarget(null) }} />

      <ConfirmDialog open={!!deleteTarget} onOpenChange={v => { if (!v) setDeleteTarget(null) }}
        title="Excluir proposta?" description={`"${deleteTarget?.title}" será excluída permanentemente.`}
        confirmLabel="Excluir" variant="destructive"
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)} loading={deleteMutation.isPending} />
    </div>
  )
}

function ProposalFormModal({ open, onOpenChange, proposal, onSaved }: {
  open: boolean; onOpenChange: (v: boolean) => void; proposal: Proposal | null; onSaved: () => void
}) {
  const [form, setForm] = useState({ title: '', amount: '', status: 'draft', issue_date: new Date().toISOString().split('T')[0], valid_until: '', notes: '', customer: 0 })
  const set = (k: string, v: any) => setForm(f => ({ ...f, [k]: v }))

  useEffect(() => {
    if (open && proposal) {
      setForm({ title: proposal.title, amount: proposal.amount, status: proposal.status, issue_date: proposal.issue_date, valid_until: proposal.valid_until ?? '', notes: proposal.notes ?? '', customer: proposal.customer })
    } else if (open) {
      setForm({ title: '', amount: '', status: 'draft', issue_date: new Date().toISOString().split('T')[0], valid_until: '', notes: '', customer: 0 })
    }
  }, [proposal, open])

  const queryClient = useQueryClient()
  const createMutation = useMutation({
    mutationFn: () => api.post('/finance/proposals/', form),
    onSuccess: () => { toast.success('Proposta criada.'); onSaved() },
    onError: () => toast.error('Erro ao criar proposta.'),
  })
  const updateMutation = useMutation({
    mutationFn: () => api.patch(`/finance/proposals/${proposal!.id}/`, form),
    onSuccess: () => { toast.success('Proposta atualizada.'); onSaved() },
    onError: () => toast.error('Erro ao atualizar.'),
  })
  const isPending = createMutation.isPending || updateMutation.isPending
  const isEdit = !!proposal

  const { data: customers } = useQuery({
    queryKey: ['customers-select'],
    queryFn: () => api.get('/customers/', { params: { page: 1 } }).then(r => r.data),
    staleTime: 60_000,
    enabled: open,
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader><DialogTitle className="text-base">{isEdit ? 'Editar Proposta' : 'Nova Proposta'}</DialogTitle></DialogHeader>
        <div className="space-y-4 py-1">
          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-slate-600">Cliente</Label>
            <Select value={String(form.customer || '')} onValueChange={v => set('customer', Number(v))}>
              <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue placeholder="Selecionar" /></SelectTrigger>
              <SelectContent>
                {customers?.results?.map((c: any) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-slate-600">Título *</Label>
            <Input value={form.title} onChange={e => set('title', e.target.value)} className="text-sm" autoFocus />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-slate-600">Valor (R$) *</Label>
              <Input type="number" step="0.01" value={form.amount} onChange={e => set('amount', e.target.value)} className="text-sm" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-slate-600">Status</Label>
              <Select value={form.status} onValueChange={v => set('status', v)}>
                <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(STATUS_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-slate-600">Emissão</Label>
              <Input type="date" value={form.issue_date} onChange={e => set('issue_date', e.target.value)} className="text-sm" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-slate-600">Validade até</Label>
              <Input type="date" value={form.valid_until} onChange={e => set('valid_until', e.target.value)} className="text-sm" />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-slate-600">Observações</Label>
            <Textarea value={form.notes} onChange={e => set('notes', e.target.value)} rows={2} className="resize-none text-sm" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={isPending}>Cancelar</Button>
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700"
            disabled={!form.title || !form.amount || isPending}
            onClick={() => isEdit ? updateMutation.mutate() : createMutation.mutate()}>
            {isPending ? 'Salvando…' : isEdit ? 'Atualizar' : 'Criar Proposta'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
