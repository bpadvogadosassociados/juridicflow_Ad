import { useState, useRef, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin, { Draggable } from '@fullcalendar/interaction'
import listPlugin from '@fullcalendar/list'
import type { DateSelectArg, EventClickArg, EventDropArg, EventReceiveArg } from '@fullcalendar/core'
import { Plus, X, Trash2, Settings } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { PageHeader } from '@/components/layout/PageHeader'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { calendarApi, type CalendarEntry, type CreateEntryData } from '@/api/calendar'
import { cn } from '@/lib/utils'

const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#f97316', '#6366f1']

// Event template — stored in localStorage via Settings > Eventos
interface EventTemplate {
  id: string
  name: string
  description: string
  color: string
  requiredFields: { id: string; label: string }[]
}

function loadTemplates(): EventTemplate[] {
  try {
    const raw = localStorage.getItem('jf-event-templates')
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

export function CalendarPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const calRef = useRef<FullCalendar>(null)
  const draggableContainerRef = useRef<HTMLDivElement>(null)
  const draggableInstance = useRef<Draggable | null>(null)

  const [modalOpen, setModalOpen] = useState(false)
  const [selectedEntry, setSelectedEntry] = useState<CalendarEntry | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<CalendarEntry | null>(null)
  const [form, setForm] = useState<CreateEntryData>({ title: '', start: '', end: '', all_day: false, color: COLORS[0] })

  // Template drag-to-create popup
  const [templateModalOpen, setTemplateModalOpen] = useState(false)
  const [pendingTemplate, setPendingTemplate] = useState<{ template: EventTemplate; dateStr: string } | null>(null)
  const [templateFormValues, setTemplateFormValues] = useState<Record<string, string>>({})

  // Load templates — re-sync from localStorage on focus (Settings might have changed)
  const [templates, setTemplates] = useState<EventTemplate[]>(loadTemplates)
  useEffect(() => {
    const sync = () => setTemplates(loadTemplates())
    window.addEventListener('focus', sync)
    window.addEventListener('storage', sync)
    return () => {
      window.removeEventListener('focus', sync)
      window.removeEventListener('storage', sync)
    }
  }, [])

  const { data: rawEntries } = useQuery({
    queryKey: ['calendar-entries'],
    queryFn: () => calendarApi.list(),
    staleTime: 30_000,
  })

  // Handle both paginated ({results: []}) and plain array responses
  const entries: CalendarEntry[] = Array.isArray(rawEntries)
    ? rawEntries
    : (rawEntries as any)?.results ?? []

  const createMutation = useMutation({
    mutationFn: (data: CreateEntryData) => calendarApi.create(data),
    onSuccess: () => { toast.success('Evento criado.'); queryClient.invalidateQueries({ queryKey: ['calendar-entries'] }); closeModal() },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Erro ao criar evento.'),
  })

  const updateMutation = useMutation({
    mutationFn: (data: Partial<CreateEntryData>) => calendarApi.update(selectedEntry!.id, data),
    onSuccess: () => { toast.success('Evento atualizado.'); queryClient.invalidateQueries({ queryKey: ['calendar-entries'] }); closeModal() },
    onError: () => toast.error('Erro ao atualizar.'),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => calendarApi.delete(id),
    onSuccess: () => { toast.success('Evento excluído.'); queryClient.invalidateQueries({ queryKey: ['calendar-entries'] }); setDeleteTarget(null) },
    onError: () => toast.error('Erro ao excluir.'),
  })

  const moveMutation = useMutation({
    mutationFn: ({ id, start, end }: { id: number; start: string; end?: string }) => calendarApi.update(id, { start, end }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['calendar-entries'] }),
    onError: () => { toast.error('Erro ao mover evento.'); queryClient.invalidateQueries({ queryKey: ['calendar-entries'] }) },
  })

  const closeModal = () => {
    setModalOpen(false); setSelectedEntry(null)
    setForm({ title: '', start: '', end: '', all_day: false, color: COLORS[0] })
  }

  // Init FullCalendar Draggable for external templates
  useEffect(() => {
    if (!draggableContainerRef.current) return
    if (draggableInstance.current) {
      draggableInstance.current.destroy()
      draggableInstance.current = null
    }
    if (templates.length === 0) return

    draggableInstance.current = new Draggable(draggableContainerRef.current, {
      itemSelector: '.fc-draggable-event',
      eventData: (el) => ({
        title: el.getAttribute('data-title') ?? 'Novo Evento',
        color: el.getAttribute('data-color') ?? '#3b82f6',
        duration: { hours: 1 },
      }),
    })
    return () => {
      if (draggableInstance.current) {
        draggableInstance.current.destroy()
        draggableInstance.current = null
      }
    }
  }, [templates])

  const handleEventReceive = useCallback((arg: EventReceiveArg) => {
    // Revert the calendar preview — we handle creation manually
    arg.revert()

    const templateId = arg.draggedEl.getAttribute('data-template-id')
    const template = templates.find(t => t.id === templateId)
    if (!template) {
      // No required fields — create directly
      const dateStr = arg.event.startStr
      createMutation.mutate({
        title: arg.event.title,
        start: dateStr,
        all_day: true,
        color: arg.event.backgroundColor || COLORS[0],
      })
      return
    }

    const dateStr = arg.event.startStr
    setPendingTemplate({ template, dateStr })
    setTemplateFormValues({})
    setTemplateModalOpen(true)
  }, [templates, createMutation])

  const handleTemplateSubmit = async () => {
    if (!pendingTemplate) return
    const { template, dateStr } = pendingTemplate

    // Build description from filled fields
    const extraFields = Object.entries(templateFormValues)
      .filter(([, v]) => v)
      .map(([k, v]) => `${k}: ${v}`)
      .join(' | ')

    await createMutation.mutateAsync({
      title: template.name,
      start: dateStr,
      all_day: true,
      color: template.color,
      // description: extraFields — add if your model supports it
    })

    setTemplateModalOpen(false)
    setPendingTemplate(null)
  }

  const handleDateSelect = useCallback((arg: DateSelectArg) => {
    setSelectedEntry(null)
    setForm({ title: '', start: arg.startStr, end: arg.endStr ?? arg.startStr, all_day: arg.allDay, color: COLORS[0] })
    setModalOpen(true)
  }, [])

  const handleEventClick = useCallback((arg: EventClickArg) => {
    const entry = entries.find(e => String(e.id) === arg.event.id)
    if (!entry) return
    setSelectedEntry(entry)
    setForm({
      title: entry.title,
      start: entry.start,
      end: entry.end ?? entry.start,
      all_day: entry.all_day,
      color: entry.color,
    })
    setModalOpen(true)
  }, [entries])

  const handleEventDrop = useCallback((arg: EventDropArg) => {
    const entry = entries.find(e => String(e.id) === arg.event.id)
    if (!entry) { arg.revert(); return }
    moveMutation.mutate({
      id: entry.id,
      start: arg.event.startStr,
      end: arg.event.endStr || undefined,
    })
  }, [entries, moveMutation])

  const fcEvents = entries.map(e => ({
    id: String(e.id),
    title: e.title,
    start: e.start,
    end: e.end || undefined,
    allDay: e.all_day,
    backgroundColor: e.color,
    borderColor: e.color,
  }))

  return (
    <div className="page-enter flex flex-col" style={{ minHeight: 'calc(100vh - 120px)' }}>
      <PageHeader
        title="Agenda"
        subtitle="Calendário de eventos do escritório"
        breadcrumbs={[{ label: 'Agenda' }]}
        actions={
          <div className="flex gap-2">
            <Button
              variant="outline" size="sm"
              onClick={() => navigate('/app/configuracoes?tab=events')}
              className="gap-2 h-9"
            >
              <Settings size={14} /> Modelos
            </Button>
            <Button size="sm" className="gap-2 h-9"
              onClick={() => { setSelectedEntry(null); setForm({ title: '', start: '', end: '', all_day: false, color: COLORS[0] }); setModalOpen(true) }}
            >
              <Plus size={14} /> Novo Evento
            </Button>
          </div>
        }
      />

      <div className="flex gap-4 flex-1">
        {/* Calendar */}
        <div className="flex-1 min-w-0 bg-white rounded-xl border border-slate-200 p-4">
          <FullCalendar
            ref={calRef}
            plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin, listPlugin]}
            initialView="dayGridMonth"
            headerToolbar={{
              left: 'prev,next today',
              center: 'title',
              right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek',
            }}
            locale="pt-br"
            height={640}
            selectable
            editable
            droppable
            events={fcEvents}
            select={handleDateSelect}
            eventClick={handleEventClick}
            eventDrop={handleEventDrop}
            eventReceive={handleEventReceive}
            buttonText={{ today: 'Hoje', month: 'Mês', week: 'Semana', day: 'Dia', list: 'Lista' }}
          />
        </div>

        {/* Templates panel */}
        {templates.length > 0 && (
          <div ref={draggableContainerRef} className="w-48 flex-shrink-0">
            <div className="bg-white rounded-xl border border-slate-200 p-3">
              <p className="text-xs font-semibold text-slate-600 mb-3 uppercase tracking-wide">Modelos</p>
              <div className="flex flex-col gap-2">
                {templates.map((t) => (
                  <div
                    key={t.id}
                    data-template-id={t.id}
                    data-title={t.name}
                    data-color={t.color}
                    className="fc-draggable-event flex items-center gap-2 p-2.5 rounded-lg border border-slate-200 bg-white cursor-grab hover:shadow-sm hover:border-slate-300 transition-all text-xs select-none"
                  >
                    <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: t.color }} />
                    <span className="font-medium text-slate-700 truncate">{t.name}</span>
                  </div>
                ))}
              </div>
              <p className="text-[10px] text-slate-400 mt-3 text-center">Arraste para o calendário</p>
            </div>
          </div>
        )}
      </div>

      {/* Create/Edit event modal */}
      <Dialog open={modalOpen} onOpenChange={(o) => !o && closeModal()}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{selectedEntry ? 'Editar Evento' : 'Novo Evento'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label>Título</Label>
              <Input
                value={form.title}
                onChange={e => setForm(p => ({ ...p, title: e.target.value }))}
                placeholder="Nome do evento"
                className="mt-1"
                autoFocus
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Início</Label>
                <Input type="datetime-local" className="mt-1"
                  value={form.start ? form.start.slice(0, 16) : ''}
                  onChange={e => setForm(p => ({ ...p, start: e.target.value }))}
                />
              </div>
              <div>
                <Label>Fim</Label>
                <Input type="datetime-local" className="mt-1"
                  value={form.end ? form.end.slice(0, 16) : ''}
                  onChange={e => setForm(p => ({ ...p, end: e.target.value }))}
                />
              </div>
            </div>
            <div>
              <Label className="mb-2 block">Cor</Label>
              <div className="flex gap-2 flex-wrap">
                {COLORS.map(c => (
                  <button key={c} type="button"
                    className={cn('w-7 h-7 rounded-full transition-all border-2', form.color === c ? 'border-slate-900 scale-110' : 'border-transparent hover:scale-105')}
                    style={{ backgroundColor: c }}
                    onClick={() => setForm(p => ({ ...p, color: c }))}
                  />
                ))}
              </div>
            </div>
          </div>
          <DialogFooter className="gap-2">
            {selectedEntry && (
              <Button variant="destructive" size="sm" onClick={() => { closeModal(); setDeleteTarget(selectedEntry) }}>
                <Trash2 size={14} />
              </Button>
            )}
            <Button variant="outline" onClick={closeModal}>Cancelar</Button>
            <Button
              onClick={() => selectedEntry
                ? updateMutation.mutate({ title: form.title, start: form.start, end: form.end, all_day: form.all_day, color: form.color })
                : createMutation.mutate(form)
              }
              disabled={!form.title || !form.start}
            >
              {selectedEntry ? 'Salvar' : 'Criar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Template fill-in modal */}
      <Dialog open={templateModalOpen} onOpenChange={o => !o && (setTemplateModalOpen(false), setPendingTemplate(null))}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>{pendingTemplate?.template.name}</DialogTitle>
            {pendingTemplate?.template.description && (
              <p className="text-sm text-slate-500 mt-1">{pendingTemplate.template.description}</p>
            )}
          </DialogHeader>
          {pendingTemplate && pendingTemplate.template.requiredFields.length > 0 ? (
            <div className="space-y-3 py-2">
              <p className="text-xs text-slate-500">Preencha os campos para criar o evento em <strong>{pendingTemplate.dateStr.slice(0, 10)}</strong>:</p>
              {pendingTemplate.template.requiredFields.map(f => (
                <div key={f.id}>
                  <Label>{f.label}</Label>
                  <Input
                    className="mt-1"
                    value={templateFormValues[f.label] ?? ''}
                    onChange={e => setTemplateFormValues(p => ({ ...p, [f.label]: e.target.value }))}
                    placeholder={f.label}
                  />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-600 py-2">
              Criar evento <strong>{pendingTemplate?.template.name}</strong> em <strong>{pendingTemplate?.dateStr.slice(0, 10)}</strong>?
            </p>
          )}
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => { setTemplateModalOpen(false); setPendingTemplate(null) }}>Cancelar</Button>
            <Button onClick={handleTemplateSubmit} disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Criando...' : 'Criar Evento'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Excluir Evento"
        description={`Excluir "${deleteTarget?.title}"? Esta ação não pode ser desfeita.`}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}
