import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Activity, Bell, BellOff, Search, Plus, RefreshCw, Radio,
  Filter, ChevronDown, ChevronUp, ExternalLink, AlertTriangle,
  Clock, CheckCircle2, Archive, Zap, Eye, Database, Settings2,
  Calendar, Building, Users, FileText, ToggleLeft, ToggleRight,
  Trash2, X, BookOpen, Layers,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  publicationsApi,
  type JudicialEvent,
  type ProcessMonitoring,
  type PublicationImport,
  type DataJudResult,
  type PublicationRule,
  type PublicationFilter,
} from '@/api/publications'
import { useDebounce } from '@/hooks/useDebounce'
import { formatDate } from '@/lib/utils'

// ─── Helpers ──────────────────────────────────────────────────────────────────

const SOURCE_LABELS: Record<string, string> = {
  datajud: 'DataJud', comunica: 'Comunica/PJe', djen: 'DJEN',
  tjsp: 'TJSP', tjrj: 'TJRJ', trf1: 'TRF1', trf2: 'TRF2',
  trf3: 'TRF3', trf4: 'TRF4', trf5: 'TRF5', manual: 'Manual', other: 'Outro',
}

const SOURCE_COLORS: Record<string, string> = {
  datajud: 'bg-blue-100 text-blue-800',
  comunica: 'bg-purple-100 text-purple-800',
  djen: 'bg-orange-100 text-orange-800',
  manual: 'bg-gray-100 text-gray-700',
}

const URGENCY_CONFIG = {
  critical: { label: 'Crítica', color: 'bg-red-100 text-red-800 border-red-200', dot: 'bg-red-500', icon: AlertTriangle },
  urgent:   { label: 'Urgente', color: 'bg-amber-100 text-amber-800 border-amber-200', dot: 'bg-amber-500', icon: Clock },
  normal:   { label: 'Normal', color: 'bg-green-100 text-green-800 border-green-200', dot: 'bg-green-500', icon: CheckCircle2 },
}

const STATUS_CONFIG = {
  new:         { label: 'Nova', color: 'bg-blue-100 text-blue-800' },
  assigned:    { label: 'Atribuída', color: 'bg-indigo-100 text-indigo-800' },
  in_progress: { label: 'Em andamento', color: 'bg-amber-100 text-amber-800' },
  resolved:    { label: 'Resolvida', color: 'bg-green-100 text-green-800' },
  archived:    { label: 'Arquivada', color: 'bg-gray-100 text-gray-600' },
}

const EVENT_TYPE_LABELS: Record<string, string> = {
  citacao: 'Citação', intimacao: 'Intimação', sentenca: 'Sentença',
  acordao: 'Acórdão', decisao: 'Decisão', despacho: 'Despacho',
  juntada: 'Juntada', audiencia: 'Audiência', peticao: 'Petição',
  edital: 'Edital', movimento: 'Movimento', other: 'Outro',
}

function groupByDate(events: JudicialEvent[]) {
  const groups: Record<string, JudicialEvent[]> = {}
  for (const ev of events) {
    const d = ev.publication_date || ev.created_at?.slice(0, 10)
    if (!groups[d]) groups[d] = []
    groups[d].push(ev)
  }
  return groups
}

function formatGroupDate(dateStr: string) {
  const d = new Date(dateStr + 'T12:00:00')
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  if (d.toDateString() === today.toDateString()) return 'Hoje'
  if (d.toDateString() === yesterday.toDateString()) return 'Ontem'
  return d.toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, color, icon: Icon }: {
  label: string; value: number | string; sub?: string; color: string; icon: any
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-start gap-4">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${color}`}>
        <Icon size={18} />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900 leading-none">{value}</p>
        <p className="text-sm text-gray-600 mt-0.5">{label}</p>
        {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
      </div>
    </div>
  )
}

// ─── Event Card ───────────────────────────────────────────────────────────────

function EventCard({ event, onUpdate }: { event: JudicialEvent; onUpdate: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const qc = useQueryClient()

  const updateMutation = useMutation({
    mutationFn: (data: any) => publicationsApi.updateEvent(event.id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['andamentos-feed'] }); onUpdate() },
  })

  const urg = URGENCY_CONFIG[event.urgency] || URGENCY_CONFIG.normal
  const sta = STATUS_CONFIG[event.status] || STATUS_CONFIG.new
  const srcColor = SOURCE_COLORS[event.source] || 'bg-gray-100 text-gray-700'
  const UrgIcon = urg.icon

  return (
    <div className={`bg-white rounded-xl border transition-all duration-200 ${
      event.status === 'new' ? 'border-blue-300 shadow-sm shadow-blue-100' : 'border-gray-200'
    } ${event.is_overdue ? 'border-red-300' : ''}`}>
      {/* Faixa de urgência */}
      <div className={`h-0.5 rounded-t-xl ${urg.dot}`} />

      <div className="p-4">
        <div className="flex items-start gap-3">
          {/* Dot indicador */}
          <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${urg.dot}`} />

          <div className="flex-1 min-w-0">
            {/* Header da card */}
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-1.5 mb-1">
                  <span className="text-xs font-mono text-gray-500 font-medium">
                    {event.process_cnj || '—'}
                  </span>
                  <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${srcColor}`}>
                    {SOURCE_LABELS[event.source] || event.source}
                  </span>
                  {event.status === 'new' && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-blue-600 text-white font-semibold">
                      NOVO
                    </span>
                  )}
                  {event.is_overdue && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-red-600 text-white font-semibold flex items-center gap-1">
                      <AlertTriangle size={9} /> VENCIDO
                    </span>
                  )}
                </div>

                <p className="font-semibold text-gray-900 text-sm leading-snug">
                  {EVENT_TYPE_LABELS[event.event_type] || event.event_type_display}
                  {event.publication_metadata?.orgao_julgador && (
                    <span className="font-normal text-gray-500 ml-1.5 text-xs">
                      — {event.publication_metadata.orgao_julgador}
                    </span>
                  )}
                </p>

                <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                  {event.raw_text_preview}
                </p>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                <span className="text-xs text-gray-400">
                  {formatDate(event.publication_date)}
                </span>
                <button
                  onClick={() => setExpanded(v => !v)}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>
              </div>
            </div>

            {/* Footer compacto */}
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${urg.color}`}>
                <UrgIcon size={9} className="inline mr-1" />
                {urg.label}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${sta.color}`}>
                {sta.label}
              </span>
              {event.days_until_deadline !== null && (
                <span className={`text-xs ${event.days_until_deadline < 0 ? 'text-red-600' : 'text-gray-500'}`}>
                  {event.days_until_deadline < 0
                    ? `${Math.abs(event.days_until_deadline)}d vencido`
                    : `${event.days_until_deadline}d restantes`}
                </span>
              )}
              {event.assigned_to && (
                <span className="text-xs text-gray-500">
                  → {event.assigned_to.full_name}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Expandido */}
        {expanded && (
          <div className="mt-4 pt-4 border-t border-gray-100 space-y-4">
            {/* Texto completo */}
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                Texto Completo
              </p>
              <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                {event.raw_text_preview}
              </p>
            </div>

            {/* Metadados */}
            {event.publication_metadata && Object.keys(event.publication_metadata).length > 0 && (
              <div className="grid grid-cols-2 gap-2 text-xs">
                {event.publication_metadata.tipo_comunicacao && (
                  <div>
                    <span className="text-gray-400">Tipo: </span>
                    <span className="text-gray-700">{event.publication_metadata.tipo_comunicacao}</span>
                  </div>
                )}
                {event.publication_metadata.tribunal && (
                  <div>
                    <span className="text-gray-400">Tribunal: </span>
                    <span className="text-gray-700">{event.publication_metadata.tribunal}</span>
                  </div>
                )}
                {event.publication_metadata.url_publicacao && (
                  <a
                    href={event.publication_metadata.url_publicacao}
                    target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-1 text-blue-600 hover:underline col-span-2"
                  >
                    <ExternalLink size={11} /> Ver publicação original
                  </a>
                )}
              </div>
            )}

            {/* Ações */}
            <div className="flex items-center gap-2 flex-wrap">
              {event.status !== 'resolved' && (
                <Button
                  size="sm" variant="outline"
                  onClick={() => updateMutation.mutate({ status: 'in_progress' })}
                  disabled={updateMutation.isPending}
                  className="text-xs h-7"
                >
                  Em Andamento
                </Button>
              )}
              {event.status !== 'resolved' && (
                <Button
                  size="sm" variant="outline"
                  onClick={() => updateMutation.mutate({ status: 'resolved' })}
                  disabled={updateMutation.isPending}
                  className="text-xs h-7 text-green-700 border-green-300 hover:bg-green-50"
                >
                  <CheckCircle2 size={12} className="mr-1" /> Resolver
                </Button>
              )}
              {event.status !== 'archived' && (
                <Button
                  size="sm" variant="ghost"
                  onClick={() => updateMutation.mutate({ status: 'archived' })}
                  disabled={updateMutation.isPending}
                  className="text-xs h-7 text-gray-500"
                >
                  <Archive size={12} className="mr-1" /> Arquivar
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Tab: Feed ────────────────────────────────────────────────────────────────

function FeedTab() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [source, setSource] = useState('')
  const [eventType, setEventType] = useState('')
  const [urgency, setUrgency] = useState('')
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [showManualModal, setShowManualModal] = useState(false)
  const [page, setPage] = useState(1)

  const debouncedSearch = useDebounce(search, 300)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['andamentos-feed', { debouncedSearch, source, eventType, urgency, unreadOnly, page }],
    queryFn: () => publicationsApi.getFeed({
      q: debouncedSearch || undefined,
      source: source || undefined,
      event_type: eventType || undefined,
      urgency: urgency || undefined,
      unread: unreadOnly || undefined,
      page,
      page_size: 30,
    }),
    staleTime: 30_000,
  })

  const markAllMutation = useMutation({
    mutationFn: publicationsApi.markAllRead,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['andamentos-feed'] }),
  })

  const summary = data?.summary
  const grouped = groupByDate(data?.results ?? [])
  const sortedDates = Object.keys(grouped).sort((a, b) => b.localeCompare(a))

  return (
    <div className="space-y-5">
      {/* KPIs */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <KpiCard label="Total" value={summary.total} icon={Activity} color="bg-gray-100 text-gray-600" />
          <KpiCard label="Novos" value={summary.new} icon={Bell} color="bg-blue-100 text-blue-600" />
          <KpiCard label="Críticos" value={summary.critical} icon={AlertTriangle} color="bg-red-100 text-red-600" />
          <KpiCard label="Urgentes" value={summary.urgent} icon={Zap} color="bg-amber-100 text-amber-600" />
          <KpiCard label="Vencidos" value={summary.overdue} icon={Clock} color="bg-rose-100 text-rose-600" />
          <KpiCard label="Monitorados" value={summary.monitored_processes} icon={Radio} color="bg-purple-100 text-purple-600" />
        </div>
      )}

      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <Input
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }}
            placeholder="Buscar por CNJ, texto…"
            className="pl-9 h-9 text-sm"
          />
        </div>

        <Button
          size="sm" variant="outline"
          onClick={() => setShowFilters(v => !v)}
          className={`h-9 gap-1.5 ${showFilters ? 'bg-gray-100' : ''}`}
        >
          <Filter size={14} /> Filtros
        </Button>

        <Button
          size="sm" variant={unreadOnly ? 'default' : 'outline'}
          onClick={() => { setUnreadOnly(v => !v); setPage(1) }}
          className="h-9 gap-1.5"
        >
          {unreadOnly ? <BellOff size={14} /> : <Bell size={14} />}
          {unreadOnly ? 'Todos' : 'Não lidos'}
        </Button>

        {(summary?.new ?? 0) > 0 && (
          <Button
            size="sm" variant="outline"
            onClick={() => markAllMutation.mutate()}
            disabled={markAllMutation.isPending}
            className="h-9 gap-1.5 text-xs"
          >
            <Eye size={14} /> Marcar todos como lidos
          </Button>
        )}

        <Button size="sm" onClick={() => setShowManualModal(true)} className="h-9 gap-1.5 ml-auto">
          <Plus size={14} /> Novo andamento
        </Button>
      </div>

      {/* Filtros expandidos */}
      {showFilters && (
        <div className="bg-gray-50 rounded-lg p-4 flex flex-wrap gap-3 border border-gray-200">
          <Select value={source} onValueChange={v => { setSource(v === 'all' ? '' : v); setPage(1) }}>
            <SelectTrigger className="w-40 h-8 text-xs">
              <SelectValue placeholder="Fonte" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas as fontes</SelectItem>
              {Object.entries(SOURCE_LABELS).map(([k, v]) => (
                <SelectItem key={k} value={k}>{v}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={eventType} onValueChange={v => { setEventType(v === 'all' ? '' : v); setPage(1) }}>
            <SelectTrigger className="w-44 h-8 text-xs">
              <SelectValue placeholder="Tipo de evento" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos os tipos</SelectItem>
              {Object.entries(EVENT_TYPE_LABELS).map(([k, v]) => (
                <SelectItem key={k} value={k}>{v}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={urgency} onValueChange={v => { setUrgency(v === 'all' ? '' : v); setPage(1) }}>
            <SelectTrigger className="w-36 h-8 text-xs">
              <SelectValue placeholder="Urgência" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Qualquer urgência</SelectItem>
              <SelectItem value="critical">Crítica</SelectItem>
              <SelectItem value="urgent">Urgente</SelectItem>
              <SelectItem value="normal">Normal</SelectItem>
            </SelectContent>
          </Select>

          {(source || eventType || urgency) && (
            <Button
              size="sm" variant="ghost"
              onClick={() => { setSource(''); setEventType(''); setUrgency(''); setPage(1) }}
              className="h-8 text-xs gap-1"
            >
              <X size={12} /> Limpar
            </Button>
          )}
        </div>
      )}

      {/* Feed agrupado */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500 text-sm">Carregando andamentos…</div>
      ) : sortedDates.length === 0 ? (
        <div className="text-center py-16">
          <Activity size={40} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500">Nenhum andamento encontrado</p>
          <p className="text-gray-400 text-sm mt-1">
            Ative o monitoramento de processos ou adicione andamentos manualmente
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {sortedDates.map(dateStr => (
            <div key={dateStr}>
              <div className="flex items-center gap-3 mb-3">
                <div className="h-px bg-gray-200 flex-1" />
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide px-2">
                  {formatGroupDate(dateStr)}
                </span>
                <div className="h-px bg-gray-200 flex-1" />
              </div>
              <div className="space-y-2.5">
                {grouped[dateStr].map(ev => (
                  <EventCard key={ev.id} event={ev} onUpdate={() => refetch()} />
                ))}
              </div>
            </div>
          ))}

          {/* Paginação */}
          {(data?.has_more || page > 1) && (
            <div className="flex items-center justify-center gap-3 pt-2">
              {page > 1 && (
                <Button size="sm" variant="outline" onClick={() => setPage(p => p - 1)}>
                  Anterior
                </Button>
              )}
              <span className="text-sm text-gray-500">Página {page}</span>
              {data?.has_more && (
                <Button size="sm" variant="outline" onClick={() => setPage(p => p + 1)}>
                  Mais andamentos
                </Button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Modal andamento manual */}
      <ManualPublicationModal
        open={showManualModal}
        onClose={() => setShowManualModal(false)}
        onSuccess={() => {
          setShowManualModal(false)
          qc.invalidateQueries({ queryKey: ['andamentos-feed'] })
        }}
      />
    </div>
  )
}

// ─── Modal: Andamento Manual ──────────────────────────────────────────────────

function ManualPublicationModal({ open, onClose, onSuccess }: {
  open: boolean; onClose: () => void; onSuccess: () => void
}) {
  const [text, setText] = useState('')
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [cnj, setCnj] = useState('')
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: () => publicationsApi.createManual({
      raw_text: text.trim(),
      publication_date: date,
      process_cnj: cnj.trim() || undefined,
      source: 'manual',
    }),
    onSuccess,
    onError: () => setError('Erro ao salvar. Verifique os dados e tente novamente.'),
  })

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Novo Andamento Manual</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div>
            <Label className="text-xs font-semibold text-gray-600 mb-1.5 block">
              Data do Andamento *
            </Label>
            <Input type="date" value={date} onChange={e => setDate(e.target.value)} className="h-9" />
          </div>
          <div>
            <Label className="text-xs font-semibold text-gray-600 mb-1.5 block">
              Número CNJ do Processo
            </Label>
            <Input
              value={cnj}
              onChange={e => setCnj(e.target.value)}
              placeholder="0000000-00.0000.0.00.0000"
              className="h-9 font-mono text-sm"
            />
          </div>
          <div>
            <Label className="text-xs font-semibold text-gray-600 mb-1.5 block">
              Descrição do Andamento *
            </Label>
            <Textarea
              value={text}
              onChange={e => setText(e.target.value)}
              placeholder="Descreva o andamento processual…"
              rows={4}
              className="text-sm resize-none"
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!text.trim() || !date || mutation.isPending}
          >
            {mutation.isPending ? 'Salvando…' : 'Salvar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Tab: Monitoramento ───────────────────────────────────────────────────────

function MonitoringTab() {
  const qc = useQueryClient()
  const [showModal, setShowModal] = useState(false)

  const { data: monitorings, isLoading } = useQuery({
    queryKey: ['andamentos-monitoring'],
    queryFn: () => publicationsApi.listMonitoring(),
    staleTime: 30_000,
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      publicationsApi.updateMonitoring(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['andamentos-monitoring'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => publicationsApi.deleteMonitoring(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['andamentos-monitoring'] }),
  })

  const syncMutation = useMutation({
    mutationFn: (id: number) => publicationsApi.syncProcess(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['andamentos-monitoring'] })
      qc.invalidateQueries({ queryKey: ['andamentos-feed'] })
    },
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-gray-900">Processos Monitorados</h3>
          <p className="text-sm text-gray-500 mt-0.5">
            O sistema verificará automaticamente novidades via DataJud e Comunica/PJe.
          </p>
        </div>
        <Button size="sm" onClick={() => setShowModal(true)} className="gap-1.5">
          <Plus size={14} /> Monitorar processo
        </Button>
      </div>

      {isLoading ? (
        <p className="text-sm text-gray-500 py-4">Carregando…</p>
      ) : !monitorings?.length ? (
        <div className="text-center py-16 border-2 border-dashed border-gray-200 rounded-xl">
          <Radio size={40} className="mx-auto text-gray-300 mb-3" />
          <p className="font-medium text-gray-600">Nenhum processo monitorado</p>
          <p className="text-sm text-gray-400 mt-1">
            Adicione processos para receber andamentos automaticamente
          </p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {monitorings.map(m => (
            <MonitoringCard
              key={m.id}
              monitoring={m}
              onToggle={() => toggleMutation.mutate({ id: m.id, is_active: !m.is_active })}
              onSync={() => syncMutation.mutate(m.id)}
              onDelete={() => deleteMutation.mutate(m.id)}
              isSyncing={syncMutation.isPending && syncMutation.variables === m.id}
            />
          ))}
        </div>
      )}

      <MonitoringModal
        open={showModal}
        onClose={() => setShowModal(false)}
        onSuccess={() => {
          setShowModal(false)
          qc.invalidateQueries({ queryKey: ['andamentos-monitoring'] })
        }}
      />
    </div>
  )
}

function MonitoringCard({ monitoring, onToggle, onSync, onDelete, isSyncing }: {
  monitoring: ProcessMonitoring
  onToggle: () => void
  onSync: () => void
  onDelete: () => void
  isSyncing: boolean
}) {
  return (
    <div className={`bg-white rounded-xl border p-4 flex items-center gap-4 ${
      monitoring.is_active ? 'border-gray-200' : 'border-gray-100 opacity-60'
    }`}>
      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${monitoring.is_active ? 'bg-green-500' : 'bg-gray-300'}`} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-semibold text-gray-800">
            {monitoring.process_cnj}
          </span>
          {monitoring.tribunal && (
            <span className="text-xs px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded font-medium">
              {monitoring.tribunal}
            </span>
          )}
          {!monitoring.initial_sync_done && (
            <span className="text-xs px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded">
              Sync inicial pendente
            </span>
          )}
        </div>
        <p className="text-sm text-gray-600 mt-0.5">{monitoring.process_title}</p>
        <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
          {monitoring.current_phase && <span>{monitoring.current_phase}</span>}
          {monitoring.last_synced_at && (
            <span>Última sync: {formatDate(monitoring.last_synced_at)}</span>
          )}
          <span className="text-blue-600 font-medium">
            {monitoring.recent_publications_count} andamentos (30d)
          </span>
          <span>{monitoring.sources.join(', ')}</span>
        </div>
      </div>

      <div className="flex items-center gap-2 flex-shrink-0">
        <Button
          size="sm" variant="ghost"
          onClick={onSync}
          disabled={!monitoring.is_active || isSyncing}
          className="h-8 text-xs gap-1 text-gray-600"
          title="Sincronizar agora via DataJud"
        >
          <RefreshCw size={13} className={isSyncing ? 'animate-spin' : ''} />
        </Button>

        <Switch
          checked={monitoring.is_active}
          onCheckedChange={onToggle}
        />

        <Button
          size="sm" variant="ghost"
          onClick={onDelete}
          className="h-8 w-8 p-0 text-gray-400 hover:text-red-600"
        >
          <Trash2 size={14} />
        </Button>
      </div>
    </div>
  )
}

function MonitoringModal({ open, onClose, onSuccess }: {
  open: boolean; onClose: () => void; onSuccess: () => void
}) {
  const [processId, setProcessId] = useState('')
  const [autocomplete, setAutocomplete] = useState(false)
  const [sources, setSources] = useState(['datajud', 'comunica'])

  const mutation = useMutation({
    mutationFn: () => publicationsApi.createMonitoring({
      process: parseInt(processId),
      autocomplete_enabled: autocomplete,
      sources,
    }),
    onSuccess,
  })

  const toggleSource = (s: string) => {
    setSources(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Monitorar Processo</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div>
            <Label className="text-xs font-semibold text-gray-600 mb-1.5 block">
              ID do Processo *
            </Label>
            <Input
              type="number"
              value={processId}
              onChange={e => setProcessId(e.target.value)}
              placeholder="ID do processo no sistema"
              className="h-9"
            />
            <p className="text-xs text-gray-400 mt-1">
              O número CNJ será detectado automaticamente pelo número do processo.
            </p>
          </div>

          <div>
            <Label className="text-xs font-semibold text-gray-600 mb-2 block">
              Fontes de Monitoramento
            </Label>
            <div className="flex flex-wrap gap-2">
              {[
                { key: 'datajud', label: 'DataJud (CNJ)' },
                { key: 'comunica', label: 'Comunica (PJe)' },
                { key: 'djen', label: 'DJEN' },
              ].map(s => (
                <button
                  key={s.key}
                  onClick={() => toggleSource(s.key)}
                  className={`text-xs px-3 py-1.5 rounded-lg border font-medium transition-colors ${
                    sources.includes(s.key)
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
            <Switch checked={autocomplete} onCheckedChange={setAutocomplete} />
            <div>
              <p className="text-sm font-medium text-gray-800">Autocompletar processo</p>
              <p className="text-xs text-gray-500">
                Preencher campos vazios do processo com dados do DataJud
              </p>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!processId || !sources.length || mutation.isPending}
          >
            {mutation.isPending ? 'Ativando…' : 'Ativar monitoramento'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Tab: Consultar DataJud ───────────────────────────────────────────────────

function DataJudTab() {
  const qc = useQueryClient()
  const [number, setNumber] = useState('')
  const [result, setResult] = useState<DataJudResult | null>(null)
  const [error, setError] = useState('')

  const searchMutation = useMutation({
    mutationFn: () => publicationsApi.lookupDataJud(number.trim()),
    onSuccess: data => { setResult(data); setError('') },
    onError: () => setError('Processo não encontrado ou tribunal não reconhecido pelo número CNJ.'),
  })

  const monitorMutation = useMutation({
    mutationFn: (processId: number) => publicationsApi.createMonitoring({
      process: processId,
      sources: ['datajud', 'comunica'],
    }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['andamentos-monitoring'] }),
  })

  return (
    <div className="space-y-5 max-w-3xl">
      <div>
        <h3 className="font-semibold text-gray-900">Consultar DataJud</h3>
        <p className="text-sm text-gray-500 mt-0.5">
          Busque dados de qualquer processo público pelo número CNJ antes de ativar o monitoramento.
        </p>
      </div>

      <div className="flex gap-2">
        <Input
          value={number}
          onChange={e => setNumber(e.target.value)}
          placeholder="0000000-00.0000.0.00.0000"
          className="font-mono h-10"
          onKeyDown={e => { if (e.key === 'Enter' && number.trim()) searchMutation.mutate() }}
        />
        <Button
          onClick={() => searchMutation.mutate()}
          disabled={!number.trim() || searchMutation.isPending}
          className="h-10 px-5"
        >
          {searchMutation.isPending ? <RefreshCw size={15} className="animate-spin" /> : <Search size={15} />}
          <span className="ml-2">Consultar</span>
        </Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && result.found && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4 border-b border-gray-200">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-mono text-sm font-bold text-gray-800">{result.cnj_number}</p>
                <p className="font-semibold text-lg text-gray-900 mt-1">{result.classe}</p>
                <p className="text-sm text-gray-600">{result.assunto}</p>
              </div>
              <span className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded font-medium">
                {result.tribunal}
              </span>
            </div>
          </div>

          <div className="p-6 space-y-5">
            {/* Infos */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Órgão Julgador</p>
                <p className="text-gray-800 mt-0.5">{result.orgao_julgador || '—'}</p>
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Ajuizamento</p>
                <p className="text-gray-800 mt-0.5">{result.data_ajuizamento ? formatDate(result.data_ajuizamento) : '—'}</p>
              </div>
              <div className="col-span-2">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Fase Atual</p>
                <p className="text-gray-800 mt-0.5">{result.fase_atual || '—'}</p>
              </div>
            </div>

            {/* Partes */}
            {result.partes.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Partes</p>
                <div className="space-y-1.5">
                  {result.partes.map((p, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm">
                      <span className={`text-xs px-1.5 py-0.5 rounded font-semibold uppercase flex-shrink-0 ${
                        p.polo === 'AT' ? 'bg-blue-100 text-blue-700' :
                        p.polo === 'RE' ? 'bg-orange-100 text-orange-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>{p.polo}</span>
                      <div>
                        <span className="text-gray-800 font-medium">{p.nome}</span>
                        {p.advogados.length > 0 && (
                          <p className="text-xs text-gray-500 mt-0.5">
                            Adv: {p.advogados.join(', ')}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Últimos movimentos */}
            {result.movimentos.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">
                  Últimas Movimentações ({Math.min(result.movimentos.length, 10)})
                </p>
                <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                  {result.movimentos.slice(-10).reverse().map((m, i) => (
                    <div key={i} className="flex gap-3 text-sm">
                      <span className="text-xs text-gray-400 flex-shrink-0 font-mono">
                        {m.data ? formatDate(m.data) : '—'}
                      </span>
                      <div>
                        <span className="text-gray-700">{m.nome}</span>
                        {m.complemento && (
                          <span className="text-gray-500 ml-1">— {m.complemento}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Tab: Configurações ───────────────────────────────────────────────────────

function SettingsTab() {
  const qc = useQueryClient()
  const [showRuleModal, setShowRuleModal] = useState(false)
  const [showFilterModal, setShowFilterModal] = useState(false)

  const { data: rules } = useQuery({
    queryKey: ['pub-rules'],
    queryFn: publicationsApi.listRules,
    staleTime: 60_000,
  })

  const { data: filters } = useQuery({
    queryKey: ['pub-filters'],
    queryFn: publicationsApi.listFilters,
    staleTime: 60_000,
  })

  const { data: imports } = useQuery({
    queryKey: ['pub-imports'],
    queryFn: () => publicationsApi.listImports({ limit: 20 }),
    staleTime: 30_000,
  })

  const deleteRuleMut = useMutation({
    mutationFn: publicationsApi.deleteRule,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pub-rules'] }),
  })
  const deleteFilterMut = useMutation({
    mutationFn: publicationsApi.deleteFilter,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pub-filters'] }),
  })

  const comunica = useMutation({
    mutationFn: () => publicationsApi.syncComunica(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pub-imports'] }),
  })

  return (
    <div className="space-y-8 max-w-3xl">
      {/* Regras de prazo */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="font-semibold text-gray-900">Regras de Prazo</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Prazos criados automaticamente por tipo de evento
            </p>
          </div>
          <Button size="sm" variant="outline" onClick={() => setShowRuleModal(true)} className="gap-1">
            <Plus size={13} /> Nova regra
          </Button>
        </div>

        {!rules?.length ? (
          <div className="text-center py-8 border border-dashed rounded-lg text-gray-400 text-sm">
            Nenhuma regra configurada
          </div>
        ) : (
          <div className="space-y-2">
            {rules.map(r => (
              <div key={r.id} className="flex items-center gap-3 bg-white border border-gray-200 rounded-lg px-4 py-3">
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-800">{r.event_type_display}</p>
                  <p className="text-xs text-gray-500">
                    {r.days} dias {r.business_days ? 'úteis' : 'corridos'} · {r.description}
                    {r.base_legal && ` · ${r.base_legal}`}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${r.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                    {r.is_active ? 'Ativa' : 'Inativa'}
                  </span>
                  <Button
                    size="sm" variant="ghost"
                    onClick={() => deleteRuleMut.mutate(r.id)}
                    className="h-7 w-7 p-0 text-gray-400 hover:text-red-600"
                  >
                    <Trash2 size={13} />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Filtros de matching */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="font-semibold text-gray-900">Filtros de Matching</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              CNJ, OAB, CPF, CNPJ ou palavras-chave para detecção automática
            </p>
          </div>
          <Button size="sm" variant="outline" onClick={() => setShowFilterModal(true)} className="gap-1">
            <Plus size={13} /> Novo filtro
          </Button>
        </div>

        {!filters?.length ? (
          <div className="text-center py-8 border border-dashed rounded-lg text-gray-400 text-sm">
            Nenhum filtro configurado
          </div>
        ) : (
          <div className="space-y-2">
            {filters.map(f => (
              <div key={f.id} className="flex items-center gap-3 bg-white border border-gray-200 rounded-lg px-4 py-3">
                <span className="text-xs font-semibold px-2 py-0.5 bg-gray-100 text-gray-600 rounded uppercase">
                  {f.filter_type_display}
                </span>
                <div className="flex-1">
                  <p className="text-sm font-mono text-gray-800">{f.value}</p>
                  {f.description && <p className="text-xs text-gray-500">{f.description}</p>}
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <span>{f.match_count} matches</span>
                  <Button
                    size="sm" variant="ghost"
                    onClick={() => deleteFilterMut.mutate(f.id)}
                    className="h-7 w-7 p-0 text-gray-400 hover:text-red-600"
                  >
                    <Trash2 size={13} />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Sync Comunica */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="font-semibold text-gray-900">Sincronização Comunica/PJe</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Download do caderno diário compactado com comunicações de todos os processos monitorados
            </p>
          </div>
          <Button
            size="sm" variant="outline"
            onClick={() => comunica.mutate()}
            disabled={comunica.isPending}
            className="gap-1"
          >
            <RefreshCw size={13} className={comunica.isPending ? 'animate-spin' : ''} />
            Sincronizar hoje
          </Button>
        </div>

        {imports && imports.length > 0 && (
          <div className="overflow-hidden rounded-lg border border-gray-200">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="px-3 py-2 text-left font-semibold text-gray-600">Data ref.</th>
                  <th className="px-3 py-2 text-left font-semibold text-gray-600">Fonte</th>
                  <th className="px-3 py-2 text-left font-semibold text-gray-600">Status</th>
                  <th className="px-3 py-2 text-right font-semibold text-gray-600">Importadas</th>
                  <th className="px-3 py-2 text-right font-semibold text-gray-600">Vinculadas</th>
                  <th className="px-3 py-2 text-right font-semibold text-gray-600">Erros</th>
                </tr>
              </thead>
              <tbody>
                {imports.map(imp => (
                  <tr key={imp.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                    <td className="px-3 py-2 font-mono">
                      {imp.reference_date ? formatDate(imp.reference_date) : '—'}
                    </td>
                    <td className="px-3 py-2">{imp.source_display}</td>
                    <td className="px-3 py-2">
                      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                        imp.status === 'success' ? 'bg-green-100 text-green-700' :
                        imp.status === 'failed' ? 'bg-red-100 text-red-700' :
                        imp.status === 'partial' ? 'bg-amber-100 text-amber-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>{imp.status_display}</span>
                    </td>
                    <td className="px-3 py-2 text-right">{imp.total_imported}</td>
                    <td className="px-3 py-2 text-right">{imp.total_matched}</td>
                    <td className="px-3 py-2 text-right text-red-600">{imp.total_errors || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Modals */}
      <RuleModal open={showRuleModal} onClose={() => setShowRuleModal(false)}
        onSuccess={() => { setShowRuleModal(false); qc.invalidateQueries({ queryKey: ['pub-rules'] }) }} />
      <FilterModal open={showFilterModal} onClose={() => setShowFilterModal(false)}
        onSuccess={() => { setShowFilterModal(false); qc.invalidateQueries({ queryKey: ['pub-filters'] }) }} />
    </div>
  )
}

function RuleModal({ open, onClose, onSuccess }: { open: boolean; onClose: () => void; onSuccess: () => void }) {
  const [form, setForm] = useState({ event_type: '', description: '', days: 15, business_days: true, auto_create_deadline: true, base_legal: '', is_active: true, priority: 0, auto_urgency: 'normal' as const })
  const mut = useMutation({
    mutationFn: () => publicationsApi.createRule(form as any),
    onSuccess,
  })
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader><DialogTitle>Nova Regra de Prazo</DialogTitle></DialogHeader>
        <div className="space-y-3 py-2">
          <Select value={form.event_type} onValueChange={v => setForm(f => ({ ...f, event_type: v }))}>
            <SelectTrigger className="h-9"><SelectValue placeholder="Tipo de evento *" /></SelectTrigger>
            <SelectContent>
              {Object.entries(EVENT_TYPE_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
            </SelectContent>
          </Select>
          <Input placeholder="Descrição *" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} className="h-9" />
          <Input placeholder="Base legal (opcional)" value={form.base_legal} onChange={e => setForm(f => ({ ...f, base_legal: e.target.value }))} className="h-9 text-sm" />
          <div className="flex gap-2">
            <Input type="number" placeholder="Dias" value={form.days} onChange={e => setForm(f => ({ ...f, days: parseInt(e.target.value) || 15 }))} className="h-9 w-24" />
            <label className="flex items-center gap-2 text-sm flex-1">
              <Switch checked={form.business_days} onCheckedChange={v => setForm(f => ({ ...f, business_days: v }))} />
              Dias úteis
            </label>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button onClick={() => mut.mutate()} disabled={!form.event_type || !form.description || mut.isPending}>
            {mut.isPending ? 'Salvando…' : 'Criar regra'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function FilterModal({ open, onClose, onSuccess }: { open: boolean; onClose: () => void; onSuccess: () => void }) {
  const [form, setForm] = useState({ filter_type: '', value: '', description: '', is_active: true, case_sensitive: false, process: null as number | null })
  const mut = useMutation({
    mutationFn: () => publicationsApi.createFilter(form as any),
    onSuccess,
  })
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader><DialogTitle>Novo Filtro de Matching</DialogTitle></DialogHeader>
        <div className="space-y-3 py-2">
          <Select value={form.filter_type} onValueChange={v => setForm(f => ({ ...f, filter_type: v }))}>
            <SelectTrigger className="h-9"><SelectValue placeholder="Tipo de filtro *" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="cnj">Número CNJ</SelectItem>
              <SelectItem value="oab">OAB</SelectItem>
              <SelectItem value="cpf">CPF</SelectItem>
              <SelectItem value="cnpj">CNPJ</SelectItem>
              <SelectItem value="keyword">Palavra-chave</SelectItem>
            </SelectContent>
          </Select>
          <Input
            placeholder="Valor *"
            value={form.value}
            onChange={e => setForm(f => ({ ...f, value: e.target.value }))}
            className={`h-9 ${form.filter_type === 'cnj' ? 'font-mono' : ''}`}
          />
          <Input placeholder="Descrição (opcional)" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} className="h-9 text-sm" />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button onClick={() => mut.mutate()} disabled={!form.filter_type || !form.value || mut.isPending}>
            {mut.isPending ? 'Salvando…' : 'Criar filtro'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Página Principal ─────────────────────────────────────────────────────────

export function AndamentosPage() {
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 pt-6 pb-4 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-blue-600 rounded-lg flex items-center justify-center">
            <Activity size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Andamentos</h1>
            <p className="text-sm text-gray-500">
              Publicações judiciais · DataJud · Comunica/PJe · DJEN
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex-1 overflow-hidden">
        <Tabs defaultValue="feed" className="h-full flex flex-col">
          <div className="px-6 pt-4 border-b border-gray-200 bg-white">
            <TabsList className="h-9 bg-gray-100">
              <TabsTrigger value="feed" className="text-xs gap-1.5">
                <Bell size={13} /> Feed
              </TabsTrigger>
              <TabsTrigger value="monitoring" className="text-xs gap-1.5">
                <Radio size={13} /> Monitoramento
              </TabsTrigger>
              <TabsTrigger value="datajud" className="text-xs gap-1.5">
                <Database size={13} /> Consultar DataJud
              </TabsTrigger>
              <TabsTrigger value="settings" className="text-xs gap-1.5">
                <Settings2 size={13} /> Configurações
              </TabsTrigger>
            </TabsList>
          </div>

          <div className="flex-1 overflow-auto">
            <TabsContent value="feed" className="p-6 mt-0 h-full">
              <FeedTab />
            </TabsContent>
            <TabsContent value="monitoring" className="p-6 mt-0">
              <MonitoringTab />
            </TabsContent>
            <TabsContent value="datajud" className="p-6 mt-0">
              <DataJudTab />
            </TabsContent>
            <TabsContent value="settings" className="p-6 mt-0">
              <SettingsTab />
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  )
}

export default AndamentosPage
