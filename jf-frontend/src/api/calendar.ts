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

export const calendarApi = {
  list: (start?: string, end?: string) =>
    api.get<CalendarEntry[]>('/calendar/entries/', { params: { start, end } }).then(r => r.data),

  create: (data: CreateEntryData) =>
    api.post<CalendarEntry>('/calendar/entries/', data).then(r => r.data),

  update: (id: number, data: Partial<CreateEntryData>) =>
    api.patch<CalendarEntry>(`/calendar/entries/${id}/`, data).then(r => r.data),

  delete: (id: number) =>
    api.delete(`/calendar/entries/${id}/`),
}
