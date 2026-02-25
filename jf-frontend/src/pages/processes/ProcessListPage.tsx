import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Plus, Search, SlidersHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PageHeader } from '@/components/layout/PageHeader'
import { DataTable } from '@/components/shared/DataTable'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { processesApi } from '@/api/processes'
import { formatDate, truncate } from '@/lib/utils'
import { PROCESS_STATUS_LABELS, PROCESS_PHASE_LABELS, PROCESS_AREA_LABELS } from '@/lib/constants'
import { useDebounce } from '@/hooks/useDebounce'
import { usePagination } from '@/hooks/usePagination'
import type { Process } from '@/types/process'

export function ProcessListPage() {
  const navigate = useNavigate()
  const { page, setPage, reset } = usePagination()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [phaseFilter, setPhaseFilter] = useState('')
  const [areaFilter, setAreaFilter] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  const debouncedSearch = useDebounce(search, 300)

  const { data, isLoading } = useQuery({
    queryKey: ['processes', { page, search: debouncedSearch, status: statusFilter, phase: phaseFilter, area: areaFilter }],
    queryFn: () =>
      processesApi.list({
        page,
        search: debouncedSearch || undefined,
        status: statusFilter || undefined,
        phase: phaseFilter || undefined,
        area: areaFilter || undefined,
      }),
    staleTime: 30_000,
  })

  const handleSearchChange = (v: string) => { setSearch(v); reset() }
  const handleFilter = (key: string, value: string) => {
    reset()
    if (key === 'status') setStatusFilter(value === 'all' ? '' : value)
    if (key === 'phase') setPhaseFilter(value === 'all' ? '' : value)
    if (key === 'area') setAreaFilter(value === 'all' ? '' : value)
  }

  const columns = [
    {
      key: 'number',
      header: 'Nº do Processo',
      render: (row: Process) => (
        <div>
          <p className="font-mono text-xs font-medium text-slate-900 leading-tight">{row.number}</p>
          {row.court && <p className="text-[11px] text-slate-400 mt-0.5 truncate max-w-[180px]">{row.court}</p>}
        </div>
      ),
    },
    {
      key: 'subject',
      header: 'Assunto',
      render: (row: Process) => (
        <div>
          <p className="text-sm text-slate-800 font-medium leading-tight">
            {truncate(row.subject, 48) || <span className="text-slate-400 font-normal italic">Sem assunto</span>}
          </p>
          {row.next_deadline && (
            <p className="text-[11px] text-amber-600 mt-0.5">
              ⏰ {row.next_deadline.title} — {formatDate(row.next_deadline.due_date)}
            </p>
          )}
        </div>
      ),
    },
    {
      key: 'area',
      header: 'Área',
      render: (row: Process) => <StatusBadge value={row.area} variant="process-area" />,
    },
    {
      key: 'phase',
      header: 'Fase',
      render: (row: Process) => <StatusBadge value={row.phase} variant="process-phase" />,
    },
    {
      key: 'status',
      header: 'Status',
      render: (row: Process) => <StatusBadge value={row.status} variant="process-status" />,
    },
    {
      key: 'risk',
      header: 'Risco',
      render: (row: Process) =>
        row.risk ? <StatusBadge value={row.risk} variant="risk" /> : <span className="text-slate-300">—</span>,
    },
    {
      key: 'responsible',
      header: 'Responsável',
      render: (row: Process) => <span className="text-xs text-slate-500">{row.responsible_name ?? '—'}</span>,
    },
    {
      key: 'deadlines',
      header: 'Prazos',
      render: (row: Process) => (
        <span className={`text-xs font-semibold ${row.deadlines_count > 0 ? 'text-blue-600' : 'text-slate-300'}`}>
          {row.deadlines_count}
        </span>
      ),
    },
  ]

  const hasFilters = !!(statusFilter || phaseFilter || areaFilter)

  return (
    <div className="max-w-7xl mx-auto page-enter">
      <PageHeader
        title="Processos"
        subtitle={data ? `${data.count} processo${data.count !== 1 ? 's' : ''} encontrado${data.count !== 1 ? 's' : ''}` : undefined}
        breadcrumbs={[{ label: 'JuridicFlow' }, { label: 'Processos' }]}
        actions={
          <Button onClick={() => navigate('/app/processos/novo')} className="bg-blue-600 hover:bg-blue-700 gap-2 h-9">
            <Plus size={15} /> Novo Processo
          </Button>
        }
      />

      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <div className="relative flex-1 max-w-md">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <Input
            placeholder="Buscar por número ou assunto…"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-9 h-9 bg-white border-slate-200 text-sm"
          />
        </div>
        <Button
          variant="outline" size="sm"
          onClick={() => setShowFilters(!showFilters)}
          className={`gap-2 h-9 ${hasFilters ? 'border-blue-300 text-blue-600 bg-blue-50' : ''}`}
        >
          <SlidersHorizontal size={14} />
          Filtros
          {hasFilters && (
            <span className="w-4 h-4 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center">
              {[statusFilter, phaseFilter, areaFilter].filter(Boolean).length}
            </span>
          )}
        </Button>
      </div>

      {showFilters && (
        <div className="flex flex-wrap gap-3 mb-5 p-4 bg-slate-50 rounded-xl border border-slate-200 animate-fade-in">
          {[
            { label: 'Status', key: 'status', value: statusFilter, options: PROCESS_STATUS_LABELS, width: 'w-36' },
            { label: 'Fase', key: 'phase', value: phaseFilter, options: PROCESS_PHASE_LABELS, width: 'w-40' },
            { label: 'Área', key: 'area', value: areaFilter, options: PROCESS_AREA_LABELS, width: 'w-44' },
          ].map(({ label, key, value, options, width }) => (
            <div key={key} className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-slate-500">{label}</label>
              <Select value={value || 'all'} onValueChange={(v) => handleFilter(key, v)}>
                <SelectTrigger className={`h-9 ${width} bg-white text-sm border-slate-200`}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  {Object.entries(options).map(([k, v]) => (
                    <SelectItem key={k} value={k}>{v}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ))}
          {hasFilters && (
            <div className="flex items-end">
              <Button
                variant="ghost" size="sm" className="h-9 text-slate-500 text-xs"
                onClick={() => { setStatusFilter(''); setPhaseFilter(''); setAreaFilter(''); reset() }}
              >
                Limpar filtros
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
        onRowClick={(row) => navigate(`/app/processos/${row.id}`)}
        emptyTitle="Nenhum processo encontrado"
        emptyDescription={
          hasFilters || search
            ? 'Tente ajustar os filtros ou termos de busca.'
            : 'Clique em "Novo Processo" para cadastrar o primeiro processo.'
        }
        emptyAction={
          !hasFilters && !search ? (
            <Button size="sm" className="bg-blue-600 hover:bg-blue-700 gap-2" onClick={() => navigate('/app/processos/novo')}>
              <Plus size={14} /> Novo Processo
            </Button>
          ) : undefined
        }
      />
    </div>
  )
}
