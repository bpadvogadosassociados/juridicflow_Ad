import api from './client'

// ─── Types ────────────────────────────────────────────────────────────────────

export type PublicationSource =
  | 'datajud' | 'comunica' | 'djen'
  | 'tjsp' | 'tjrj' | 'trf1' | 'trf2' | 'trf3' | 'trf4' | 'trf5'
  | 'manual' | 'other'

export type EventType =
  | 'citacao' | 'intimacao' | 'sentenca' | 'acordao'
  | 'decisao' | 'despacho' | 'juntada' | 'audiencia'
  | 'peticao' | 'edital' | 'movimento' | 'other'

export type EventStatus = 'new' | 'assigned' | 'in_progress' | 'resolved' | 'archived'
export type Urgency = 'critical' | 'urgent' | 'normal'

export interface UserMini {
  id: number
  email: string
  first_name: string
  last_name: string
  full_name: string
}

export interface JudicialEvent {
  id: number
  event_type: EventType
  event_type_display: string
  status: EventStatus
  status_display: string
  urgency: Urgency
  urgency_display: string
  publication: number
  process: number | null
  deadline: number | null
  assigned_to: UserMini | null
  // Campos derivados da publicação
  process_cnj: string
  publication_date: string
  source: PublicationSource
  source_display: string
  raw_text_preview: string
  publication_metadata: Record<string, any>
  // Workflow
  notes: string
  assigned_at: string | null
  resolved_at: string | null
  is_overdue: boolean
  days_until_deadline: number | null
  created_at: string
  updated_at: string
}

export interface FeedSummary {
  total: number
  new: number
  critical: number
  urgent: number
  overdue: number
  monitored_processes: number
}

export interface FeedResponse {
  results: JudicialEvent[]
  total: number
  page: number
  page_size: number
  has_more: boolean
  summary: FeedSummary
}

export interface ProcessMonitoring {
  id: number
  process: number
  process_number: string
  process_title: string
  process_cnj: string
  sources: string[]
  tribunal: string
  tribunal_index: string
  current_phase: string
  is_active: boolean
  autocomplete_enabled: boolean
  initial_sync_done: boolean
  last_synced_at: string | null
  recent_publications_count: number
  created_at: string
}

export interface PublicationRule {
  id: number
  event_type: EventType
  event_type_display: string
  description: string
  base_legal: string
  days: number
  business_days: boolean
  auto_create_deadline: boolean
  auto_urgency: Urgency
  is_active: boolean
  priority: number
}

export interface PublicationFilter {
  id: number
  filter_type: 'cnj' | 'oab' | 'cpf' | 'cnpj' | 'keyword'
  filter_type_display: string
  value: string
  description: string
  process: number | null
  is_active: boolean
  match_count: number
  last_matched_at: string | null
}

export interface PublicationImport {
  id: number
  source: PublicationSource
  source_display: string
  status: 'processing' | 'success' | 'partial' | 'failed'
  status_display: string
  reference_date: string | null
  total_found: number
  total_imported: number
  total_duplicates: number
  total_matched: number
  total_errors: number
  error_log: string
  summary: string
  success_rate: number
  duration_seconds: number | null
  started_at: string
  finished_at: string | null
  triggered_by: UserMini | null
}

export interface DataJudResult {
  found: boolean
  cnj_number: string
  tribunal: string
  tribunal_index: string
  classe: string
  assunto: string
  orgao_julgador: string
  data_ajuizamento: string
  fase_atual: string
  movimentos: Array<{
    data: string
    codigo: string
    nome: string
    complemento: string
  }>
  partes: Array<{
    polo: string
    nome: string
    tipo: string
    advogados: string[]
  }>
}

export interface FeedFilters {
  source?: string
  event_type?: string
  status?: string
  urgency?: string
  process?: number
  cnj?: string
  unread?: boolean
  date_from?: string
  date_to?: string
  q?: string
  page?: number
  page_size?: number
}

// ─── API ──────────────────────────────────────────────────────────────────────

const BASE = '/publications'

export const publicationsApi = {
  // Feed de andamentos
  getFeed: (filters: FeedFilters = {}) =>
    api.get<FeedResponse>(`${BASE}/feed/`, {
      params: { ...filters, unread: filters.unread ? 'true' : undefined },
    }).then(r => r.data),

  getEvent: (id: number) =>
    api.get<JudicialEvent>(`${BASE}/feed/${id}/`).then(r => r.data),

  updateEvent: (id: number, data: Partial<Pick<JudicialEvent, 'status' | 'urgency' | 'event_type' | 'notes'> & { assigned_to_id: number | null }>) =>
    api.patch<JudicialEvent>(`${BASE}/feed/${id}/`, data).then(r => r.data),

  markAllRead: () =>
    api.post<{ marked: number }>(`${BASE}/feed/mark-all-read/`).then(r => r.data),

  // Publicação manual
  createManual: (data: { raw_text: string; publication_date: string; source?: string; process_cnj?: string; process?: number }) =>
    api.post(`${BASE}/raw/`, data).then(r => r.data),

  // Monitoramento
  listMonitoring: (params?: { is_active?: boolean }) =>
    api.get<ProcessMonitoring[]>(`${BASE}/monitoring/`, { params }).then(r => r.data),

  createMonitoring: (data: { process: number; autocomplete_enabled?: boolean; sources?: string[] }) =>
    api.post<ProcessMonitoring>(`${BASE}/monitoring/`, data).then(r => r.data),

  updateMonitoring: (id: number, data: Partial<Pick<ProcessMonitoring, 'is_active' | 'autocomplete_enabled' | 'sources'>>) =>
    api.patch<ProcessMonitoring>(`${BASE}/monitoring/${id}/`, data).then(r => r.data),

  deleteMonitoring: (id: number) =>
    api.delete(`${BASE}/monitoring/${id}/`),

  syncProcess: (id: number) =>
    api.post<{ message: string; imported: number; skipped: number; errors: number }>(
      `${BASE}/monitoring/${id}/sync/`
    ).then(r => r.data),

  syncComunica: (date?: string) =>
    api.post<{ message: string; imported?: number }>(`${BASE}/sync-comunica/`, date ? { date } : {}).then(r => r.data),

  // DataJud lookup
  lookupDataJud: (number: string) =>
    api.get<DataJudResult>(`${BASE}/datajud/`, { params: { number } }).then(r => r.data),

  // Regras
  listRules: () =>
    api.get<PublicationRule[]>(`${BASE}/rules/`).then(r => r.data),

  createRule: (data: Omit<PublicationRule, 'id' | 'event_type_display' | 'urgency_display'>) =>
    api.post<PublicationRule>(`${BASE}/rules/`, data).then(r => r.data),

  updateRule: (id: number, data: Partial<PublicationRule>) =>
    api.patch<PublicationRule>(`${BASE}/rules/${id}/`, data).then(r => r.data),

  deleteRule: (id: number) =>
    api.delete(`${BASE}/rules/${id}/`),

  // Filtros de matching
  listFilters: () =>
    api.get<PublicationFilter[]>(`${BASE}/filters/`).then(r => r.data),

  createFilter: (data: Omit<PublicationFilter, 'id' | 'filter_type_display' | 'match_count' | 'last_matched_at'>) =>
    api.post<PublicationFilter>(`${BASE}/filters/`, data).then(r => r.data),

  updateFilter: (id: number, data: Partial<PublicationFilter>) =>
    api.patch<PublicationFilter>(`${BASE}/filters/${id}/`, data).then(r => r.data),

  deleteFilter: (id: number) =>
    api.delete(`${BASE}/filters/${id}/`),

  // Importações
  listImports: (params?: { source?: string; status?: string; limit?: number }) =>
    api.get<PublicationImport[]>(`${BASE}/imports/`, { params }).then(r => r.data),
}
