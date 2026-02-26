import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, List, Kanban } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/layout/PageHeader'
import { customersApi } from '@/api/customers'
import { formatCurrency, initials, truncate } from '@/lib/utils'
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
  // Track dragenter/dragleave depth to prevent flickering on child elements
  const dragCounters = useRef<Record<string, number>>({})

  const { data, isLoading } = useQuery({
    queryKey: ['customers-pipeline'],
    queryFn: () => customersApi.list({ page: 1, page_size: 200 }),
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

  const grouped = STAGES.reduce<Record<string, Customer[]>>((acc, s) => {
    acc[s.key] = customers.filter((c) => c.pipeline_stage === s.key)
    return acc
  }, {})
  const noStage = customers.filter((c) => !c.pipeline_stage)
  if (noStage.length > 0) grouped['novo'] = [...(grouped['novo'] ?? []), ...noStage]

  const totalEstimated = customers
    .filter((c) => c.estimated_value && c.pipeline_stage !== 'perdido')
    .reduce((sum, c) => sum + parseFloat(c.estimated_value ?? '0'), 0)

  // ── Drag handlers using counter technique to avoid child flicker ─────────
  const handleDragEnter = (stage: string, e: React.DragEvent) => {
    e.preventDefault()
    dragCounters.current[stage] = (dragCounters.current[stage] ?? 0) + 1
    setOverStage(stage)
  }

  const handleDragLeave = (stage: string) => {
    dragCounters.current[stage] = (dragCounters.current[stage] ?? 1) - 1
    if (dragCounters.current[stage] <= 0) {
      dragCounters.current[stage] = 0
      setOverStage(null)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  const handleDrop = (stage: string, e: React.DragEvent) => {
    e.preventDefault()
    dragCounters.current[stage] = 0
    setOverStage(null)
    if (draggingId !== null) {
      const customer = customers.find(c => c.id === draggingId)
      if (customer && customer.pipeline_stage !== stage) {
        updateMutation.mutate({ id: draggingId, stage })
      }
    }
    setDraggingId(null)
  }

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
            <Button size="sm" onClick={() => navigate('/app/contatos/novo')} className="gap-2 h-9">
              <Plus size={14} /> Novo Contato
            </Button>
          </div>
        }
      />

      <div className="overflow-x-auto pb-4">
        <div className="flex gap-4 min-w-max p-1">
          {STAGES.map((stage) => {
            const cards = grouped[stage.key] ?? []
            const stageValue = cards
              .filter(c => c.estimated_value)
              .reduce((sum, c) => sum + parseFloat(c.estimated_value ?? '0'), 0)

            return (
              <div
                key={stage.key}
                className={cn(
                  'flex-shrink-0 w-64 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col transition-all duration-150',
                  overStage === stage.key && draggingId !== null && 'bg-blue-50 border-blue-300 ring-2 ring-blue-200',
                )}
                onDragEnter={(e) => handleDragEnter(stage.key, e)}
                onDragLeave={() => handleDragLeave(stage.key)}
                onDragOver={handleDragOver}
                onDrop={(e) => handleDrop(stage.key, e)}
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
                      onDragStart={(e) => {
                        setDraggingId(customer.id)
                        e.dataTransfer.effectAllowed = 'move'
                        e.dataTransfer.setData('text/plain', String(customer.id))
                      }}
                      onDragEnd={() => {
                        setDraggingId(null)
                        setOverStage(null)
                        // Reset all counters
                        dragCounters.current = {}
                      }}
                      onClick={() => navigate(`/app/contatos/${customer.id}`)}
                      className={cn(
                        'bg-white rounded-lg border border-slate-200 p-3 cursor-grab select-none',
                        'hover:shadow-md hover:border-slate-300 transition-all duration-150',
                        'active:cursor-grabbing',
                        draggingId === customer.id && 'opacity-40 scale-95 shadow-lg',
                      )}
                    >
                      <div className="flex items-start gap-2 mb-2">
                        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-[10px] font-bold flex-shrink-0">
                          {initials(customer.name)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold text-slate-800 truncate">{customer.name}</p>
                          {customer.email && (
                            <p className="text-[10px] text-slate-400 truncate">{customer.email}</p>
                          )}
                        </div>
                      </div>
                      {customer.estimated_value && parseFloat(customer.estimated_value) > 0 && (
                        <div className="mt-1.5 pt-1.5 border-t border-slate-100">
                          <p className="text-[10px] text-emerald-600 font-semibold">
                            {formatCurrency(customer.estimated_value)}
                          </p>
                        </div>
                      )}
                    </div>
                  ))}

                  {cards.length === 0 && (
                    <div className={cn(
                      'flex-1 rounded-lg border-2 border-dashed flex items-center justify-center min-h-[60px] transition-colors',
                      overStage === stage.key && draggingId !== null
                        ? 'border-blue-300 bg-blue-50/50'
                        : 'border-slate-200/70',
                    )}>
                      <p className="text-[10px] text-slate-400">Solte aqui</p>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function PipelineSkeleton() {
  return (
    <div className="page-enter">
      <div className="flex gap-4 overflow-x-auto pb-4">
        {STAGES.map(s => (
          <div key={s.key} className="flex-shrink-0 w-64 h-64 rounded-xl bg-slate-100 animate-pulse" />
        ))}
      </div>
    </div>
  )
}
