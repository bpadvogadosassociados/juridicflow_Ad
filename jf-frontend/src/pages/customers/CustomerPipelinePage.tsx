import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, List, Kanban } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/layout/PageHeader'
import { customersApi } from '@/api/customers'
import { formatCurrency, initials, truncate } from '@/lib/utils'
import { PIPELINE_STAGE_LABELS } from '@/lib/constants'
import { cn } from '@/lib/utils'
import type { Customer } from '@/types/customer'

const STAGES = [
  { key: 'novo',             label: 'Novo',              color: 'bg-slate-400' },
  { key: 'contato_feito',    label: 'Contato Feito',     color: 'bg-blue-400' },
  { key: 'reuniao_marcada',  label: 'Reunião Marcada',   color: 'bg-violet-400' },
  { key: 'proposta_enviada', label: 'Proposta Enviada',  color: 'bg-amber-400' },
  { key: 'em_negociacao',    label: 'Em Negociação',     color: 'bg-orange-400' },
  { key: 'ganho',            label: 'Ganho',             color: 'bg-emerald-500' },
  { key: 'perdido',          label: 'Perdido',           color: 'bg-red-400' },
]

export function CustomerPipelinePage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [draggingId, setDraggingId] = useState<number | null>(null)
  const [overStage, setOverStage] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['customers-pipeline'],
    queryFn: () => customersApi.list({ page: 1 }),
    staleTime: 30_000,
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, stage }: { id: number; stage: string }) =>
      customersApi.update(id, { pipeline_stage: stage }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customers-pipeline'] })
      queryClient.invalidateQueries({ queryKey: ['customers'] })
    },
    onError: () => toast.error('Erro ao mover card.'),
  })

  const customers = data?.results ?? []

  // Group by pipeline_stage
  const grouped = STAGES.reduce<Record<string, Customer[]>>((acc, s) => {
    acc[s.key] = customers.filter((c) => c.pipeline_stage === s.key)
    return acc
  }, {})
  // Customers without a stage go to 'novo'
  const noStage = customers.filter((c) => !c.pipeline_stage)
  if (noStage.length > 0) grouped['novo'] = [...(grouped['novo'] ?? []), ...noStage]

  const handleDrop = (stage: string) => {
    if (draggingId !== null && stage !== overStage) {
      updateMutation.mutate({ id: draggingId, stage })
    }
    setDraggingId(null)
    setOverStage(null)
  }

  const totalEstimated = customers
    .filter((c) => c.estimated_value && c.pipeline_stage !== 'perdido')
    .reduce((sum, c) => sum + parseFloat(c.estimated_value ?? '0'), 0)

  if (isLoading) return <PipelineSkeleton />

  return (
    <div className="page-enter">
      <PageHeader
        title="Pipeline"
        subtitle={`${customers.length} contato${customers.length !== 1 ? 's' : ''} · ${formatCurrency(totalEstimated)} em aberto`}
        breadcrumbs={[{ label: 'Contatos', href: '/app/contatos' }, { label: 'Pipeline' }]}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => navigate('/app/contatos')} className="gap-2 h-9">
              <List size={14} /> Lista
            </Button>
            <Button onClick={() => navigate('/app/contatos/novo')} className="bg-blue-600 hover:bg-blue-700 gap-2 h-9">
              <Plus size={15} /> Novo Contato
            </Button>
          </div>
        }
      />

      {/* Board */}
      <div className="flex gap-4 overflow-x-auto pb-4 -mx-1 px-1">
        {STAGES.map((stage) => {
          const cards = grouped[stage.key] ?? []
          const stageValue = cards
            .filter((c) => c.estimated_value)
            .reduce((s, c) => s + parseFloat(c.estimated_value ?? '0'), 0)

          return (
            <div
              key={stage.key}
              className={cn(
                'flex-shrink-0 w-64 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col transition-all duration-150',
                overStage === stage.key && 'bg-blue-50 border-blue-300 ring-2 ring-blue-200',
              )}
              onDragOver={(e) => { e.preventDefault(); setOverStage(stage.key) }}
              onDragLeave={() => setOverStage(null)}
              onDrop={() => handleDrop(stage.key)}
            >
              {/* Column header */}
              <div className="p-3 border-b border-slate-200/70">
                <div className="flex items-center gap-2 mb-1">
                  <div className={cn('w-2 h-2 rounded-full flex-shrink-0', stage.color)} />
                  <span className="text-xs font-semibold text-slate-700">{stage.label}</span>
                  <span className="ml-auto text-xs text-slate-400 font-medium">{cards.length}</span>
                </div>
                {stageValue > 0 && (
                  <p className="text-[10px] text-slate-400 pl-4">{formatCurrency(stageValue)}</p>
                )}
              </div>

              {/* Cards */}
              <div className="p-2 flex flex-col gap-2 flex-1 min-h-[120px]">
                {cards.map((customer) => (
                  <div
                    key={customer.id}
                    draggable
                    onDragStart={() => setDraggingId(customer.id)}
                    onDragEnd={() => { setDraggingId(null); setOverStage(null) }}
                    onClick={() => navigate(`/app/contatos/${customer.id}`)}
                    className={cn(
                      'bg-white rounded-lg border border-slate-200 p-3 cursor-pointer',
                      'hover:shadow-md hover:border-slate-300 transition-all duration-150',
                      'active:opacity-60',
                      draggingId === customer.id && 'opacity-40 scale-95',
                    )}
                  >
                    <div className="flex items-start gap-2 mb-2">
                      <div className={cn(
                        'w-7 h-7 rounded-md flex items-center justify-center text-[10px] font-bold flex-shrink-0',
                        customer.type === 'PJ' ? 'bg-violet-100 text-violet-600' : 'bg-blue-100 text-blue-600',
                      )}>
                        {initials(customer.name)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-slate-900 leading-tight truncate">{customer.name}</p>
                        {customer.email && (
                          <p className="text-[10px] text-slate-400 truncate mt-0.5">{customer.email}</p>
                        )}
                      </div>
                    </div>

                    {customer.next_action && (
                      <p className="text-[10px] text-slate-500 bg-slate-50 rounded px-1.5 py-1 border border-slate-100 leading-tight">
                        → {truncate(customer.next_action, 60)}
                      </p>
                    )}

                    {customer.estimated_value && parseFloat(customer.estimated_value) > 0 && (
                      <p className="text-[10px] font-semibold text-emerald-600 mt-1.5">
                        {formatCurrency(customer.estimated_value)}
                      </p>
                    )}
                  </div>
                ))}

                {cards.length === 0 && (
                  <div className="flex items-center justify-center h-16 text-[11px] text-slate-300 border border-dashed border-slate-200 rounded-lg">
                    Arraste aqui
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function PipelineSkeleton() {
  return (
    <div className="page-enter">
      <div className="h-8 w-48 bg-slate-100 rounded animate-pulse mb-6" />
      <div className="flex gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex-shrink-0 w-64 h-64 bg-slate-100 rounded-xl animate-pulse" />
        ))}
      </div>
    </div>
  )
}
