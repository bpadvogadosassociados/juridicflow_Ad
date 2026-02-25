import type { PaginatedResponse } from './api'

export interface StatusInfo {
  label: 'overdue' | 'today' | 'soon' | 'future'
  text: string
  class: string
}

export interface RelatedProcess {
  id: number
  number: string
  subject: string
}

export interface Deadline {
  id: number
  title: string
  due_date: string
  type: string
  priority: string
  status: string
  description: string
  responsible: number | null
  responsible_name: string | null
  process_id?: number
  related_process: RelatedProcess | null
  status_info: StatusInfo
  created_at: string
  updated_at: string
}

export type DeadlineList = PaginatedResponse<Deadline>

export interface DeadlineFilters {
  status?: string
  priority?: string
  due_date_before?: string
  due_date_after?: string
  page?: number
}

export interface CreateDeadlineData {
  title: string
  due_date: string
  type?: string
  priority?: string
  status?: string
  description?: string
  responsible?: number | null
  process_id?: number | null
}
