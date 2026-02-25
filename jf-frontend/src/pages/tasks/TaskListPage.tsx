import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, CheckCircle2, Clock, AlertTriangle, SlidersHorizontal } from 'lucide-react'
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
import { tasksApi } from '@/api/tasks'
import { formatDate, formatRelative, initials } from '@/lib/utils'
import { TASK_STATUS_LABELS, TASK_PRIORITY_LABELS } from '@/lib/constants'
import { usePagination } from '@/hooks/usePagination'
import { cn } from '@/lib/utils'
import type { Task, CreateTaskData } from '@/types/task'

const PRIORITY_COLORS: Record<string, string> = {
  low: 'bg-slate-200',
  medium: 'bg-blue-400',
  high: 'bg-amber-400',
  critical: 'bg-red-500',
}

export function TaskListPage() {
  const { page, setPage, reset } = usePagination()
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editTarget, setEditTarget] = useState<Task | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Task | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['tasks', { page, status: statusFilter, priority: priorityFilter }],
    queryFn: () => tasksApi.list({
      page,
      status: statusFilter || undefined,
      priority: priorityFilter || undefined,
    }),
    staleTime: 30_000,
  })

  const quickUpdateMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) => tasksApi.update(id, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks'] }),
    onError: () => toast.error('Erro ao atualizar status.'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => tasksApi.delete(id),
    onSuccess: () => {
      toast.success('Tarefa excluída.')
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
      setDeleteTarget(null)
    },
    onError: () => toast.error('Erro ao excluir.'),
  })

  const columns = [
    {
      key: 'priority_bar',
      header: '',
      width: 'w-1 px-0 pl-3',
      render: (row: Task) => (
        <div className={cn('w-1 h-8 rounded-full', PRIORITY_COLORS[row.priority] ?? 'bg-slate-200')} />
      ),
    },
    {
      key: 'title',
      header: 'Tarefa',
      render: (row: Task) => (
        <div>
          <p className={cn('text-sm font-medium', row.status === 'done' ? 'line-through text-slate-400' : 'text-slate-900')}>
            {row.title}
          </p>
          {row.description && (
            <p className="text-[11px] text-slate-400 mt-0.5 truncate max-w-xs">{row.description}</p>
          )}
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row: Task) => (
        <Select
          value={row.status}
          onValueChange={v => quickUpdateMutation.mutate({ id: row.id, status: v })}
        >
          <SelectTrigger className="h-7 text-xs border-slate-200 w-36 bg-white" onClick={e => e.stopPropagation()}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(TASK_STATUS_LABELS).map(([k, v]) => (
              <SelectItem key={k} value={k} className="text-xs">{v}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      ),
    },
    {
      key: 'priority',
      header: 'Prioridade',
      render: (row: Task) => <StatusBadge value={row.priority} variant="task-priority" />,
    },
    {
      key: 'due_date',
      header: 'Prazo',
      render: (row: Task) => row.due_date
        ? <span className="text-xs text-slate-500">{formatDate(row.due_date)}</span>
        : <span className="text-slate-300 text-xs">—</span>,
    },
    {
      key: 'assigned_to',
      header: 'Responsável',
      render: (row: Task) => row.assigned_to_name ? (
        <div className="flex items-center gap-1.5">
          <div className="w-5 h-5 rounded-md bg-slate-100 flex items-center justify-center text-[9px] font-bold text-slate-500">
            {initials(row.assigned_to_name)}
          </div>
          <span className="text-xs text-slate-500">{row.assigned_to_name.split(' ')[0]}</span>
        </div>
      ) : <span className="text-slate-300 text-xs">—</span>,
    },
    {
      key: 'created',
      header: 'Criado',
      render: (row: Task) => <span className="text-[11px] text-slate-400">{formatRelative(row.created_at)}</span>,
    },
    {
      key: 'actions',
      header: '',
      render: (row: Task) => (
        <div className="flex gap-1" onClick={e => e.stopPropagation()}>
          {row.status !== 'done' && (
            <Button
              variant="ghost" size="sm"
              className="h-7 px-2 text-[10px] text-emerald-600 hover:bg-emerald-50"
              onClick={() => quickUpdateMutation.mutate({ id: row.id, status: 'done' })}
            >
              <CheckCircle2 size={11} className="mr-1" /> Concluir
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

  const hasFilters = !!(statusFilter || priorityFilter)

  return (
    <div className="max-w-7xl mx-auto page-enter">
      <PageHeader
        title="Tarefas"
        subtitle={data ? `${data.count} tarefa${data.count !== 1 ? 's' : ''}` : undefined}
        breadcrumbs={[{ label: 'JuridicFlow' }, { label: 'Tarefas' }]}
        actions={
          <Button onClick={() => { setEditTarget(null); setShowForm(true) }} className="bg-blue-600 hover:bg-blue-700 gap-2 h-9">
            <Plus size={15} /> Nova Tarefa
          </Button>
        }
      />

      {/* Status filter tabs */}
      <div className="flex flex-wrap gap-2 mb-5">
        {[
          { label: 'Todas', value: '' },
          { label: 'A Fazer', value: 'todo', icon: <Clock size={11} /> },
          { label: 'Em Andamento', value: 'in_progress', icon: <AlertTriangle size={11} /> },
          { label: 'Revisão', value: 'review' },
          { label: 'Concluídas', value: 'done', icon: <CheckCircle2 size={11} /> },
        ].map(({ label, value, icon }) => (
          <Button
            key={value}
            variant={statusFilter === value ? 'default' : 'outline'}
            size="sm"
            className={cn('h-9 gap-1.5 text-xs', statusFilter === value ? 'bg-blue-600 hover:bg-blue-700' : '')}
            onClick={() => { setStatusFilter(value); reset() }}
          >
            {icon}{label}
          </Button>
        ))}

        <div className="ml-auto">
          <Button
            variant="outline" size="sm"
            className={cn('gap-2 h-9', priorityFilter ? 'border-blue-300 text-blue-600 bg-blue-50' : '')}
            onClick={() => setShowFilters(!showFilters)}
          >
            <SlidersHorizontal size={14} /> Prioridade
          </Button>
        </div>
      </div>

      {showFilters && (
        <div className="flex gap-3 mb-5 p-4 bg-slate-50 rounded-xl border border-slate-200 animate-fade-in">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-500">Prioridade</label>
            <Select value={priorityFilter || 'all'} onValueChange={v => { setPriorityFilter(v === 'all' ? '' : v); reset() }}>
              <SelectTrigger className="h-9 w-36 bg-white text-sm border-slate-200"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                {Object.entries(TASK_PRIORITY_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          {priorityFilter && (
            <div className="flex items-end">
              <Button variant="ghost" size="sm" className="h-9 text-xs text-slate-500"
                onClick={() => { setPriorityFilter(''); reset() }}>Limpar</Button>
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
        emptyTitle="Nenhuma tarefa encontrada"
        emptyDescription="Clique em 'Nova Tarefa' para criar a primeira."
        emptyAction={
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700 gap-2" onClick={() => setShowForm(true)}>
            <Plus size={14} /> Nova Tarefa
          </Button>
        }
      />

      <TaskFormModal
        open={showForm}
        onOpenChange={v => { setShowForm(v); if (!v) setEditTarget(null) }}
        task={editTarget}
        onSaved={() => {
          queryClient.invalidateQueries({ queryKey: ['tasks'] })
          setShowForm(false)
          setEditTarget(null)
        }}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={v => { if (!v) setDeleteTarget(null) }}
        title="Excluir tarefa?"
        description={`"${deleteTarget?.title}" será excluída permanentemente.`}
        confirmLabel="Excluir"
        variant="destructive"
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        loading={deleteMutation.isPending}
      />
    </div>
  )
}

// ── Task Form Modal ──────────────────────────────────────────────────────────

function TaskFormModal({ open, onOpenChange, task, onSaved }: {
  open: boolean; onOpenChange: (v: boolean) => void
  task: Task | null; onSaved: () => void
}) {
  const [form, setForm] = useState<CreateTaskData>({
    title: '', description: '', status: 'todo', priority: 'medium', due_date: null,
  })
  const set = (k: keyof CreateTaskData, v: any) => setForm(f => ({ ...f, [k]: v }))

  useEffect(() => {
    if (open) {
      if (task) {
        setForm({
          title: task.title, description: task.description ?? '',
          status: task.status, priority: task.priority,
          assigned_to: task.assigned_to, due_date: task.due_date,
        })
      } else {
        setForm({ title: '', description: '', status: 'todo', priority: 'medium', due_date: null })
      }
    }
  }, [task, open])

  const createMutation = useMutation({
    mutationFn: () => tasksApi.create(form),
    onSuccess: () => { toast.success('Tarefa criada.'); onSaved() },
    onError: () => toast.error('Erro ao criar tarefa.'),
  })
  const updateMutation = useMutation({
    mutationFn: () => tasksApi.update(task!.id, form),
    onSuccess: () => { toast.success('Tarefa atualizada.'); onSaved() },
    onError: () => toast.error('Erro ao atualizar.'),
  })
  const isPending = createMutation.isPending || updateMutation.isPending
  const isEdit = !!task

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader><DialogTitle className="text-base">{isEdit ? 'Editar Tarefa' : 'Nova Tarefa'}</DialogTitle></DialogHeader>
        <div className="space-y-4 py-1">
          <FormField label="Título *">
            <Input value={form.title} onChange={e => set('title', e.target.value)} placeholder="Descrição curta da tarefa" className="text-sm" autoFocus />
          </FormField>
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Status">
              <Select value={form.status ?? 'todo'} onValueChange={v => set('status', v)}>
                <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(TASK_STATUS_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                </SelectContent>
              </Select>
            </FormField>
            <FormField label="Prioridade">
              <Select value={form.priority ?? 'medium'} onValueChange={v => set('priority', v)}>
                <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(TASK_PRIORITY_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                </SelectContent>
              </Select>
            </FormField>
          </div>
          <FormField label="Prazo">
            <Input type="date" value={form.due_date ?? ''} onChange={e => set('due_date', e.target.value || null)} className="text-sm" />
          </FormField>
          <FormField label="Descrição">
            <Textarea value={form.description ?? ''} onChange={e => set('description', e.target.value)} rows={3} className="resize-none text-sm" placeholder="Detalhes, contexto, referências…" />
          </FormField>
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={isPending}>Cancelar</Button>
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700"
            disabled={!form.title || isPending}
            onClick={() => isEdit ? updateMutation.mutate() : createMutation.mutate()}>
            {isPending ? 'Salvando…' : isEdit ? 'Atualizar' : 'Criar Tarefa'}
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
