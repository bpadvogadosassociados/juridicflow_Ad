import api from './client'

export interface ActivityEvent {
  id: number
  created_at: string
  actor: number | null
  actor_name: string
  actor_display: string
  module: string
  module_display: string
  action: string
  action_display: string
  entity_type: string
  entity_id: string
  entity_label: string
  summary: string
  changes: Record<string, { before: any; after: any }>
  ip_address: string | null
}

export interface ActivityListResponse {
  count: number
  next: string | null
  previous: string | null
  results: ActivityEvent[]
}

export interface ActivitySummary {
  period: string
  total: number
  by_module: { module: string; count: number }[]
  by_action: { action: string; count: number }[]
  top_actors: { id: number; name: string; count: number }[]
  daily: { date: string; count: number }[]
  tasks: { created: number; completed: number }
  deadlines: { completed_on_time: number; missed: number }
}

export const activityApi = {
  list: (params: Record<string, any> = {}) =>
    api.get<ActivityListResponse>('/activity/', { params }).then(r => r.data),

  detail: (id: number) =>
    api.get<ActivityEvent>(`/activity/${id}/`).then(r => r.data),

  summary: (period = '30d') =>
    api.get<ActivitySummary>('/activity/summary/', { params: { period } }).then(r => r.data),

  exportCsv: (params: Record<string, any> = {}) => {
    const qs = new URLSearchParams(params).toString()
    const token = localStorage.getItem('jf-auth-storage')
      ? JSON.parse(localStorage.getItem('jf-auth-storage')!).state?.accessToken
      : null
    // Open CSV download in new tab via direct URL
    window.open(`/api/activity/export/?${qs}`, '_blank')
  },
}
