import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, CheckCircle2, Clock, AlertTriangle, SlidersHorizontal, UserCheck, X, Search, AlertCircle } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { PageHeader } from '@/components/layout/PageHeader'
import { DataTable } from '@/components/shared/DataTable'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { tasksApi } from '@/api/tasks'
import { formatDate, formatRelative, initials } from '@/lib/utils'
import { TASK_STATUS_LABELS, TASK_PRIORITY_LABELS } from '@/lib/constants'
import { usePagination } from '@/hooks/usePagination'
import { useDebounce } from '@/hooks/useDebounce'
import { cn } from '@/lib/utils'
import api from '@/api/client'
import type { Task, CreateTaskData } from '@/types/task'

const PRIORITY_COLORS: Record<string, string> = {
  low: 'bg-slate-200',
  medium: 'bg-blue-400',
  high: 'bg-amber-400',
  critical: 'bg-red-500',
}

// ── User search hook ──────────────────────────────────────────────────────────
function useUserSearch(q: string) {
  return useQuery({
    queryKey: ['user-search', q],
    queryFn: () => api.get<{ results: { id: number; name: string; email: string }[] }>(
      '/auth/users/search/', { params: { q } }
    ).then(r => r.data.results),
    enabled: q.length >= 2,
    staleTime: 30_000,
  })
}

// ── Process search hook ───────────────────────────────────────────────────────
function useProcessSearch(q: string) {
  return useQuery({
    queryKey: ['process-search-task', q],
    queryFn: () => api.get<{ results: { id: number; title: string; case_number: string }[] }>(
      '/search/', { params: { q, types: 'process' } }
    ).then(r => (r.data as any).results?.filter((x: any) => x.type === 'process') ?? []),
    enabled: q.length >= 2,
    staleTime: 30_000,
  })
}

// ── User Selector Component ───────────────────────────────────────────────────
interface UserOption { id: number; name: string; email: string }

function UserSelector({
  value, onChange, error,
}: {
  value: UserOption | null
  onChange: (u: UserOption | null) => void
  error?: string
}) {
  const [q, setQ] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [touched, setTouched] = useState(false)
  const debouncedQ = useDebounce(q, 250)
  const { data: results = [], isFetching } = useUserSearch(debouncedQ)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setShowDropdown(false)
        // Check if typed text doesn't match selected user
        if (q && !value) setTouched(true)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [q, value])

  const handleSelect = (u: UserOption) => {
    onChange(u)
    setQ('')
    setShowDropdown(false)
    setTouched(false)
  }

  const handleClear = () => {
    onChange(null)
    setQ('')
    setTouched(false)
  }

  const noMatch = touched && q.length >= 2 && results.length === 0 && !isFetching

  return (
    <div ref={ref} className="relative">
      {value ? (
        <div className="flex items-center gap-2 p-2 rounded-md border border-slate-200 bg-slate-50">
          <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center text-white text-[10px] font-semibold">
            {initials(value.name)}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-slate-800 truncate">{value.name}</p>
            <p className="text-[10px] text-slate-400 truncate">{value.email}</p>
          </div>
          <button onClick={handleClear} className="text-slate-400 hover:text-slate-600">
            <X size={13} />
          </button>
        </div>
      ) : (
        <div className="relative">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <Input
            value={q}
            onChange={e => { setQ(e.target.value); setShowDropdown(true); setTouched(false) }}
            onFocus={() => setShowDropdown(true)}
            onBlur={() => setTimeout(() => { setTouched(true); setShowDropdown(false) }, 150)}
            placeholder="Digite nome ou e-mail…"
            className={cn('pl-7 text-sm', (noMatch || error) && 'border-red-400')}
          />
        </div>
      )}

      {/* Suggestions dropdown */}
      {showDropdown && !value && q.length >= 2 && (
        <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-lg overflow-hidden">
          {isFetching ? (
            <p className="text-xs text-slate-400 p-3">Buscando…</p>
          ) : results.length === 0 ? (
            <div className="p-3 flex items-center gap-2 text-red-500">
              <AlertCircle size={13} />
              <span className="text-xs">Nenhum usuário encontrado com "{q}"</span>
            </div>
          ) : (
            results.map(u => (
              <button
                key={u.id}
                onMouseDown={() => handleSelect(u)}
                className="w-full flex items-center gap-2 px-3 py-2 hover:bg-slate-50 text-left"
              >
                <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-white text-[10px] font-semibold flex-shrink-0">
                  {initials(u.name)}
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-800">{u.name}</p>
                  <p className="text-[10px] text-slate-400">{u.email}</p>
                </div>
              </button>
            ))
          )}
        </div>
      )}

      {/* Error messages */}
      {noMatch && !value && (
        <p className="text-xs text-red-500 mt-1 flex items-center gap-1">
          <AlertCircle size={11} /> Usuário não encontrado. Escolha um da lista.
        </p>
      )}
      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
    </div>
  )
}

// ── Process Selector Component ────────────────────────────────────────────────
interface ProcessOption { id: number; title: string; subtitle?: string }

function ProcessSelector({
  value, onChange,
}: {
  value: ProcessOption | null
  onChange: (p: ProcessOption | null) => void
}) {
  const [q, setQ] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const debouncedQ = useDebounce(q, 250)
  const { data: results = [], isFetching } = useProcessSearch(debouncedQ)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setShowDropdown(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} className="relative">
      {value ? (
        <div className="flex items-center gap-2 p-2 rounded-md border border-slate-200 bg-slate-50">
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-slate-800 truncate">{value.title}</p>
            {value.subtitle && <p className="text-[10px] text-slate-400 truncate font-mono">{value.subtitle}</p>}
          </div>
          <button onClick={() => onChange(null)} className="text-slate-400 hover:text-slate-600">
            <X size={13} />
          </button>
        </div>
      ) : (
        <div className="relative">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <Input
            value={q}
            onChange={e => { setQ(e.target.value); setShowDropdown(true) }}
            onFocus={() => setShowDropdown(true)}
            placeholder="Buscar por assunto, número ou partes…"
            className="pl-7 text-sm"
          />
        </div>
      )}

      {showDropdown && !value && q.length >= 2 && (
        <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-lg overflow-hidden">
          {isFetching ? (
            <p className="text-xs text-slate-400 p-3">Buscando…</p>
          ) : results.length === 0 ? (
            <p className="text-xs text-slate-400 p-3">Nenhum processo encontrado.</p>
          ) : (
            (results as any[]).map((p: any) => (
              <button
                key={p.id}
                onMouseDown={() => { onChange({ id: p.id, title: p.title, subtitle: p.subtitle }); setQ(''); setShowDropdown(false) }}
                className="w-full flex flex-col items-start px-3 py-2 hover:bg-slate-50 text-left"
              >
                <p className="text-xs font-medium text-slate-800 truncate">{p.title}</p>
                <p className="text-[10px] text-slate-400 font-mono">{p.subtitle}</p>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
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
      key: 'priority_bar', header: '', width: 'w-1 px-0 pl-3',
      render: (row: Task) => (
        <div className={cn('w-1 h-8 rounded-full', PRIORITY_COLORS[row.priority] ?? 'bg-slate-200')} />
      ),
    },
    {
      key: 'title', header: 'Tarefa',
      render: (row: Task) => (
        <div>
          <p className={cn('text-sm font-medium', row.status === 'done' ? 'line-through text-slate-400' : 'text-slate-900')}>
            {row.title}
          </p>
          {row.description && (
            <p className="text-[11px] text-slate-400 mt-0.5 truncate max-w-xs">{row.description}</p>
          )}
          {/* Show process link if exists */}
          {(row as any).process_title && (
            <p className="text-[10px] text-blue-500 mt-0.5 truncate max-w-xs">
              🔗 {(row as any).process_title}
            </p>
          )}
        </div>
      ),
    },
    {
      key: 'status', header: 'Status',
      render: (row: Task) => (
        <Select value={row.status} onValueChange={v => quickUpdateMutation.mutate({ id: row.id, status: v })}>
          <SelectTrigger className="h-7 text-xs border-slate-200 w-36 bg-white" onClick={e => e.stopPropagation()}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(TASK_STATUS_LABELS).map(([k, v]) => (
              <SelectItem key={k} value={k}>{v}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      ),
    },
    {
      key: 'assigned_to', header: 'Responsável',
      render: (row: Task) => row.assigned_to_name ? (
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center text-white text-[10px] font-semibold flex-shrink-0">
            {initials(row.assigned_to_name)}
          </div>
          <span className="text-xs text-slate-700">{row.assigned_to_name}</span>
        </div>
      ) : <span className="text-xs text-slate-400">—</span>,
    },
    {
      key: 'priority', header: 'Prioridade',
      render: (row: Task) => (
        <Badge variant="outline" className={cn(
          'text-[10px]',
          row.priority === 'critical' && 'border-red-300 text-red-600',
          row.priority === 'high' && 'border-amber-300 text-amber-600',
          row.priority === 'medium' && 'border-blue-300 text-blue-600',
        )}>
          {TASK_PRIORITY_LABELS[row.priority] ?? row.priority}
        </Badge>
      ),
    },
    {
      key: 'due_date', header: 'Prazo',
      render: (row: Task) => {
        if (!row.due_date) return <span className="text-xs text-slate-400">—</span>
        const isOverdue = new Date(row.due_date) < new Date() && row.status !== 'done'
        return (
          <span className={cn('text-xs', isOverdue ? 'text-red-600 font-medium' : 'text-slate-600')}>
            {formatDate(row.due_date)}
          </span>
        )
      },
    },
    {
      key: 'actions', header: '', width: 'w-16',
      render: (row: Task) => (
        <div className="flex gap-1">
          <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-slate-400"
            onClick={(e) => { e.stopPropagation(); setEditTarget(row); setShowForm(true) }}>✏️</Button>
          <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-400"
            onClick={(e) => { e.stopPropagation(); setDeleteTarget(row) }}>🗑️</Button>
        </div>
      ),
    },
  ]

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
        <div className="flex gap-3 mb-5 p-4 bg-slate-50 rounded-xl border border-slate-200">
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

// ── Task Form Modal ───────────────────────────────────────────────────────────
function TaskFormModal({ open, onOpenChange, task, onSaved }: {
  open: boolean; onOpenChange: (v: boolean) => void
  task: Task | null; onSaved: () => void
}) {
  const [form, setForm] = useState<CreateTaskData>({
    title: '', description: '', status: 'todo', priority: 'medium', due_date: null,
  })
  const [assignee, setAssignee] = useState<UserOption | null>(null)
  const [process, setProcess] = useState<ProcessOption | null>(null)
  const [assigneeError, setAssigneeError] = useState('')
  const set = (k: keyof CreateTaskData, v: any) => setForm(f => ({ ...f, [k]: v }))

  useEffect(() => {
    if (open) {
      if (task) {
        setForm({
          title: task.title, description: task.description ?? '',
          status: task.status, priority: task.priority,
          assigned_to: task.assigned_to, due_date: task.due_date,
        })
        setAssignee(task.assigned_to ? { id: task.assigned_to, name: task.assigned_to_name ?? '', email: '' } : null)
        setProcess((task as any).process ? { id: (task as any).process, title: (task as any).process_title ?? '' } : null)
      } else {
        setForm({ title: '', description: '', status: 'todo', priority: 'medium', due_date: null })
        setAssignee(null)
        setProcess(null)
      }
      setAssigneeError('')
    }
  }, [task, open])

  const validate = () => {
    if (!assignee) {
      setAssigneeError('Responsável é obrigatório.')
      return false
    }
    return true
  }

  const createMutation = useMutation({
    mutationFn: () => tasksApi.create({ ...form, assigned_to: assignee?.id, process: process?.id } as any),
    onSuccess: () => { toast.success('Tarefa criada.'); onSaved() },
    onError: () => toast.error('Erro ao criar tarefa.'),
  })
  const updateMutation = useMutation({
    mutationFn: () => tasksApi.update(task!.id, { ...form, assigned_to: assignee?.id, process: process?.id } as any),
    onSuccess: () => { toast.success('Tarefa atualizada.'); onSaved() },
    onError: () => toast.error('Erro ao atualizar.'),
  })
  const isPending = createMutation.isPending || updateMutation.isPending
  const isEdit = !!task

  const handleSubmit = () => {
    if (!validate()) return
    isEdit ? updateMutation.mutate() : createMutation.mutate()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-base">{isEdit ? 'Editar Tarefa' : 'Nova Tarefa'}</DialogTitle>
        </DialogHeader>
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

          {/* Assignee — REQUIRED */}
          <FormField label="Responsável *">
            <UserSelector
              value={assignee}
              onChange={u => { setAssignee(u); if (u) setAssigneeError('') }}
              error={assigneeError}
            />
          </FormField>

          {/* Process link — OPTIONAL */}
          <FormField label="Processo vinculado (opcional)">
            <ProcessSelector value={process} onChange={setProcess} />
          </FormField>

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
            onClick={handleSubmit}
          >
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
