import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, SlidersHorizontal } from 'lucide-react'
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
import { EXPENSE_CATEGORY_LABELS, EXPENSE_STATUS_LABELS, PAYMENT_METHOD_LABELS } from '@/lib/constants'
import { usePagination } from '@/hooks/usePagination'
import { cn } from '@/lib/utils'
import type { Expense, CreateExpenseData } from '@/types/finance'

export function ExpenseListPage() {
  const { page, setPage, reset } = usePagination()
  const queryClient = useQueryClient()
  const [categoryFilter, setCategoryFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editTarget, setEditTarget] = useState<Expense | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Expense | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['expenses', { page, category: categoryFilter, status: statusFilter }],
    queryFn: () => financeApi.listExpenses({
      page,
      category: categoryFilter || undefined,
      status: statusFilter || undefined,
    }),
    staleTime: 30_000,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => financeApi.deleteExpense(id),
    onSuccess: () => {
      toast.success('Despesa excluída.')
      queryClient.invalidateQueries({ queryKey: ['expenses'] })
      setDeleteTarget(null)
    },
    onError: () => toast.error('Erro ao excluir.'),
  })

  const totalShown = (data?.results ?? []).reduce((s, e) => s + parseFloat(e.amount), 0)

  const columns = [
    {
      key: 'title',
      header: 'Despesa',
      render: (row: Expense) => (
        <div>
          <p className="text-sm font-medium text-slate-900">{row.title}</p>
          {row.supplier && <p className="text-[11px] text-slate-400">{row.supplier}</p>}
        </div>
      ),
    },
    {
      key: 'category',
      header: 'Categoria',
      render: (row: Expense) => (
        <span className="text-xs text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md">
          {EXPENSE_CATEGORY_LABELS[row.category] ?? row.category}
        </span>
      ),
    },
    {
      key: 'amount',
      header: 'Valor',
      render: (row: Expense) => (
        <span className="text-sm font-semibold text-slate-800">{formatCurrency(row.amount)}</span>
      ),
    },
    {
      key: 'date',
      header: 'Data',
      render: (row: Expense) => <span className="text-xs text-slate-500">{formatDate(row.date)}</span>,
    },
    {
      key: 'due_date',
      header: 'Vencimento',
      render: (row: Expense) => row.due_date
        ? <span className="text-xs text-slate-500">{formatDate(row.due_date)}</span>
        : <span className="text-slate-300 text-xs">—</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (row: Expense) => <StatusBadge value={row.status} variant="expense-status" />,
    },
    {
      key: 'actions',
      header: '',
      render: (row: Expense) => (
        <div className="flex gap-1" onClick={e => e.stopPropagation()}>
          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-slate-500"
            onClick={() => { setEditTarget(row); setShowForm(true) }}>Editar</Button>
          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs text-red-400"
            onClick={() => setDeleteTarget(row)}>Excluir</Button>
        </div>
      ),
    },
  ]

  const hasFilters = !!(categoryFilter || statusFilter)

  return (
    <div className="max-w-7xl mx-auto page-enter">
      <PageHeader
        title="Despesas"
        subtitle={data ? `${data.count} despesa${data.count !== 1 ? 's' : ''} · Total exibido: ${formatCurrency(totalShown)}` : undefined}
        breadcrumbs={[{ label: 'Financeiro', href: '/app/financeiro' }, { label: 'Despesas' }]}
        actions={
          <Button onClick={() => { setEditTarget(null); setShowForm(true) }} className="bg-blue-600 hover:bg-blue-700 gap-2 h-9">
            <Plus size={15} /> Nova Despesa
          </Button>
        }
      />

      <div className="flex gap-3 mb-5">
        <Button
          variant="outline" size="sm"
          onClick={() => setShowFilters(!showFilters)}
          className={cn('gap-2 h-9', hasFilters ? 'border-blue-300 text-blue-600 bg-blue-50' : '')}
        >
          <SlidersHorizontal size={14} /> Filtros
          {hasFilters && (
            <span className="w-4 h-4 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center">
              {[categoryFilter, statusFilter].filter(Boolean).length}
            </span>
          )}
        </Button>
      </div>

      {showFilters && (
        <div className="flex flex-wrap gap-3 mb-5 p-4 bg-slate-50 rounded-xl border border-slate-200 animate-fade-in">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-500">Categoria</label>
            <Select value={categoryFilter || 'all'} onValueChange={v => { setCategoryFilter(v === 'all' ? '' : v); reset() }}>
              <SelectTrigger className="h-9 w-48 bg-white text-sm border-slate-200"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                {Object.entries(EXPENSE_CATEGORY_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-500">Status</label>
            <Select value={statusFilter || 'all'} onValueChange={v => { setStatusFilter(v === 'all' ? '' : v); reset() }}>
              <SelectTrigger className="h-9 w-36 bg-white text-sm border-slate-200"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                {Object.entries(EXPENSE_STATUS_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          {hasFilters && (
            <div className="flex items-end">
              <Button variant="ghost" size="sm" className="h-9 text-xs text-slate-500"
                onClick={() => { setCategoryFilter(''); setStatusFilter(''); reset() }}>Limpar</Button>
            </div>
          )}
        </div>
      )}

      <DataTable
        columns={columns}
        data={data?.results ?? []}
        keyFn={r => r.id}
        isLoading={isLoading}
        total={data?.count}
        page={page}
        pageSize={25}
        onPageChange={setPage}
        emptyTitle="Nenhuma despesa encontrada"
        emptyDescription="Registre uma nova despesa do escritório."
        emptyAction={
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700 gap-2" onClick={() => setShowForm(true)}>
            <Plus size={14} /> Nova Despesa
          </Button>
        }
      />

      <ExpenseFormModal
        open={showForm}
        onOpenChange={v => { setShowForm(v); if (!v) setEditTarget(null) }}
        expense={editTarget}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ['expenses'] })
          setShowForm(false)
          setEditTarget(null)
        }}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={v => { if (!v) setDeleteTarget(null) }}
        title="Excluir despesa?"
        description={`"${deleteTarget?.title}" será excluída permanentemente.`}
        confirmLabel="Excluir"
        variant="destructive"
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        loading={deleteMutation.isPending}
      />
    </div>
  )
}

// ── Expense Form Modal ───────────────────────────────────────────────────────

function ExpenseFormModal({ open, onOpenChange, expense, onSaved }: {
  open: boolean; onOpenChange: (v: boolean) => void
  expense: Expense | null; onSaved: () => void
}) {
  const [form, setForm] = useState<CreateExpenseData>({
    title: '', date: new Date().toISOString().split('T')[0], amount: '',
    category: 'other', status: 'pending',
  })
  const set = (k: keyof CreateExpenseData, v: any) => setForm(f => ({ ...f, [k]: v }))

  useEffect(() => {
    if (open) {
      if (expense) {
        setForm({
          title: expense.title, description: expense.description ?? '',
          category: expense.category, date: expense.date,
          due_date: expense.due_date ?? '', amount: expense.amount,
          status: expense.status, payment_method: expense.payment_method ?? '',
          supplier: expense.supplier ?? '', reference: expense.reference ?? '',
          notes: expense.notes ?? '',
        })
      } else {
        setForm({ title: '', date: new Date().toISOString().split('T')[0], amount: '', category: 'other', status: 'pending' })
      }
    }
  }, [expense, open])

  const createMutation = useMutation({
    mutationFn: () => financeApi.createExpense(form),
    onSuccess: () => { toast.success('Despesa registrada.'); onSaved() },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Erro ao criar despesa.'),
  })
  const updateMutation = useMutation({
    mutationFn: () => financeApi.updateExpense(expense!.id, form),
    onSuccess: () => { toast.success('Despesa atualizada.'); onSaved() },
    onError: () => toast.error('Erro ao atualizar.'),
  })
  const isPending = createMutation.isPending || updateMutation.isPending
  const isEdit = !!expense

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader><DialogTitle className="text-base">{isEdit ? 'Editar Despesa' : 'Nova Despesa'}</DialogTitle></DialogHeader>
        <div className="space-y-4 py-1">
          <FormField label="Título *">
            <Input value={form.title} onChange={e => set('title', e.target.value)} placeholder="Ex: Aluguel Junho/2025" className="text-sm" />
          </FormField>
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Categoria">
              <Select value={form.category ?? 'other'} onValueChange={v => set('category', v)}>
                <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(EXPENSE_CATEGORY_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                </SelectContent>
              </Select>
            </FormField>
            <FormField label="Status">
              <Select value={form.status ?? 'pending'} onValueChange={v => set('status', v)}>
                <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(EXPENSE_STATUS_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                </SelectContent>
              </Select>
            </FormField>
            <FormField label="Valor (R$) *">
              <Input type="number" step="0.01" value={form.amount} onChange={e => set('amount', e.target.value)} className="text-sm" />
            </FormField>
            <FormField label="Data *">
              <Input type="date" value={form.date} onChange={e => set('date', e.target.value)} className="text-sm" />
            </FormField>
            <FormField label="Vencimento">
              <Input type="date" value={form.due_date ?? ''} onChange={e => set('due_date', e.target.value)} className="text-sm" />
            </FormField>
            <FormField label="Método de Pagamento">
              <Select value={form.payment_method ?? ''} onValueChange={v => set('payment_method', v)}>
                <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue placeholder="Selecionar" /></SelectTrigger>
                <SelectContent>
                  {Object.entries(PAYMENT_METHOD_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                </SelectContent>
              </Select>
            </FormField>
          </div>
          <FormField label="Fornecedor">
            <Input value={form.supplier ?? ''} onChange={e => set('supplier', e.target.value)} placeholder="Nome do fornecedor" className="text-sm" />
          </FormField>
          <FormField label="Observações">
            <Textarea value={form.notes ?? ''} onChange={e => set('notes', e.target.value)} rows={2} className="resize-none text-sm" />
          </FormField>
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={isPending}>Cancelar</Button>
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700"
            disabled={!form.title || !form.amount || !form.date || isPending}
            onClick={() => isEdit ? updateMutation.mutate() : createMutation.mutate()}>
            {isPending ? 'Salvando…' : isEdit ? 'Atualizar' : 'Registrar Despesa'}
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
