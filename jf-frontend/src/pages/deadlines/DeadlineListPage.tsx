import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, AlertTriangle, Clock, CheckCircle2, SlidersHorizontal } from 'lucide-react'
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
import { deadlinesApi } from '@/api/deadlines'
import { formatDate } from '@/lib/utils'
import { DEADLINE_TYPE_LABELS, DEADLINE_PRIORITY_LABELS, DEADLINE_STATUS_LABELS } from '@/lib/constants'
import { usePagination } from '@/hooks/usePagination'
import type { Deadline, CreateDeadlineData } from '@/types/deadline'
import { cn } from '@/lib/utils'

export function DeadlineListPage() {
  const { page, setPage, reset } = usePagination()
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('pending')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editTarget, setEditTarget] = useState<Deadline | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Deadline | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['deadlines', { page, status: statusFilter, priority: priorityFilter }],
    queryFn: () =>
      deadlinesApi.list({
        page,
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
      }),
    staleTime: 30_000,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deadlinesApi.delete(id),
    onSuccess: () => {
      toast.success('Prazo excluído.')
      queryClient.invalidateQueries({ queryKey: ['deadlines'] })
      setDeleteTarget(null)
    },
    onError: () => toast.error('Erro ao excluir.'),
  })

  const overdueCount = data?.results.filter((d) => d.status_info?.label === 'overdue').length ?? 0

  const columns = [
    {
      key: 'urgency',
      header: '',
      width: 'w-1 px-0 pl-3',
      render: (row: Deadline) => (
        <div className={cn(
          'w-1 h-8 rounded-full',
          row.status_info?.label === 'overdue' ? 'bg-red-500' :
          row.status_info?.label === 'today' ? 'bg-amber-400' :
          row.status_info?.label === 'soon' ? 'bg-blue-400' : 'bg-slate-200',
        )} />
      ),
    },
    {
      key: 'title',
      header: 'Prazo',
      render: (row: Deadline) => (
        <div>
          <p className="text-sm font-medium text-slate-900">{row.title}</p>
          {row.related_process && (
            <p className="text-[11px] text-slate-400 font-mono mt-0.5">{row.related_process.number}</p>
          )}
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Tipo',
      render: (row: Deadline) => <StatusBadge value={row.type} variant="deadline-type" />,
    },
    {
      key: 'due_date',
      header: 'Vencimento',
      render: (row: Deadline) => (
        <div>
          <p className={cn(
            'text-sm font-semibold',
            row.status_info?.label === 'overdue' ? 'text-red-600' :
            row.status_info?.label === 'today' ? 'text-amber-600' : 'text-slate-700',
          )}>
            {formatDate(row.due_date)}
          </p>
          {row.status_info && (
            <p className={cn(
              'text-[11px] mt-0.5',
              row.status_info.label === 'overdue' ? 'text-red-400' :
              row.status_info.label === 'today' ? 'text-amber-500' : 'text-slate-400',
            )}>
              {row.status_info.text}
            </p>
          )}
        </div>
      ),
    },
    {
      key: 'priority',
      header: 'Prioridade',
      render: (row: Deadline) => <StatusBadge value={row.priority} variant="deadline-priority" />,
    },
    {
      key: 'status',
      header: 'Status',
      render: (row: Deadline) => <StatusBadge value={row.status} variant="deadline-status" />,
    },
    {
      key: 'responsible',
      header: 'Responsável',
      render: (row: Deadline) => <span className="text-xs text-slate-500">{row.responsible_name ?? '—'}</span>,
    },
    {
      key: 'actions',
      header: '',
      render: (row: Deadline) => (
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          <Button
            variant="ghost" size="sm"
            onClick={() => { setEditTarget(row); setShowForm(true) }}
            className="h-7 px-2 text-xs text-slate-500 hover:text-slate-800"
          >
            Editar
          </Button>
          <Button
            variant="ghost" size="sm"
            onClick={() => setDeleteTarget(row)}
            className="h-7 px-2 text-xs text-red-400 hover:text-red-600"
          >
            Excluir
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div className="max-w-7xl mx-auto page-enter">
      <PageHeader
        title="Prazos"
        subtitle={data ? `${data.count} prazo${data.count !== 1 ? 's' : ''}` : undefined}
        breadcrumbs={[{ label: 'JuridicFlow' }, { label: 'Prazos' }]}
        actions={
          <Button
            onClick={() => { setEditTarget(null); setShowForm(true) }}
            className="bg-blue-600 hover:bg-blue-700 gap-2 h-9"
          >
            <Plus size={15} /> Novo Prazo
          </Button>
        }
      />

      {overdueCount > 0 && statusFilter !== 'overdue' && (
        <div className="flex items-center gap-3 p-3.5 mb-5 bg-red-50 border border-red-200 rounded-xl">
          <AlertTriangle size={16} className="text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-700">
            <span className="font-semibold">{overdueCount} prazo{overdueCount !== 1 ? 's' : ''} vencido{overdueCount !== 1 ? 's' : ''}</span>
            {' '}— requer ação imediata.{' '}
            <button onClick={() => { setStatusFilter('overdue'); reset() }} className="underline">
              Ver vencidos
            </button>
          </p>
        </div>
      )}

      <div className="flex flex-wrap gap-2 mb-5">
        {[
          { label: 'Pendentes', value: 'pending', icon: <Clock size={12} /> },
          { label: `Vencidos${overdueCount > 0 ? ` (${overdueCount})` : ''}`, value: 'overdue', icon: <AlertTriangle size={12} /> },
          { label: 'Concluídos', value: 'completed', icon: <CheckCircle2 size={12} /> },
          { label: 'Todos', value: '' },
        ].map(({ label, value, icon }) => (
          <Button
            key={value}
            variant={statusFilter === value ? 'default' : 'outline'}
            size="sm"
            className={cn(
              'h-9 gap-1.5 text-xs',
              statusFilter === value ? 'bg-blue-600 hover:bg-blue-700' : '',
              value === 'overdue' && statusFilter !== 'overdue' && overdueCount > 0
                ? 'border-red-200 text-red-600 hover:bg-red-50' : '',
            )}
            onClick={() => { setStatusFilter(value); reset() }}
          >
            {icon}{label}
          </Button>
        ))}

        <div className="ml-auto">
          <Button
            variant="outline" size="sm"
            onClick={() => setShowFilters(!showFilters)}
            className={`gap-2 h-9 ${priorityFilter ? 'border-blue-300 text-blue-600 bg-blue-50' : ''}`}
          >
            <SlidersHorizontal size={14} /> Filtros
          </Button>
        </div>
      </div>

      {showFilters && (
        <div className="flex gap-3 mb-5 p-4 bg-slate-50 rounded-xl border border-slate-200 animate-fade-in">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-500">Prioridade</label>
            <Select
              value={priorityFilter || 'all'}
              onValueChange={(v) => { setPriorityFilter(v === 'all' ? '' : v); reset() }}
            >
              <SelectTrigger className="h-9 w-36 bg-white text-sm border-slate-200">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                {Object.entries(DEADLINE_PRIORITY_LABELS).map(([k, v]) => (
                  <SelectItem key={k} value={k}>{v}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {priorityFilter && (
            <div className="flex items-end">
              <Button variant="ghost" size="sm" className="h-9 text-xs text-slate-500"
                onClick={() => { setPriorityFilter(''); reset() }}>
                Limpar
              </Button>
            </div>
          )}
        </div>
      )}

      <DataTable
        columns={columns}
        data={data?.results ?? []}
        keyFn={(row) => row.id}
        isLoading={isLoading}
        total={data?.count}
        page={page}
        pageSize={25}
        onPageChange={setPage}
        emptyTitle="Nenhum prazo encontrado"
        emptyDescription="Clique em 'Novo Prazo' para adicionar."
        emptyAction={
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700 gap-2"
            onClick={() => { setEditTarget(null); setShowForm(true) }}>
            <Plus size={14} /> Novo Prazo
          </Button>
        }
      />

      <DeadlineFormModal
        open={showForm}
        onOpenChange={(v) => { setShowForm(v); if (!v) setEditTarget(null) }}
        deadline={editTarget}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ['deadlines'] })
          queryClient.invalidateQueries({ queryKey: ['dashboard'] })
          setShowForm(false)
          setEditTarget(null)
        }}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(v) => { if (!v) setDeleteTarget(null) }}
        title="Excluir prazo?"
        description={`"${deleteTarget?.title}" será excluído permanentemente.`}
        confirmLabel="Excluir"
        variant="destructive"
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        loading={deleteMutation.isPending}
      />
    </div>
  )
}

// ── Deadline Form Modal ───────────────────────────────────────────────────────

interface DeadlineFormModalProps {
  open: boolean
  onOpenChange: (v: boolean) => void
  deadline: Deadline | null
  onSaved: () => void
}

function emptyForm(): CreateDeadlineData {
  return { title: '', due_date: '', type: 'legal', priority: 'medium', status: 'pending', description: '' }
}

function DeadlineFormModal({ open, onOpenChange, deadline, onSaved }: DeadlineFormModalProps) {
  const [form, setForm] = useState<CreateDeadlineData>(emptyForm())

  useEffect(() => {
    if (open) {
      if (deadline) {
        setForm({
          title: deadline.title,
          due_date: deadline.due_date,
          type: deadline.type,
          priority: deadline.priority,
          status: deadline.status,
          description: deadline.description ?? '',
          responsible: deadline.responsible ?? undefined,
          process_id: deadline.related_process?.id ?? null,
        })
      } else {
        setForm(emptyForm())
      }
    }
  }, [deadline, open])

  const createMutation = useMutation({
    mutationFn: () => deadlinesApi.create(form),
    onSuccess: () => { toast.success('Prazo criado.'); onSaved() },
    onError: (err: any) => toast.error(err?.response?.data?.detail ?? 'Erro ao criar prazo.'),
  })

  const updateMutation = useMutation({
    mutationFn: () => deadlinesApi.update(deadline!.id, form),
    onSuccess: () => { toast.success('Prazo atualizado.'); onSaved() },
    onError: () => toast.error('Erro ao atualizar prazo.'),
  })

  const isPending = createMutation.isPending || updateMutation.isPending
  const isEdit = !!deadline
  const set = (key: keyof CreateDeadlineData, value: any) =>
    setForm((prev) => ({ ...prev, [key]: value }))

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-base">{isEdit ? 'Editar Prazo' : 'Novo Prazo'}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-1">
          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-slate-600">Título *</Label>
            <Input
              value={form.title}
              onChange={(e) => set('title', e.target.value)}
              placeholder="Ex: Contestação — Prazo fatal"
              className="text-sm"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-slate-600">Vencimento *</Label>
              <Input type="date" value={form.due_date} onChange={(e) => set('due_date', e.target.value)} className="text-sm" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-slate-600">Status</Label>
              <Select value={form.status ?? 'pending'} onValueChange={(v) => set('status', v)}>
                <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(DEADLINE_STATUS_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-slate-600">Tipo</Label>
              <Select value={form.type ?? 'legal'} onValueChange={(v) => set('type', v)}>
                <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(DEADLINE_TYPE_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-slate-600">Prioridade</Label>
              <Select value={form.priority ?? 'medium'} onValueChange={(v) => set('priority', v)}>
                <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(DEADLINE_PRIORITY_LABELS).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-slate-600">Descrição</Label>
            <Textarea
              value={form.description ?? ''}
              onChange={(e) => set('description', e.target.value)}
              placeholder="Detalhes adicionais sobre o prazo"
              rows={2}
              className="resize-none text-sm"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={isPending}>
            Cancelar
          </Button>
          <Button
            size="sm"
            className="bg-blue-600 hover:bg-blue-700"
            disabled={!form.title || !form.due_date || isPending}
            onClick={() => isEdit ? updateMutation.mutate() : createMutation.mutate()}
          >
            {isPending ? 'Salvando…' : isEdit ? 'Atualizar' : 'Criar Prazo'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
