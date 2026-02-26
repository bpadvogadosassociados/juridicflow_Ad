import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import {
  Search, Download, Filter, ChevronDown, ChevronRight,
  Activity, User, FileText, DollarSign, CheckSquare,
  Calendar, Users, Settings, Shield, LayoutGrid,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { PageHeader } from '@/components/layout/PageHeader'
import { activityApi, type ActivityEvent } from '@/api/activity'
import { cn } from '@/lib/utils'
import { useDebounce } from '@/hooks/useDebounce'
import { usePagination } from '@/hooks/usePagination'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

// ── Module icon map ──────────────────────────────────────────────────────────

const MODULE_ICONS: Record<string, React.ReactNode> = {
  processes: <FileText size={14} />,
  deadlines: <Calendar size={14} />,
  customers: <Users size={14} />,
  documents: <FileText size={14} />,
  finance:   <DollarSign size={14} />,
  tasks:     <CheckSquare size={14} />,
  kanban:    <LayoutGrid size={14} />,
  calendar:  <Calendar size={14} />,
  team:      <Users size={14} />,
  auth:      <Shield size={14} />,
  settings:  <Settings size={14} />,
  system:    <Activity size={14} />,
}

const MODULE_COLORS: Record<string, string> = {
  processes: 'bg-blue-100 text-blue-700',
  deadlines: 'bg-amber-100 text-amber-700',
  customers: 'bg-violet-100 text-violet-700',
  documents: 'bg-slate-100 text-slate-700',
  finance:   'bg-emerald-100 text-emerald-700',
  tasks:     'bg-orange-100 text-orange-700',
  kanban:    'bg-cyan-100 text-cyan-700',
  calendar:  'bg-pink-100 text-pink-700',
  team:      'bg-indigo-100 text-indigo-700',
  auth:      'bg-red-100 text-red-700',
  settings:  'bg-gray-100 text-gray-700',
  system:    'bg-gray-100 text-gray-700',
}

const ACTION_COLORS: Record<string, string> = {
  created:    'bg-emerald-50 text-emerald-700 border-emerald-200',
  updated:    'bg-blue-50 text-blue-700 border-blue-200',
  deleted:    'bg-red-50 text-red-700 border-red-200',
  completed:  'bg-teal-50 text-teal-700 border-teal-200',
  uploaded:   'bg-indigo-50 text-indigo-700 border-indigo-200',
  login:      'bg-slate-50 text-slate-600 border-slate-200',
  exported:   'bg-orange-50 text-orange-700 border-orange-200',
  status_changed: 'bg-purple-50 text-purple-700 border-purple-200',
  member_added: 'bg-green-50 text-green-700 border-green-200',
  member_removed: 'bg-red-50 text-red-700 border-red-200',
}

const PERIOD_OPTIONS = [
  { value: '1d',  label: 'Hoje' },
  { value: '7d',  label: 'Últimos 7 dias' },
  { value: '30d', label: 'Últimos 30 dias' },
  { value: '90d', label: 'Últimos 90 dias' },
]

const MODULE_OPTIONS = [
  { value: '',          label: 'Todos os módulos' },
  { value: 'processes', label: 'Processos' },
  { value: 'deadlines', label: 'Prazos' },
  { value: 'customers', label: 'Contatos' },
  { value: 'documents', label: 'Documentos' },
  { value: 'finance',   label: 'Financeiro' },
  { value: 'tasks',     label: 'Tarefas' },
  { value: 'calendar',  label: 'Agenda' },
  { value: 'team',      label: 'Equipe' },
  { value: 'auth',      label: 'Autenticação' },
  { value: 'settings',  label: 'Configurações' },
]

const ACTION_OPTIONS = [
  { value: '',             label: 'Todas as ações' },
  { value: 'created',      label: 'Criou' },
  { value: 'updated',      label: 'Atualizou' },
  { value: 'deleted',      label: 'Excluiu' },
  { value: 'completed',    label: 'Concluiu' },
  { value: 'uploaded',     label: 'Upload' },
  { value: 'exported',     label: 'Exportou' },
  { value: 'status_changed','label': 'Mudou status' },
  { value: 'login',        label: 'Login' },
  { value: 'member_added', label: 'Adicionou membro' },
  { value: 'member_removed','label':'Removeu membro' },
]

// ── EventRow component ────────────────────────────────────────────────────────

function EventRow({ event }: { event: ActivityEvent }) {
  const [expanded, setExpanded] = useState(false)
  const hasChanges = Object.keys(event.changes ?? {}).length > 0

  const date = new Date(event.created_at)
  const timeStr = date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  const dateStr = date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })

  return (
    <div className={cn(
      'border-b border-slate-100 last:border-0 transition-colors',
      expanded ? 'bg-slate-50' : 'hover:bg-slate-50/50',
    )}>
      <div
        className="flex items-start gap-3 px-4 py-3 cursor-pointer select-none"
        onClick={() => hasChanges && setExpanded(p => !p)}
      >
        {/* Module icon */}
        <div className={cn(
          'w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5',
          MODULE_COLORS[event.module] ?? 'bg-gray-100 text-gray-700',
        )}>
          {MODULE_ICONS[event.module] ?? <Activity size={14} />}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <p className="text-sm text-slate-800">{event.summary}</p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="text-xs text-slate-400">{dateStr} {timeStr}</span>
            {event.ip_address && (
              <span className="text-xs text-slate-300">· {event.ip_address}</span>
            )}
          </div>
        </div>

        {/* Badges */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className={cn(
            'text-[10px] font-semibold px-1.5 py-0.5 rounded border',
            ACTION_COLORS[event.action] ?? 'bg-gray-50 text-gray-600 border-gray-200',
          )}>
            {event.action_display}
          </span>

          {hasChanges && (
            <button className="text-slate-400 hover:text-slate-600 transition-colors">
              {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </button>
          )}
        </div>
      </div>

      {/* Diff viewer */}
      {expanded && hasChanges && (
        <div className="mx-4 mb-3 rounded-lg border border-slate-200 overflow-hidden text-xs">
          <div className="bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600 border-b border-slate-200">
            Alterações
          </div>
          <div className="divide-y divide-slate-100">
            {Object.entries(event.changes).map(([field, diff]) => (
              <div key={field} className="grid grid-cols-3 px-3 py-2 gap-2">
                <span className="text-slate-500 font-medium">{field}</span>
                <span className="text-red-600 line-through truncate">{String(diff.before ?? '—')}</span>
                <span className="text-emerald-600 truncate">{String(diff.after ?? '—')}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Day group ─────────────────────────────────────────────────────────────────

function groupByDay(events: ActivityEvent[]) {
  const groups: { label: string; events: ActivityEvent[] }[] = []
  const map = new Map<string, ActivityEvent[]>()
  const today = new Date().toDateString()
  const yesterday = new Date(Date.now() - 86400000).toDateString()

  for (const e of events) {
    const d = new Date(e.created_at)
    const key = d.toDateString()
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(e)
  }

  map.forEach((evts, key) => {
    let label = new Date(key).toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'long' })
    if (key === today) label = 'Hoje'
    else if (key === yesterday) label = 'Ontem'
    groups.push({ label, events: evts })
  })
  return groups
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export function ReportsDashboardPage() {
  const [searchParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [period, setPeriod] = useState('7d')
  const [module, setModule] = useState('')
  const [action, setAction] = useState('')
  const { page, setPage } = usePagination()
  const debouncedSearch = useDebounce(search, 300)

  const queryParams = {
    period,
    module: module || undefined,
    action: action || undefined,
    search: debouncedSearch || undefined,
    page,
    page_size: 50,
  }

  const { data, isLoading } = useQuery({
    queryKey: ['activity', queryParams],
    queryFn: () => activityApi.list(queryParams),
    staleTime: 15_000,
  })

  const { data: summary } = useQuery({
    queryKey: ['activity-summary', period],
    queryFn: () => activityApi.summary(period),
    staleTime: 60_000,
  })

  const events = data?.results ?? []
  const groups = groupByDay(events)
  const totalPages = data ? Math.ceil(data.count / 50) : 1

  const handleExport = () => {
    activityApi.exportCsv({ period, module, action })
  }

  return (
    <div className="page-enter">
      <PageHeader
        title="Atividade"
        subtitle="Trilha de auditoria — registro completo de todas as ações"
        breadcrumbs={[{ label: 'Atividade' }]}
        actions={
          <Button variant="outline" size="sm" onClick={handleExport} className="gap-2 h-9">
            <Download size={14} /> Exportar CSV
          </Button>
        }
      />

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <p className="text-xs text-slate-500 mb-1">Total de eventos</p>
            <p className="text-2xl font-bold text-slate-800">{summary.total.toLocaleString()}</p>
            <p className="text-xs text-slate-400 mt-1">{PERIOD_OPTIONS.find(p => p.value === period)?.label}</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <p className="text-xs text-slate-500 mb-1">Tarefas criadas / concluídas</p>
            <p className="text-2xl font-bold text-slate-800">
              {summary.tasks.created} <span className="text-sm font-normal text-slate-400">/ {summary.tasks.completed}</span>
            </p>
            <div className="mt-2 h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-500 rounded-full"
                style={{ width: summary.tasks.created > 0 ? `${Math.round((summary.tasks.completed / summary.tasks.created) * 100)}%` : '0%' }}
              />
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <p className="text-xs text-slate-500 mb-1">Módulo mais ativo</p>
            <p className="text-lg font-bold text-slate-800 truncate">
              {summary.by_module[0] ? MODULE_OPTIONS.find(m => m.value === summary.by_module[0].module)?.label ?? summary.by_module[0].module : '—'}
            </p>
            <p className="text-xs text-slate-400 mt-1">{summary.by_module[0]?.count ?? 0} eventos</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <p className="text-xs text-slate-500 mb-1">Membro mais ativo</p>
            <p className="text-lg font-bold text-slate-800 truncate">{summary.top_actors[0]?.name ?? '—'}</p>
            <p className="text-xs text-slate-400 mt-1">{summary.top_actors[0]?.count ?? 0} ações</p>
          </div>
        </div>
      )}

      {/* Daily chart */}
      {summary && summary.daily.length > 1 && (
        <div className="bg-white rounded-xl border border-slate-200 p-4 mb-6">
          <p className="text-xs font-semibold text-slate-500 mb-3 uppercase tracking-wide">Atividade diária</p>
          <ResponsiveContainer width="100%" height={120}>
            <BarChart data={summary.daily} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={d => d.slice(5)} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip
                contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }}
                formatter={(v) => [v, 'Eventos']}
              />
              <Bar dataKey="count" fill="#3b82f6" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <Input
            placeholder="Buscar no log..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }}
            className="pl-9 h-9"
          />
        </div>
        <Select value={period} onValueChange={v => { setPeriod(v); setPage(1) }}>
          <SelectTrigger className="w-44 h-9">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PERIOD_OPTIONS.map(o => (
              <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={module} onValueChange={v => { setModule(v); setPage(1) }}>
          <SelectTrigger className="w-44 h-9">
            <SelectValue placeholder="Módulo" />
          </SelectTrigger>
          <SelectContent>
            {MODULE_OPTIONS.map(o => (
              <SelectItem key={o.value} value={o.value || '_all'}>{o.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={action} onValueChange={v => { setAction(v); setPage(1) }}>
          <SelectTrigger className="w-40 h-9">
            <SelectValue placeholder="Ação" />
          </SelectTrigger>
          <SelectContent>
            {ACTION_OPTIONS.map(o => (
              <SelectItem key={o.value} value={o.value || '_all'}>{o.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Active filters */}
      {(module || action) && (
        <div className="flex gap-2 mb-3">
          {module && (
            <button
              onClick={() => setModule('')}
              className="flex items-center gap-1 px-2 py-1 rounded-full bg-blue-50 border border-blue-200 text-xs text-blue-700 hover:bg-blue-100"
            >
              {MODULE_OPTIONS.find(m => m.value === module)?.label}
              <X size={10} />
            </button>
          )}
          {action && (
            <button
              onClick={() => setAction('')}
              className="flex items-center gap-1 px-2 py-1 rounded-full bg-slate-100 border border-slate-200 text-xs text-slate-700 hover:bg-slate-200"
            >
              {ACTION_OPTIONS.find(a => a.value === action)?.label}
              <X size={10} />
            </button>
          )}
        </div>
      )}

      {/* Event list */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-slate-400 text-sm">Carregando...</div>
        ) : events.length === 0 ? (
          <div className="p-12 text-center">
            <Activity size={32} className="mx-auto text-slate-300 mb-3" />
            <p className="text-slate-500 text-sm">Nenhum evento encontrado</p>
            <p className="text-slate-400 text-xs mt-1">Tente ajustar os filtros</p>
          </div>
        ) : (
          <>
            {groups.map(group => (
              <div key={group.label}>
                <div className="px-4 py-2 bg-slate-50 border-b border-slate-100 sticky top-0 z-10">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{group.label}</p>
                </div>
                {group.events.map(event => (
                  <EventRow key={event.id} event={event} />
                ))}
              </div>
            ))}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100">
                <p className="text-xs text-slate-400">
                  {data?.count.toLocaleString()} eventos · Página {page} de {totalPages}
                </p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
                    Anterior
                  </Button>
                  <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
                    Próxima
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
