import api from './client'

export interface DashboardData {
  processes: {
    total: number
    active: number
    suspended: number
    finished: number
  }
  deadlines: {
    overdue: number
    today: number
    this_week: number
    total_pending: number
  }
  finance: {
    receivable: string
    received_month: string
    pending_invoices: number
    expenses_month: string
  }
  customers: {
    total: number
    leads: number
    clients: number
  }
  recent_activity: Array<{
    verb: string
    description: string
    actor: string
    when: string
  }>
}

export const dashboardApi = {
  get: () => api.get<DashboardData>('/dashboard/').then((r) => r.data),
}
