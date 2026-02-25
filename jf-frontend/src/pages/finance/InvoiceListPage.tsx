import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, AlertTriangle, CheckCircle2, Clock, CreditCard } from 'lucide-react'
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
import { formatCurrency, formatDate } from '@/lib/utils'
import { INVOICE_STATUS_LABELS, PAYMENT_METHOD_LABELS } from '@/lib/constants'
import { usePagination } from '@/hooks/usePagination'
import { cn } from '@/lib/utils'
import type { Invoice, CreateInvoiceData } from '@/types/finance'

const STATUS_TABS = [
  { label: 'Todas', value: '' },
  { label: 'Emitidas', value: 'issued' },
  { label: 'Enviadas', value: 'sent' },
  { label: 'Vencidas', value: 'overdue', alert: true },
  { label: 'Pagas', value: 'paid' },
]

export function InvoiceListPage() {
  const { page, setPage, reset } = usePagination()
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editTarget, setEditTarget] = useState<Invoice | null>(null)
  const [payTarget, setPayTarget] = useState<Invoice | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Invoice | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['invoices', { page, status: statusFilter }],
    queryFn: () => financeApi.listInvoices({ page, status: statusFilter || undefined }),
    staleTime: 30_000,
  })

  const { data: overdueData } = useQuery({
    queryKey: ['invoices-overdue-count'],
    queryFn: () => financeApi.listInvoices({ status: 'overdue' }),
    staleTime: 60_000,
  })
  const overdueCount = overdueData?.count ?? 0

  const deleteMutation = useMutation({
    mutationFn: (id: number) => financeApi.deleteInvoice(id),
    onSuccess: () => {
      toast.success('Fatura excluída.')
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
      setDeleteTarget(null)
    },
    onError: () => toast.error('Erro ao excluir.'),
  })

  const columns = [
    {
      key: 'urgency',
      header: '',
      width: 'w-1 px-0 pl-3',
      render: (row: Invoice) => (
        <div className={cn(
          'w-1 h-8 rounded-full',
          row.status === 'overdue' ? 'bg-red-500' :
          row.status === 'paid' ? 'bg-emerald-400' :
          row.status === 'sent' ? 'bg-blue-400' : 'bg-slate-200',
        )} />
      ),
    },
    {
      key: 'number',
      header: 'Fatura',
      render: (row: Invoice) => (
        <div>
          <p className="text-sm font-medium text-slate-900">{row.number || `#${row.id}`}</p>
          {row.description && <p className="text-[11px] text-slate-400">{row.description.slice(0, 48)}</p>}
        </div>
      ),
    },
    {
      key: 'amount',
      header: 'Valor',
      render: (row: Invoice) => (
        <div>
          <p className="text-sm font-semibold text-slate-800">{formatCurrency(row.net_amount)}</p>
          {parseFloat(row.discount ?? '0') > 0 && (
            <p className="text-[10px] text-slate-400 line-through">{formatCurrency(row.amount)}</p>
          )}
        </div>
      ),
    },
    {
      key: 'balance',
      header: 'Saldo',
      render: (row: Invoice) => {
        const bal = parseFloat(row.balance ?? '0')
        return (
          <span className={cn('text-sm font-semibold', bal > 0 ? 'text-amber-600' : 'text-emerald-600')}>
            {formatCurrency(row.balance)}
          </span>
        )
      },
    },
    {
      key: 'due_date',
      header: 'Vencimento',
      render: (row: Invoice) => (
        <span className={cn(
          'text-xs',
          row.status === 'overdue' ? 'text-red-600 font-semibold' : 'text-slate-600',
        )}>
          {formatDate(row.due_date)}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row: Invoice) => <StatusBadge value={row.status} variant="invoice-status" />,
    },
    {
      key: 'actions',
      header: '',
      render: (row: Invoice) => (
        <div className="flex gap-1" onClick={e => e.stopPropagation()}>
          {row.status !== 'paid' && row.status !== 'cancelled' && (
            <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
              onClick={() => setPayTarget(row)}>
              <CreditCard size={11} className="mr-1" /> Pagar
            </Button>
          )}
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
        title="Faturas"
        subtitle={data ? `${data.count} fatura${data.count !== 1 ? 's' : ''}` : undefined}
        breadcrumbs={[{ label: 'Financeiro', href: '/app/financeiro' }, { label: 'Faturas' }]}
        actions={
          <Button onClick={() => { setEditTarget(null); setShowForm(true) }} className="bg-blue-600 hover:bg-blue-700 gap-2 h-9">
            <Plus size={15} /> Nova Fatura
          </Button>
        }
      />

      {overdueCount > 0 && statusFilter !== 'overdue' && (
        <div className="flex items-center gap-3 p-3.5 mb-5 bg-red-50 border border-red-200 rounded-xl">
          <AlertTriangle size={16} className="text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-700">
            <span className="font-semibold">{overdueCount} fatura{overdueCount !== 1 ? 's' : ''} vencida{overdueCount !== 1 ? 's' : ''}</span>.{' '}
            <button onClick={() => { setStatusFilter('overdue'); reset() }} className="underline">Ver agora</button>
          </p>
        </div>
      )}

      <div className="flex flex-wrap gap-2 mb-5">
        {STATUS_TABS.map(tab => (
          <Button
            key={tab.value}
            variant={statusFilter === tab.value ? 'default' : 'outline'}
            size="sm"
            className={cn(
              'h-9 text-xs gap-1.5',
              statusFilter === tab.value ? 'bg-blue-600 hover:bg-blue-700' : '',
              tab.alert && statusFilter !== 'overdue' && overdueCount > 0 ? 'border-red-200 text-red-600 hover:bg-red-50' : '',
            )}
            onClick={() => { setStatusFilter(tab.value); reset() }}
          >
            {tab.label}
            {tab.alert && overdueCount > 0 && (
              <span className="w-4 h-4 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center">
                {overdueCount > 9 ? '9+' : overdueCount}
              </span>
            )}
          </Button>
        ))}
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
        emptyTitle="Nenhuma fatura encontrada"
        emptyDescription="Crie uma nova fatura vinculada a um contrato."
        emptyAction={
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700 gap-2"
            onClick={() => setShowForm(true)}>
            <Plus size={14} /> Nova Fatura
          </Button>
        }
      />

      <InvoiceFormModal
        open={showForm}
        onOpenChange={v => { setShowForm(v); if (!v) setEditTarget(null) }}
        invoice={editTarget}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ['invoices'] })
          setShowForm(false)
          setEditTarget(null)
        }}
      />

      <PaymentModal
        open={!!payTarget}
        onOpenChange={v => { if (!v) setPayTarget(null) }}
        invoice={payTarget}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ['invoices'] })
          queryClient.invalidateQueries({ queryKey: ['invoices-overdue-count'] })
          setPayTarget(null)
        }}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={v => { if (!v) setDeleteTarget(null) }}
        title="Excluir fatura?"
        description={`Fatura "${deleteTarget?.number || '#' + deleteTarget?.id}" será excluída permanentemente.`}
        confirmLabel="Excluir"
        variant="destructive"
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        loading={deleteMutation.isPending}
      />
    </div>
  )
}

// ── Invoice Form Modal ──────────────────────────────────────────────────────

function InvoiceFormModal({ open, onOpenChange, invoice, onSaved }: {
  open: boolean; onOpenChange: (v: boolean) => void
  invoice: Invoice | null; onSaved: () => void
}) {
  const [form, setForm] = useState<CreateInvoiceData>({
    agreement: 0, issue_date: new Date().toISOString().split('T')[0], due_date: '', amount: '', status: 'draft',
  })
  const set = (k: keyof CreateInvoiceData, v: any) => setForm(f => ({ ...f, [k]: v }))

  useEffect(() => {
    if (open) {
      if (invoice) {
        setForm({ agreement: invoice.agreement, number: invoice.number, issue_date: invoice.issue_date, due_date: invoice.due_date, amount: invoice.amount, discount: invoice.discount, status: invoice.status, description: invoice.description, notes: invoice.notes, payment_method: invoice.payment_method })
      } else {
        setForm({ agreement: 0, issue_date: new Date().toISOString().split('T')[0], due_date: '', amount: '', status: 'draft' })
      }
    }
  }, [invoice, open])

  const { data: agreements } = useQuery({
    queryKey: ['agreements-select'],
    queryFn: () => financeApi.listAgreements({ page: 1 }),
    staleTime: 60_000,
    enabled: open,
  })

  const createMutation = useMutation({
    mutationFn: () => financeApi.createInvoice(form),
    onSuccess: () => { toast.success('Fatura criada.'); onSaved() },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Erro ao criar fatura.'),
  })
  const updateMutation = useMutation({
    mutationFn: () => financeApi.updateInvoice(invoice!.id, form),
    onSuccess: () => { toast.success('Fatura atualizada.'); onSaved() },
    onError: () => toast.error('Erro ao atualizar.'),
  })
  const isPending = createMutation.isPending || updateMutation.isPending
  const isEdit = !!invoice

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader><DialogTitle className="text-base">{isEdit ? 'Editar Fatura' : 'Nova Fatura'}</DialogTitle></DialogHeader>
        <div className="space-y-4 py-1">
          <FormField label="Contrato *">
            <Select value={String(form.agreement || '')} onValueChange={v => set('agreement', Number(v))}>
              <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue placeholder="Selecionar contrato" /></SelectTrigger>
              <SelectContent>
                {agreements?.results.map(a => (
                  <SelectItem key={a.id} value={String(a.id)}>{a.title}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Nº da Fatura">
              <Input value={form.number ?? ''} onChange={e => set('number', e.target.value)} placeholder="Automático" className="text-sm" />
            </FormField>
            <FormField label="Status">
              <Select value={form.status ?? 'draft'} onValueChange={v => set('status', v)}>
                <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(INVOICE_STATUS_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                </SelectContent>
              </Select>
            </FormField>
            <FormField label="Data de Emissão *">
              <Input type="date" value={form.issue_date} onChange={e => set('issue_date', e.target.value)} className="text-sm" />
            </FormField>
            <FormField label="Data de Vencimento *">
              <Input type="date" value={form.due_date} onChange={e => set('due_date', e.target.value)} className="text-sm" />
            </FormField>
            <FormField label="Valor (R$) *">
              <Input type="number" step="0.01" value={form.amount} onChange={e => set('amount', e.target.value)} className="text-sm" />
            </FormField>
            <FormField label="Desconto (R$)">
              <Input type="number" step="0.01" value={form.discount ?? ''} onChange={e => set('discount', e.target.value)} className="text-sm" />
            </FormField>
          </div>
          <FormField label="Descrição">
            <Textarea value={form.description ?? ''} onChange={e => set('description', e.target.value)} rows={2} className="resize-none text-sm" />
          </FormField>
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={isPending}>Cancelar</Button>
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700"
            disabled={!form.agreement || !form.amount || !form.due_date || isPending}
            onClick={() => isEdit ? updateMutation.mutate() : createMutation.mutate()}>
            {isPending ? 'Salvando…' : isEdit ? 'Atualizar' : 'Criar Fatura'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Payment Modal ────────────────────────────────────────────────────────────

function PaymentModal({ open, onOpenChange, invoice, onSaved }: {
  open: boolean; onOpenChange: (v: boolean) => void
  invoice: Invoice | null; onSaved: () => void
}) {
  const [form, setForm] = useState({ paid_at: new Date().toISOString().split('T')[0], amount: '', method: 'bank_transfer', reference: '', notes: '' })
  const set = (k: string, v: any) => setForm(f => ({ ...f, [k]: v }))

  useEffect(() => {
    if (open && invoice) {
      setForm(f => ({ ...f, amount: invoice.balance || invoice.net_amount }))
    }
  }, [invoice, open])

  const mutation = useMutation({
    mutationFn: () => financeApi.createPayment({ invoice: invoice!.id, ...form }),
    onSuccess: () => { toast.success('Pagamento registrado!'); onSaved() },
    onError: () => toast.error('Erro ao registrar pagamento.'),
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader><DialogTitle className="text-base">Registrar Pagamento</DialogTitle></DialogHeader>
        <div className="space-y-4 py-1">
          {invoice && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3">
              <p className="text-xs text-emerald-700 font-semibold">
                {invoice.number || `Fatura #${invoice.id}`} — Saldo: {formatCurrency(invoice.balance)}
              </p>
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Data do Pagamento">
              <Input type="date" value={form.paid_at} onChange={e => set('paid_at', e.target.value)} className="text-sm" />
            </FormField>
            <FormField label="Valor Pago (R$) *">
              <Input type="number" step="0.01" value={form.amount} onChange={e => set('amount', e.target.value)} className="text-sm" />
            </FormField>
          </div>
          <FormField label="Método">
            <Select value={form.method} onValueChange={v => set('method', v)}>
              <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue /></SelectTrigger>
              <SelectContent>
                {Object.entries(PAYMENT_METHOD_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
              </SelectContent>
            </Select>
          </FormField>
          <FormField label="Referência / Comprovante">
            <Input value={form.reference} onChange={e => set('reference', e.target.value)} placeholder="Nº do comprovante, PIX, etc." className="text-sm" />
          </FormField>
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700"
            disabled={!form.amount || mutation.isPending}
            onClick={() => mutation.mutate()}>
            {mutation.isPending ? 'Registrando…' : 'Confirmar Pagamento'}
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
