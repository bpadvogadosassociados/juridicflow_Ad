import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { PageHeader } from '@/components/layout/PageHeader'
import { DataTable } from '@/components/shared/DataTable'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { financeApi } from '@/api/finance'
import { customersApi } from '@/api/customers'
import { formatCurrency, formatDate, truncate } from '@/lib/utils'
import { BILLING_TYPE_LABELS, AGREEMENT_STATUS_LABELS } from '@/lib/constants'
import { usePagination } from '@/hooks/usePagination'
import { useDebounce } from '@/hooks/useDebounce'
import type { FeeAgreement, CreateAgreementData } from '@/types/finance'

export function AgreementListPage() {
  const { page, setPage, reset } = usePagination()
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editTarget, setEditTarget] = useState<FeeAgreement | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<FeeAgreement | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['agreements', { page, status: statusFilter }],
    queryFn: () => financeApi.listAgreements({ page, status: statusFilter || undefined }),
    staleTime: 30_000,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => financeApi.deleteAgreement(id),
    onSuccess: () => {
      toast.success('Contrato excluído.')
      queryClient.invalidateQueries({ queryKey: ['agreements'] })
      setDeleteTarget(null)
    },
    onError: () => toast.error('Erro ao excluir.'),
  })

  const columns = [
    {
      key: 'title',
      header: 'Contrato',
      render: (row: FeeAgreement) => (
        <div>
          <p className="text-sm font-medium text-slate-900">{row.title}</p>
          {row.description && (
            <p className="text-[11px] text-slate-400 mt-0.5">{truncate(row.description, 60)}</p>
          )}
        </div>
      ),
    },
    {
      key: 'billing_type',
      header: 'Tipo',
      render: (row: FeeAgreement) => (
        <span className="text-xs text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md">
          {BILLING_TYPE_LABELS[row.billing_type] ?? row.billing_type}
        </span>
      ),
    },
    {
      key: 'amount',
      header: 'Valor',
      render: (row: FeeAgreement) => (
        <span className="text-sm font-semibold text-slate-800">{formatCurrency(row.amount)}</span>
      ),
    },
    {
      key: 'balance',
      header: 'Saldo',
      render: (row: FeeAgreement) => {
        const bal = parseFloat(row.balance)
        return (
          <span className={bal > 0 ? 'text-sm font-semibold text-amber-600' : 'text-sm text-emerald-600 font-semibold'}>
            {formatCurrency(row.balance)}
          </span>
        )
      },
    },
    {
      key: 'status',
      header: 'Status',
      render: (row: FeeAgreement) => <StatusBadge value={row.status} variant="agreement-status" />,
    },
    {
      key: 'dates',
      header: 'Vigência',
      render: (row: FeeAgreement) => (
        <span className="text-xs text-slate-400">
          {formatDate(row.start_date)}{row.end_date ? ` → ${formatDate(row.end_date)}` : ''}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      render: (row: FeeAgreement) => (
        <div className="flex gap-1" onClick={e => e.stopPropagation()}>
          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-slate-500"
            onClick={() => { setEditTarget(row); setShowForm(true) }}>Editar</Button>
          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-red-400 hover:text-red-600"
            onClick={() => setDeleteTarget(row)}>Excluir</Button>
        </div>
      ),
    },
  ]

  return (
    <div className="max-w-7xl mx-auto page-enter">
      <PageHeader
        title="Contratos de Honorários"
        subtitle={data ? `${data.count} contrato${data.count !== 1 ? 's' : ''}` : undefined}
        breadcrumbs={[{ label: 'Financeiro', href: '/app/financeiro' }, { label: 'Contratos' }]}
        actions={
          <Button onClick={() => { setEditTarget(null); setShowForm(true) }} className="bg-blue-600 hover:bg-blue-700 gap-2 h-9">
            <Plus size={15} /> Novo Contrato
          </Button>
        }
      />

      <div className="flex gap-3 mb-5">
        {Object.entries(AGREEMENT_STATUS_LABELS).map(([k, v]) => (
          <Button
            key={k}
            variant={statusFilter === k ? 'default' : 'outline'}
            size="sm"
            className={`h-9 text-xs ${statusFilter === k ? 'bg-blue-600 hover:bg-blue-700' : ''}`}
            onClick={() => { setStatusFilter(statusFilter === k ? '' : k); reset() }}
          >
            {v}
          </Button>
        ))}
        {statusFilter && (
          <Button variant="ghost" size="sm" className="h-9 text-xs text-slate-500"
            onClick={() => { setStatusFilter(''); reset() }}>Todos</Button>
        )}
      </div>

      <DataTable
        columns={columns}
        data={data?.results ?? []}
        keyFn={r => r.id}
        isLoading={isLoading}
        total={data?.count}
        page={page}
        pageSize={25}
        onPageChange={setPage}
        emptyTitle="Nenhum contrato encontrado"
        emptyDescription="Cadastre o primeiro contrato de honorários."
        emptyAction={
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700 gap-2"
            onClick={() => setShowForm(true)}>
            <Plus size={14} /> Novo Contrato
          </Button>
        }
      />

      <AgreementFormModal
        open={showForm}
        onOpenChange={v => { setShowForm(v); if (!v) setEditTarget(null) }}
        agreement={editTarget}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ['agreements'] })
          setShowForm(false)
          setEditTarget(null)
        }}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={v => { if (!v) setDeleteTarget(null) }}
        title="Excluir contrato?"
        description={`"${deleteTarget?.title}" será excluído permanentemente.`}
        confirmLabel="Excluir"
        variant="destructive"
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        loading={deleteMutation.isPending}
      />
    </div>
  )
}

// ── Form Modal ──────────────────────────────────────────────────────────────

function emptyForm(): CreateAgreementData {
  return {
    customer: 0,
    title: '',
    amount: '',
    billing_type: 'one_time',
    status: 'draft',
    installments: 1,
  }
}

function AgreementFormModal({ open, onOpenChange, agreement, onSaved }: {
  open: boolean
  onOpenChange: (v: boolean) => void
  agreement: FeeAgreement | null
  onSaved: () => void
}) {
  const [form, setForm] = useState<CreateAgreementData>(emptyForm())
  const set = (k: keyof CreateAgreementData, v: any) => setForm(f => ({ ...f, [k]: v }))

  const { data: customers } = useQuery({
    queryKey: ['customers-select'],
    queryFn: () => customersApi.list({ page: 1 }),
    staleTime: 60_000,
    enabled: open,
  })

  useState(() => {
    if (open) {
      if (agreement) {
        setForm({
          customer: agreement.customer,
          process: agreement.process ?? undefined,
          title: agreement.title,
          description: agreement.description ?? '',
          amount: agreement.amount,
          billing_type: agreement.billing_type,
          installments: agreement.installments,
          status: agreement.status,
          start_date: agreement.start_date ?? '',
          end_date: agreement.end_date ?? '',
          notes: agreement.notes ?? '',
        })
      } else {
        setForm(emptyForm())
      }
    }
  })

  const createMutation = useMutation({
    mutationFn: () => financeApi.createAgreement(form),
    onSuccess: () => { toast.success('Contrato criado.'); onSaved() },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Erro ao criar contrato.'),
  })

  const updateMutation = useMutation({
    mutationFn: () => financeApi.updateAgreement(agreement!.id, form),
    onSuccess: () => { toast.success('Contrato atualizado.'); onSaved() },
    onError: () => toast.error('Erro ao atualizar.'),
  })

  const isPending = createMutation.isPending || updateMutation.isPending
  const isEdit = !!agreement

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-base">{isEdit ? 'Editar Contrato' : 'Novo Contrato'}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-1">
          <FormField label="Cliente *">
            <Select value={String(form.customer || '')} onValueChange={v => set('customer', Number(v))}>
              <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue placeholder="Selecionar cliente" /></SelectTrigger>
              <SelectContent>
                {customers?.results.map(c => (
                  <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>

          <FormField label="Título *">
            <Input value={form.title} onChange={e => set('title', e.target.value)} placeholder="Ex: Contrato de Representação — João Silva" className="text-sm" />
          </FormField>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Tipo de Cobrança">
              <Select value={form.billing_type ?? 'one_time'} onValueChange={v => set('billing_type', v)}>
                <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(BILLING_TYPE_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
            <FormField label="Status">
              <Select value={form.status ?? 'draft'} onValueChange={v => set('status', v)}>
                <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(AGREEMENT_STATUS_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Valor Total (R$) *">
              <Input type="number" step="0.01" value={form.amount} onChange={e => set('amount', e.target.value)} placeholder="0,00" className="text-sm" />
            </FormField>
            <FormField label="Parcelas">
              <Input type="number" min="1" value={form.installments ?? 1} onChange={e => set('installments', Number(e.target.value))} className="text-sm" />
            </FormField>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Data de Início">
              <Input type="date" value={form.start_date ?? ''} onChange={e => set('start_date', e.target.value)} className="text-sm" />
            </FormField>
            <FormField label="Data de Término">
              <Input type="date" value={form.end_date ?? ''} onChange={e => set('end_date', e.target.value)} className="text-sm" />
            </FormField>
          </div>

          <FormField label="Observações">
            <Textarea value={form.notes ?? ''} onChange={e => set('notes', e.target.value)} rows={2} className="resize-none text-sm" />
          </FormField>
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={isPending}>Cancelar</Button>
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700"
            disabled={!form.title || !form.amount || !form.customer || isPending}
            onClick={() => isEdit ? updateMutation.mutate() : createMutation.mutate()}>
            {isPending ? 'Salvando…' : isEdit ? 'Atualizar' : 'Criar Contrato'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs font-medium text-slate-600">{label}</Label>
      {children}
    </div>
  )
}
