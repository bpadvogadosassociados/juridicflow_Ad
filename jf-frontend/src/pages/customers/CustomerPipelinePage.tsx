import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Plus, Search, SlidersHorizontal, Users, LayoutKanban } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PageHeader } from '@/components/layout/PageHeader'
import { DataTable } from '@/components/shared/DataTable'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { customersApi } from '@/api/customers'
import { formatDocument, formatDate, truncate, initials } from '@/lib/utils'
import { CUSTOMER_STATUS_LABELS, PIPELINE_STAGE_LABELS } from '@/lib/constants'
import { useDebounce } from '@/hooks/useDebounce'
import { usePagination } from '@/hooks/usePagination'
import { cn } from '@/lib/utils'
import type { Customer } from '@/types/customer'

const TYPE_LABELS: Record<string, string> = { PF: 'Pessoa Física', PJ: 'Pessoa Jurídica' }

export function CustomerListPage() {
  const navigate = useNavigate()
  const { page, setPage, reset } = usePagination()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  const debouncedSearch = useDebounce(search, 300)

  const { data, isLoading } = useQuery({
    queryKey: ['customers', { page, search: debouncedSearch, status: statusFilter, type: typeFilter }],
    queryFn: () =>
      customersApi.list({
        page,
        search: debouncedSearch || undefined,
        status: statusFilter || undefined,
        type: typeFilter || undefined,
      }),
    staleTime: 30_000,
  })

  const hasFilters = !!(statusFilter || typeFilter)

  const columns = [
    {
      key: 'name',
      header: 'Contato',
      render: (row: Customer) => (
        <div className="flex items-center gap-3">
          <div className={cn(
            'w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0',
            row.type === 'PJ' ? 'bg-violet-100 text-violet-600' : 'bg-blue-100 text-blue-600',
          )}>
            {initials(row.name)}
          </div>
          <div>
            <p className="text-sm font-medium text-slate-900">{row.name}</p>
            {row.email && <p className="text-[11px] text-slate-400">{row.email}</p>}
          </div>
        </div>
      ),
    },
    {
      key: 'type',
      header: 'Tipo',
      render: (row: Customer) => (
        <span className={cn(
          'text-xs px-2 py-0.5 rounded-md font-medium',
          row.type === 'PJ' ? 'bg-violet-50 text-violet-700' : 'bg-blue-50 text-blue-700',
        )}>
          {TYPE_LABELS[row.type] ?? row.type}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row: Customer) => <StatusBadge value={row.status} variant="customer-status" />,
    },
    {
      key: 'pipeline',
      header: 'Pipeline',
      render: (row: Customer) =>
        row.pipeline_stage
          ? <span className="text-xs text-slate-600 bg-slate-100 px-2 py-0.5 rounded-md">{PIPELINE_STAGE_LABELS[row.pipeline_stage] ?? row.pipeline_stage}</span>
          : <span className="text-slate-300 text-xs">—</span>,
    },
    {
      key: 'document',
      header: 'CPF/CNPJ',
      render: (row: Customer) => (
        <span className="text-xs font-mono text-slate-500">{formatDocument(row.document)}</span>
      ),
    },
    {
      key: 'phone',
      header: 'Telefone',
      render: (row: Customer) => <span className="text-xs text-slate-500">{row.phone || '—'}</span>,
    },
    {
      key: 'responsible',
      header: 'Responsável',
      render: (row: Customer) => <span className="text-xs text-slate-500">{row.responsible_name ?? '—'}</span>,
    },
    {
      key: 'last_contact',
      header: 'Últ. Contato',
      render: (row: Customer) => (
        <span className="text-xs text-slate-400">{formatDate(row.last_interaction_date)}</span>
      ),
    },
  ]

  return (
    <div className="max-w-7xl mx-auto page-enter">
      <PageHeader
        title="Contatos"
        subtitle={data ? `${data.count} contato${data.count !== 1 ? 's' : ''}` : undefined}
        breadcrumbs={[{ label: 'JuridicFlow' }, { label: 'Contatos' }]}
        actions={
          <div className="flex gap-2">
            <Button
              variant="outline" size="sm"
              onClick={() => navigate('/app/contatos/pipeline')}
              className="gap-2 h-9"
            >
              <LayoutKanban size={14} /> Pipeline
            </Button>
            <Button
              onClick={() => navigate('/app/contatos/novo')}
              className="bg-blue-600 hover:bg-blue-700 gap-2 h-9"
            >
              <Plus size={15} /> Novo Contato
            </Button>
          </div>
        }
      />

      <div className="flex gap-3 mb-5">
        <div className="relative flex-1 max-w-md">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <Input
            placeholder="Buscar por nome, e-mail ou documento…"
            value={search}
            onChange={(e) => { setSearch(e.target.value); reset() }}
            className="pl-9 h-9 bg-white border-slate-200 text-sm"
          />
        </div>
        <Button
          variant="outline" size="sm"
          onClick={() => setShowFilters(!showFilters)}
          className={`gap-2 h-9 ${hasFilters ? 'border-blue-300 text-blue-600 bg-blue-50' : ''}`}
        >
          <SlidersHorizontal size={14} /> Filtros
          {hasFilters && (
            <span className="w-4 h-4 rounded-full bg-blue-600 text-white text-[10px] font-bold flex items-center justify-center">
              {[statusFilter, typeFilter].filter(Boolean).length}
            </span>
          )}
        </Button>
      </div>

      {showFilters && (
        <div className="flex flex-wrap gap-3 mb-5 p-4 bg-slate-50 rounded-xl border border-slate-200 animate-fade-in">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-500">Status</label>
            <Select value={statusFilter || 'all'} onValueChange={(v) => { setStatusFilter(v === 'all' ? '' : v); reset() }}>
              <SelectTrigger className="h-9 w-36 bg-white text-sm border-slate-200"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                {Object.entries(CUSTOMER_STATUS_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-500">Tipo</label>
            <Select value={typeFilter || 'all'} onValueChange={(v) => { setTypeFilter(v === 'all' ? '' : v); reset() }}>
              <SelectTrigger className="h-9 w-36 bg-white text-sm border-slate-200"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                {Object.entries(TYPE_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          {hasFilters && (
            <div className="flex items-end">
              <Button variant="ghost" size="sm" className="h-9 text-xs text-slate-500"
                onClick={() => { setStatusFilter(''); setTypeFilter(''); reset() }}>
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
        onRowClick={(row) => navigate(`/app/contatos/${row.id}`)}
        emptyTitle="Nenhum contato encontrado"
        emptyDescription={
          hasFilters || search
            ? 'Tente ajustar os filtros.'
            : 'Clique em "Novo Contato" para cadastrar o primeiro cliente.'
        }
        emptyAction={
          !hasFilters && !search ? (
            <Button size="sm" className="bg-blue-600 hover:bg-blue-700 gap-2" onClick={() => navigate('/app/contatos/novo')}>
              <Plus size={14} /> Novo Contato
            </Button>
          ) : undefined
        }
      />
    </div>
  )
}
