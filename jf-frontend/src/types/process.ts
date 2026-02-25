import type { PaginatedResponse } from './api'

export interface ProcessParty {
  id: number
  role: string
  customer: number | null
  name: string
  document: string
  email: string
  phone: string
  notes: string
}

export interface ProcessNote {
  id: number
  text: string
  is_private: boolean
  author: number
  author_name: string
  created_at: string
  updated_at: string
}

export interface NextDeadline {
  id: number
  title: string
  due_date: string
  priority: string
}

export interface Process {
  id: number
  // Identificação
  number: string
  court: string
  subject: string
  // Status
  phase: string
  status: string
  area: string
  // Dados jurídicos
  description: string
  cause_value: string | null
  filing_date: string | null
  distribution_date: string | null
  first_hearing_date: string | null
  sentence_date: string | null
  court_unit: string
  judge_name: string
  // Avaliação
  risk: string
  success_probability: number | null
  // Controle
  tags: string[]
  internal_notes: string
  next_action: string
  last_movement: string
  last_movement_date: string | null
  // Responsável
  responsible: number | null
  responsible_name: string | null
  // Nested
  parties: ProcessParty[]
  // Computed
  deadlines_count: number
  next_deadline: NextDeadline | null
  // Timestamps
  created_at: string
  updated_at: string
}

export type ProcessList = PaginatedResponse<Process>

export interface ProcessFilters {
  search?: string
  status?: string
  phase?: string
  area?: string
  page?: number
}

export interface CreateProcessData {
  number: string
  court?: string
  subject?: string
  phase?: string
  status?: string
  area?: string
  description?: string
  cause_value?: string | null
  filing_date?: string | null
  distribution_date?: string | null
  first_hearing_date?: string | null
  sentence_date?: string | null
  court_unit?: string
  judge_name?: string
  risk?: string
  success_probability?: number | null
  tags?: string[]
  internal_notes?: string
  next_action?: string
  last_movement?: string
  last_movement_date?: string | null
  responsible?: number | null
  parties?: Omit<ProcessParty, 'id'>[]
}
