import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft, Edit, Trash2, Scale, Calendar, User, FileText,
  Clock, AlertTriangle, Plus, Lock, Unlock, ChevronRight,
} from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { PageHeader } from '@/components/layout/PageHeader'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { processesApi } from '@/api/processes'
import { formatDate, formatCurrency, formatRelative, initials } from '@/lib/utils'
import { PROCESS_STATUS_LABELS, PROCESS_PHASE_LABELS, PROCESS_AREA_LABELS, RISK_LABELS, PARTY_ROLE_LABELS } from '@/lib/constants'
import { cn } from '@/lib/utils'

export function ProcessDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [newNote, setNewNote] = useState('')
  const [notePrivate, setNotePrivate] = useState(false)
  const [addingNote, setAddingNote] = useState(false)

  const processId = Number(id)

  const { data: process, isLoading, isError } = useQuery({
    queryKey: ['process', processId],
    queryFn: () => processesApi.get(processId),
    enabled: !!processId,
  })

  const { data: notes, isLoading: notesLoading } = useQuery({
    queryKey: ['process-notes', processId],
    queryFn: () => processesApi.getNotes(processId),
    enabled: !!processId,
  })

  const deleteMutation = useMutation({
    mutationFn: () => processesApi.delete(processId),
    onSuccess: () => {
      toast.success('Processo excluído com sucesso.')
      navigate('/app/processos')
    },
    onError: () => toast.error('Erro ao excluir processo.'),
  })

  const addNoteMutation = useMutation({
    mutationFn: () => processesApi.addNote(processId, { text: newNote, is_private: notePrivate }),
    onSuccess: () => {
      toast.success('Nota adicionada.')
      setNewNote('')
      setNotePrivate(false)
      setAddingNote(false)
      queryClient.invalidateQueries({ queryKey: ['process-notes', processId] })
    },
    onError: () => toast.error('Erro ao adicionar nota.'),
  })

  const deleteNoteMutation = useMutation({
    mutationFn: (noteId: number) => processesApi.deleteNote(processId, noteId),
    onSuccess: () => {
      toast.success('Nota removida.')
      queryClient.invalidateQueries({ queryKey: ['process-notes', processId] })
    },
  })

  if (isLoading) return <DetailSkeleton />
  if (isError || !process) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 text-slate-400">
        <AlertTriangle size={32} />
        <p className="text-sm">Processo não encontrado.</p>
        <Button variant="outline" size="sm" onClick={() => navigate('/app/processos')}>
          <ArrowLeft size={14} className="mr-2" /> Voltar
        </Button>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto page-enter">
      <PageHeader
        title={process.number}
        subtitle={process.subject || 'Sem assunto'}
        breadcrumbs={[
          { label: 'Processos', href: '/app/processos' },
          { label: process.number },
        ]}
        actions={
          <div className="flex gap-2">
            <Button
              variant="outline" size="sm"
              onClick={() => navigate(`/app/processos/${processId}/editar`)}
              className="gap-2"
            >
              <Edit size={14} /> Editar
            </Button>
            <Button
              variant="outline" size="sm"
              onClick={() => setDeleteOpen(true)}
              className="gap-2 text-red-600 border-red-200 hover:bg-red-50"
            >
              <Trash2 size={14} /> Excluir
            </Button>
          </div>
        }
      />

      {/* Status pills */}
      <div className="flex flex-wrap items-center gap-2 mb-6">
        <StatusBadge value={process.status} variant="process-status" />
        <StatusBadge value={process.phase} variant="process-phase" />
        <StatusBadge value={process.area} variant="process-area" />
        {process.risk && <StatusBadge value={process.risk} variant="risk" />}
      </div>

      {/* 2-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Main content (2/3) */}
        <div className="lg:col-span-2">
          <Tabs defaultValue="info">
            <TabsList className="bg-slate-100 h-9 mb-5">
              <TabsTrigger value="info" className="text-xs">Informações</TabsTrigger>
              <TabsTrigger value="parties" className="text-xs">
                Partes ({process.parties.length})
              </TabsTrigger>
              <TabsTrigger value="notes" className="text-xs">
                Notas ({notes?.length ?? 0})
              </TabsTrigger>
              <TabsTrigger value="deadlines" className="text-xs">
                Prazos ({process.deadlines_count})
              </TabsTrigger>
            </TabsList>

            {/* Tab: Informações */}
            <TabsContent value="info" className="space-y-4">
              <InfoCard title="Dados Judiciais">
                <InfoRow label="Número CNJ" value={<span className="font-mono text-sm">{process.number}</span>} />
                <InfoRow label="Tribunal/Vara" value={process.court} />
                <InfoRow label="Unidade Judiciária" value={process.court_unit} />
                <InfoRow label="Juiz" value={process.judge_name} />
                <InfoRow label="Assunto" value={process.subject} />
              </InfoCard>

              <InfoCard title="Datas">
                <InfoRow label="Ajuizamento" value={formatDate(process.filing_date)} />
                <InfoRow label="Distribuição" value={formatDate(process.distribution_date)} />
                <InfoRow label="Audiência Inicial" value={formatDate(process.first_hearing_date)} />
                <InfoRow label="Sentença" value={formatDate(process.sentence_date)} />
                <InfoRow label="Último Movimento" value={formatDate(process.last_movement_date)} />
              </InfoCard>

              {process.description && (
                <InfoCard title="Descrição">
                  <p className="text-sm text-slate-600 leading-relaxed">{process.description}</p>
                </InfoCard>
              )}

              {process.last_movement && (
                <InfoCard title="Último Movimento">
                  <p className="text-sm text-slate-600 leading-relaxed">{process.last_movement}</p>
                </InfoCard>
              )}

              {process.next_action && (
                <InfoCard title="Próxima Ação">
                  <p className="text-sm text-slate-600 leading-relaxed">{process.next_action}</p>
                </InfoCard>
              )}

              {process.tags && process.tags.length > 0 && (
                <InfoCard title="Tags">
                  <div className="flex flex-wrap gap-1.5">
                    {process.tags.map((tag) => (
                      <span key={tag} className="px-2 py-0.5 rounded-md bg-slate-100 text-xs text-slate-600 border border-slate-200">
                        {tag}
                      </span>
                    ))}
                  </div>
                </InfoCard>
              )}
            </TabsContent>

            {/* Tab: Partes */}
            <TabsContent value="parties">
              {process.parties.length === 0 ? (
                <div className="text-center py-12 text-slate-400 text-sm">
                  Nenhuma parte cadastrada.
                </div>
              ) : (
                <div className="space-y-3">
                  {process.parties.map((party) => (
                    <Card key={party.id} className="border-slate-200 shadow-none">
                      <CardContent className="p-4">
                        <div className="flex items-start gap-3">
                          <div className="w-9 h-9 rounded-lg bg-slate-100 flex items-center justify-center text-xs font-semibold text-slate-600 flex-shrink-0">
                            {initials(party.name)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <p className="text-sm font-semibold text-slate-900">{party.name}</p>
                              <span className="text-xs px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
                                {PARTY_ROLE_LABELS[party.role] ?? party.role}
                              </span>
                            </div>
                            <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                              {party.document && <span>Doc: {party.document}</span>}
                              {party.email && <span>{party.email}</span>}
                              {party.phone && <span>{party.phone}</span>}
                            </div>
                            {party.notes && (
                              <p className="text-xs text-slate-400 mt-1.5 italic">{party.notes}</p>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* Tab: Notas */}
            <TabsContent value="notes" className="space-y-3">
              {/* Add note */}
              {!addingNote ? (
                <Button
                  variant="outline" size="sm"
                  onClick={() => setAddingNote(true)}
                  className="gap-2 text-slate-600"
                >
                  <Plus size={14} /> Adicionar Nota
                </Button>
              ) : (
                <Card className="border-slate-200 shadow-none">
                  <CardContent className="p-4 space-y-3">
                    <Textarea
                      placeholder="Escreva sua nota aqui…"
                      value={newNote}
                      onChange={(e) => setNewNote(e.target.value)}
                      className="text-sm min-h-[100px] resize-none border-slate-200"
                      autoFocus
                    />
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={notePrivate}
                          onChange={(e) => setNotePrivate(e.target.checked)}
                          className="rounded"
                        />
                        <span className="text-xs text-slate-500 flex items-center gap-1">
                          <Lock size={11} /> Nota privada
                        </span>
                      </label>
                      <div className="flex gap-2">
                        <Button variant="ghost" size="sm" onClick={() => { setAddingNote(false); setNewNote('') }}>
                          Cancelar
                        </Button>
                        <Button
                          size="sm"
                          className="bg-blue-600 hover:bg-blue-700"
                          disabled={!newNote.trim() || addNoteMutation.isPending}
                          onClick={() => addNoteMutation.mutate()}
                        >
                          Salvar
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {notesLoading ? (
                <div className="space-y-3">
                  {[1, 2].map((i) => (
                    <div key={i} className="h-20 bg-slate-100 rounded-xl animate-pulse" />
                  ))}
                </div>
              ) : notes?.length === 0 ? (
                <div className="text-center py-12 text-slate-400 text-sm">
                  Nenhuma nota registrada.
                </div>
              ) : (
                <div className="space-y-3">
                  {notes?.map((note) => (
                    <Card key={note.id} className={cn('border-slate-200 shadow-none', note.is_private && 'border-amber-200 bg-amber-50/30')}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex-1">
                            {note.is_private && (
                              <span className="inline-flex items-center gap-1 text-[10px] text-amber-600 font-medium mb-1.5">
                                <Lock size={10} /> Nota privada
                              </span>
                            )}
                            <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{note.text}</p>
                            <p className="text-xs text-slate-400 mt-2">
                              {note.author_name} · {formatRelative(note.created_at)}
                            </p>
                          </div>
                          <button
                            onClick={() => deleteNoteMutation.mutate(note.id)}
                            className="text-slate-300 hover:text-red-400 transition-colors p-1 flex-shrink-0"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* Tab: Prazos */}
            <TabsContent value="deadlines">
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm text-slate-500">{process.deadlines_count} prazo(s) vinculado(s)</p>
                <Link
                  to="/app/prazos"
                  className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1"
                >
                  Ver todos os prazos <ChevronRight size={12} />
                </Link>
              </div>
              {process.next_deadline ? (
                <Card className="border-amber-200 bg-amber-50/30 shadow-none">
                  <CardContent className="p-4">
                    <p className="text-xs font-semibold text-amber-700 mb-1">Próximo prazo</p>
                    <p className="text-sm font-medium text-slate-900">{process.next_deadline.title}</p>
                    <p className="text-xs text-slate-500 mt-1">
                      {formatDate(process.next_deadline.due_date)}
                    </p>
                  </CardContent>
                </Card>
              ) : (
                <div className="text-center py-12 text-slate-400 text-sm">
                  Nenhum prazo pendente.
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>

        {/* Sidebar (1/3) */}
        <div className="space-y-4">
          {/* Indicadores */}
          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="pb-3 pt-4 px-4">
              <CardTitle className="text-sm font-semibold text-slate-900">Indicadores</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 space-y-3">
              {process.cause_value && (
                <InfoRow label="Valor da Causa" value={formatCurrency(process.cause_value)} />
              )}
              {process.success_probability !== null && process.success_probability !== undefined && (
                <div>
                  <p className="text-xs text-slate-500 mb-1.5">Probabilidade de Êxito</p>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 rounded-full"
                        style={{ width: `${process.success_probability}%` }}
                      />
                    </div>
                    <span className="text-xs font-semibold text-slate-700 tabular-nums">
                      {process.success_probability}%
                    </span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Responsável */}
          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="pb-3 pt-4 px-4">
              <CardTitle className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                <User size={14} className="text-slate-400" /> Responsável
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              {process.responsible_name ? (
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center text-xs font-semibold text-blue-600">
                    {initials(process.responsible_name)}
                  </div>
                  <p className="text-sm font-medium text-slate-800">{process.responsible_name}</p>
                </div>
              ) : (
                <p className="text-sm text-slate-400 italic">Não atribuído</p>
              )}
            </CardContent>
          </Card>

          {/* Datas relevantes */}
          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="pb-3 pt-4 px-4">
              <CardTitle className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                <Calendar size={14} className="text-slate-400" /> Datas
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 space-y-2">
              <InfoRow label="Criado" value={formatRelative(process.created_at)} />
              <InfoRow label="Atualizado" value={formatRelative(process.updated_at)} />
              {process.last_movement_date && (
                <InfoRow label="Últ. Movimento" value={formatDate(process.last_movement_date)} />
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Excluir processo?"
        description={`O processo ${process.number} será permanentemente excluído. Esta ação não pode ser desfeita.`}
        confirmLabel="Sim, excluir"
        variant="destructive"
        onConfirm={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
      />
    </div>
  )
}

function InfoCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="border-slate-200 shadow-none">
      <CardHeader className="pb-2 pt-4 px-4">
        <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{title}</CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4 space-y-2">{children}</CardContent>
    </Card>
  )
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  if (!value || value === '—') return null
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="text-xs text-slate-500 flex-shrink-0 pt-0.5">{label}</span>
      <span className="text-xs text-slate-800 text-right font-medium">{value}</span>
    </div>
  )
}

function DetailSkeleton() {
  return (
    <div className="max-w-6xl mx-auto space-y-4 animate-pulse">
      <div className="h-8 bg-slate-100 rounded w-64" />
      <div className="flex gap-2">
        {[1, 2, 3].map((i) => <div key={i} className="h-6 w-20 bg-slate-100 rounded-md" />)}
      </div>
      <div className="grid grid-cols-3 gap-5">
        <div className="col-span-2 space-y-4">
          <div className="h-10 bg-slate-100 rounded-lg w-80" />
          <div className="h-48 bg-slate-100 rounded-xl" />
          <div className="h-32 bg-slate-100 rounded-xl" />
        </div>
        <div className="space-y-4">
          <div className="h-32 bg-slate-100 rounded-xl" />
          <div className="h-24 bg-slate-100 rounded-xl" />
        </div>
      </div>
    </div>
  )
}
