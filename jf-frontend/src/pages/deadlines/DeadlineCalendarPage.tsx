import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import listPlugin from '@fullcalendar/list'
import interactionPlugin from '@fullcalendar/interaction'
import type { EventClickArg } from '@fullcalendar/core'
import { List } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/layout/PageHeader'
import { deadlinesApi } from '@/api/deadlines'
import { cn } from '@/lib/utils'

const PRIORITY_COLORS: Record<string, string> = {
  urgent: '#ef4444',
  high: '#f97316',
  medium: '#3b82f6',
  low: '#94a3b8',
}

const STATUS_COLORS: Record<string, string> = {
  overdue: '#ef4444',
  pending: '#3b82f6',
  completed: '#10b981',
  cancelled: '#94a3b8',
}

export function DeadlineCalendarPage() {
  const navigate = useNavigate()

  const { data, isLoading } = useQuery({
    queryKey: ['deadlines-calendar'],
    queryFn: () => deadlinesApi.list({ page: 1 }),
    staleTime: 60_000,
  })

  const deadlines = data?.results ?? []

  const fcEvents = deadlines.map(d => ({
    id: String(d.id),
    title: d.title,
    date: d.due_date,
    allDay: true,
    backgroundColor: STATUS_COLORS[d.status] ?? PRIORITY_COLORS[d.priority] ?? '#3b82f6',
    borderColor: STATUS_COLORS[d.status] ?? PRIORITY_COLORS[d.priority] ?? '#3b82f6',
    textColor: '#fff',
    extendedProps: { deadline: d },
  }))

  const handleEventClick = (arg: EventClickArg) => {
    navigate('/app/prazos')
  }

  return (
    <div className="page-enter flex flex-col h-full">
      <PageHeader
        title="Calendário de Prazos"
        subtitle={`${deadlines.length} prazo${deadlines.length !== 1 ? 's' : ''} visíveis`}
        breadcrumbs={[{ label: 'Prazos', href: '/app/prazos' }, { label: 'Calendário' }]}
        actions={
          <Button variant="outline" size="sm" onClick={() => navigate('/app/prazos')} className="gap-2 h-9">
            <List size={14} /> Ver Lista
          </Button>
        }
      />

      {/* Legend */}
      <div className="flex gap-4 mb-4">
        {[
          { label: 'Vencidos', color: '#ef4444' },
          { label: 'Pendentes', color: '#3b82f6' },
          { label: 'Concluídos', color: '#10b981' },
        ].map(({ label, color }) => (
          <div key={label} className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
            <span className="text-xs text-slate-500">{label}</span>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex-1 fc-wrapper">
        <style>{`
          .fc-wrapper .fc { font-family: inherit; }
          .fc-wrapper .fc-toolbar-title { font-size: 1rem; font-weight: 600; color: #1e293b; }
          .fc-wrapper .fc-button { background: white; border: 1px solid #e2e8f0; color: #475569; font-size: 0.75rem; padding: 4px 10px; border-radius: 8px; }
          .fc-wrapper .fc-button:hover { background: #f8fafc; }
          .fc-wrapper .fc-button-active, .fc-wrapper .fc-button-primary.fc-button-active { background: #2563eb !important; border-color: #2563eb !important; color: white !important; }
          .fc-wrapper .fc-event { border-radius: 6px; padding: 1px 5px; font-size: 0.72rem; cursor: pointer; }
          .fc-wrapper .fc-daygrid-day.fc-day-today { background: #eff6ff; }
          .fc-wrapper .fc-col-header-cell { font-size: 0.72rem; font-weight: 600; color: #64748b; text-transform: uppercase; padding: 8px 0; background: #f8fafc; }
          .fc-wrapper .fc-toolbar { padding: 12px 16px; border-bottom: 1px solid #f1f5f9; }
          .fc-wrapper .fc-list-event:hover td { background: #f8fafc; }
          .fc-wrapper .fc-list-day-cushion { background: #f8fafc; font-size: 0.75rem; }
        `}</style>
        <FullCalendar
          plugins={[dayGridPlugin, listPlugin, interactionPlugin]}
          initialView="dayGridMonth"
          locale="pt-br"
          height="100%"
          events={fcEvents}
          eventClick={handleEventClick}
          dayMaxEvents={4}
          headerToolbar={{
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,listMonth',
          }}
          buttonText={{ today: 'Hoje', month: 'Mês', list: 'Lista' }}
          noEventsText="Nenhum prazo neste período"
        />
      </div>
    </div>
  )
}
