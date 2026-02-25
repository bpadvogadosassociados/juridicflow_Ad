import api from './client'

export interface CalendarEntry {
  id: number
  title: string
  start: string
  end: string | null
  all_day: boolean
  color: string
  created_by: number
  created_at: string
}

export interface CreateEntryData {
  title: string
  start: string
  end?: string | null
  all_day?: boolean
  color?: string
}

interface PaginatedCalendarEntries {
  count: number
  results: CalendarEntry[]
  next: string | null
  previous: string | null
}

export const calendarApi = {
  list: (start?: string, end?: string) =>
    api.get<PaginatedCalendarEntries | CalendarEntry[]>('/calendar/entries/', { params: { start, end } })
      .then(r => {
        // Handle both paginated and non-paginated responses
        const data = r.data as any
        if (data && typeof data === 'object' && 'results' in data) {
          return data.results as CalendarEntry[]
        }
        return data as CalendarEntry[]
      }),

  create: (data: CreateEntryData) =>
    api.post<CalendarEntry>('/calendar/entries/', data).then(r => r.data),

  update: (id: number, data: Partial<CreateEntryData>) =>
    api.patch<CalendarEntry>(`/calendar/entries/${id}/`, data).then(r => r.data),

  delete: (id: number) =>
    api.delete(`/calendar/entries/${id}/`),
}
