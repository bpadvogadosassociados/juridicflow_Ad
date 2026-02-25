import { useState, useRef, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin, { Draggable } from '@fullcalendar/interaction'
import listPlugin from '@fullcalendar/list'
import type { DateSelectArg, EventClickArg, EventDropArg, EventReceiveArg } from '@fullcalendar/core'
import { Plus, X, Trash2, GripVertical } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { PageHeader } from '@/components/layout/PageHeader'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { calendarApi, type CalendarEntry, type CreateEntryData } from '@/api/calendar'
import { cn } from '@/lib/utils'

const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#f97316', '#6366f1']

// Event template from local storage (set via Settings > Eventos)
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

  const [templates] = useState<EventTemplate[]>(loadTemplates)

  const { data: entries = [] } = useQuery({
    queryKey: ['calendar-entries'],
    queryFn: () => calendarApi.list(),
    staleTime: 30_000,
  })

  const createMutation = useMutation({
    mutationFn: () => calendarApi.create(form),
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
    if (!draggableContainerRef.current || templates.length === 0) return
    if (draggableInstance.current) { draggableInstance.current.destroy() }
    draggableInstance.current = new Draggable(draggableContainerRef.current, {
      itemSelector: '.fc-draggable-event',
      eventData: (el) => ({
        title: el.getAttribute('data-title') ?? '',
        color: el.getAttribute('data-color') ?? '#3b82f6',
        duration: { hours: 1 },
        create: false, // we handle creation manually in eventReceive
      }),
    })
    return () => { draggableInstance.current?.destroy() }
  }, [templates])

  const handleEventReceive = useCallback((arg: EventReceiveArg) => {
    arg.revert()
    const templateId = arg.draggedEl.getAttribute('data-template-id')
    const template = templates.find(t => t.id === templateId)
    if (!template) return
    const dateStr = arg.event.startStr
    setPendingTemplate({ template, dateStr })
    setTemplateFormValues({})
    setTemplateModalOpen(true)
  }, [templates])

  const handleTemplateSubmit = async () => {
    if (!pendingTemplate) return
    const { template, dateStr } = pendingTemplate
    const desc = Object.entries(templateFormValues)
      .map(([k, v]) => `${k}: ${v}`).join(' | ')
    await calendarApi.create({
      title: template.name,
      start: dateStr,
      all_day: true,
      color: template.color,
    })
    queryClient.invalidateQueries({ queryKey: ['calendar-entries'] })
    toast.success('Evento criado.')
    setTemplateModalOpen(false)
    setPendingTemplate(null)
  }

  const handleDateSelect = useCallback((arg: DateSelectArg) => {
    setSelectedEntry(null)
    setForm({ title: '', start: arg.startStr, end: arg.endStr ?? arg.startStr, all_day: arg.allDay, color: COLORS[0] })
    setModalOpen(true)
  }, [])

  const handleEventClick = useCallback((arg: EventClickArg) => {
    const entry = (entries as CalendarEntry[]).find(e => String(e.id) === arg.event.id)
    if (!entry) return
    setSelectedEntry(entry)
    setForm({ title: entry.title, start: entry.start, end: entry.end ?? entry.start, all_day: entry.all_day, color: entry.color })
    setModalOpen(true)
  }, [entries])

  const handleEventDrop = useCallback((arg: EventDropArg) => {
    moveMutation.mutate({ id: Number(arg.event.id), start: arg.event.startStr, end: arg.event.endStr })
  }, [moveMutation])

  const fcEvents = (entries as CalendarEntry[]).map(e => ({
    id: String(e.id), title: e.title, start: e.start, end: e.end ?? undefined,
    allDay: e.all_day, backgroundColor: e.color, borderColor: e.color, textColor: '#fff',
  }))

  const isPending = createMutation.isPending || updateMutation.isPending
  const isEdit = !!selectedEntry

  return (
    <div className="page-enter">
      <PageHeader
        title="Agenda"
        subtitle="Eventos e compromissos do escritório"
        breadcrumbs={[{ label: 'JuridicFlow' }, { label: 'Agenda' }]}
        actions={
          <Button onClick={() => {
            const now = new Date()
            setForm({ title: '', start: now.toISOString().slice(0, 16), end: new Date(now.getTime() + 3600000).toISOString().slice(0, 16), all_day: false, color: COLORS[0] })
            setSelectedEntry(null); setModalOpen(true)
          }} className="bg-blue-600 hover:bg-blue-700 gap-2 h-9">
            <Plus size={15} /> Novo Evento
          </Button>
        }
      />

      <div className="flex gap-4">
        {/* Event templates panel */}
        {templates.length > 0 && (
          <div ref={draggableContainerRef} className="w-48 flex-shrink-0">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Arraste para agendar</p>
            <div className="space-y-2">
              {templates.map(t => (
                <div
                  key={t.id}
                  className="fc-draggable-event flex items-center gap-2 p-2.5 rounded-lg border border-slate-200 bg-white cursor-grab hover:shadow-sm hover:border-slate-300 transition-all text-xs"
                  data-title={t.name}
                  data-color={t.color}
                  data-template-id={t.id}
                >
                  <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: t.color }} />
                  <span className="font-medium text-slate-700 truncate">{t.name}</span>
                  <GripVertical size={12} className="text-slate-300 ml-auto flex-shrink-0" />
                </div>
              ))}
            </div>
            <p className="text-[10px] text-slate-400 mt-3 leading-tight">Configure em Configurações → Eventos</p>
          </div>
        )}

        {/* Calendar */}
        <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden fc-wrapper">
          <style>{`
            .fc-wrapper .fc { font-family: inherit; }
            .fc-wrapper .fc-toolbar-title { font-size: 1rem; font-weight: 600; color: #1e293b; }
            .fc-wrapper .fc-button { background: white; border: 1px solid #e2e8f0; color: #475569; font-size: 0.75rem; padding: 4px 10px; border-radius: 8px; transition: all 0.15s; }
            .fc-wrapper .fc-button:hover { background: #f8fafc; border-color: #cbd5e1; }
            .fc-wrapper .fc-button-primary:not(.fc-button-active):not(:disabled) { background: white; }
            .fc-wrapper .fc-button-active, .fc-wrapper .fc-button-primary.fc-button-active { background: #2563eb !important; border-color: #2563eb !important; color: white !important; }
            .fc-wrapper .fc-event { border-radius: 6px; padding: 1px 4px; font-size: 0.72rem; cursor: pointer; }
            .fc-wrapper .fc-daygrid-day:hover { background: #f8fafc; }
            .fc-wrapper .fc-daygrid-day.fc-day-today { background: #eff6ff; }
            .fc-wrapper .fc-col-header-cell { font-size: 0.72rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.04em; padding: 8px 0; background: #f8fafc; }
            .fc-wrapper .fc-toolbar { padding: 12px 16px; border-bottom: 1px solid #f1f5f9; }
            .fc-wrapper .fc-list-event:hover td { background: #f8fafc; }
            .fc-wrapper .fc-list-day-cushion { background: #f8fafc; font-size: 0.75rem; }
          `}</style>
          <FullCalendar
            ref={calRef}
            plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin, listPlugin]}
            initialView="dayGridMonth"
            locale="pt-br"
            height={650}
            events={fcEvents}
            editable={true}
            selectable={true}
            selectMirror={true}
            dayMaxEvents={3}
            droppable={templates.length > 0}
            select={handleDateSelect}
            eventClick={handleEventClick}
            eventDrop={handleEventDrop}
            eventReceive={handleEventReceive}
            headerToolbar={{
              left: 'prev,next today',
              center: 'title',
              right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek',
            }}
            buttonText={{ today: 'Hoje', month: 'Mês', week: 'Semana', day: 'Dia', list: 'Lista' }}
            noEventsText="Nenhum evento neste período"
          />
        </div>
      </div>

      {/* Event create/edit modal */}
      <Dialog open={modalOpen} onOpenChange={v => { if (!v) closeModal() }}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle className="text-base">{isEdit ? 'Editar Evento' : 'Novo Evento'}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-1">
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-slate-600">Título *</Label>
              <Input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="Ex: Audiência — Vara Cível" className="text-sm" autoFocus />
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" id="all_day" checked={form.all_day} onChange={e => setForm(f => ({ ...f, all_day: e.target.checked }))} className="w-3.5 h-3.5 accent-blue-600" />
              <label htmlFor="all_day" className="text-xs text-slate-600">Dia inteiro</label>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-slate-600">Início</Label>
                <Input type={form.all_day ? 'date' : 'datetime-local'} value={form.all_day ? form.start?.slice(0, 10) : form.start?.slice(0, 16)} onChange={e => setForm(f => ({ ...f, start: e.target.value }))} className="text-xs" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-slate-600">Fim</Label>
                <Input type={form.all_day ? 'date' : 'datetime-local'} value={form.all_day ? (form.end ?? '').slice(0, 10) : (form.end ?? '').slice(0, 16)} onChange={e => setForm(f => ({ ...f, end: e.target.value }))} className="text-xs" />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-slate-600">Cor</Label>
              <div className="flex gap-2 flex-wrap">
                {COLORS.map(color => (
                  <button key={color} onClick={() => setForm(f => ({ ...f, color }))}
                    className={cn('w-6 h-6 rounded-full transition-transform', form.color === color ? 'ring-2 ring-offset-2 ring-blue-500 scale-110' : 'hover:scale-105')}
                    style={{ backgroundColor: color }} />
                ))}
              </div>
            </div>
          </div>
          <DialogFooter className="gap-2">
            {isEdit && (
              <Button variant="outline" size="sm" className="text-red-600 border-red-200 hover:bg-red-50 mr-auto"
                onClick={() => { setDeleteTarget(selectedEntry); setModalOpen(false) }}>
                <Trash2 size={13} className="mr-1" /> Excluir
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={closeModal} disabled={isPending}>Cancelar</Button>
            <Button size="sm" className="bg-blue-600 hover:bg-blue-700" disabled={!form.title || !form.start || isPending}
              onClick={() => isEdit
                ? updateMutation.mutate({ title: form.title, start: form.start, end: form.end, all_day: form.all_day, color: form.color })
                : createMutation.mutate()
              }>
              {isPending ? 'Salvando…' : isEdit ? 'Atualizar' : 'Criar Evento'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Template drop modal */}
      <Dialog open={templateModalOpen} onOpenChange={v => { if (!v) { setTemplateModalOpen(false); setPendingTemplate(null) } }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-base flex items-center gap-2">
              {pendingTemplate && (
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: pendingTemplate.template.color }} />
              )}
              {pendingTemplate?.template.name}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-1">
            {pendingTemplate?.template.description && (
              <p className="text-xs text-slate-500">{pendingTemplate.template.description}</p>
            )}
            <div className="space-y-1.5">
              <Label className="text-xs font-medium text-slate-600">Data</Label>
              <p className="text-sm text-slate-700">{pendingTemplate?.dateStr.slice(0, 10)}</p>
            </div>
            {pendingTemplate?.template.requiredFields.map(field => (
              <div key={field.id} className="space-y-1.5">
                <Label className="text-xs font-medium text-slate-600">{field.label} *</Label>
                <Input
                  value={templateFormValues[field.id] ?? ''}
                  onChange={e => setTemplateFormValues(v => ({ ...v, [field.id]: e.target.value }))}
                  className="text-sm"
                />
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => { setTemplateModalOpen(false); setPendingTemplate(null) }}>Cancelar</Button>
            <Button size="sm" className="bg-blue-600 hover:bg-blue-700" onClick={handleTemplateSubmit}>
              Confirmar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={v => { if (!v) setDeleteTarget(null) }}
        title="Excluir evento?"
        description={`"${deleteTarget?.title}" será excluído.`}
        confirmLabel="Excluir"
        variant="destructive"
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        loading={deleteMutation.isPending}
      />
    </div>
  )
}
