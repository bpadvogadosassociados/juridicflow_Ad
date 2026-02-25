import api from './client'
import type { PaginatedResponse } from '@/types/api'

export interface Notification {
  id: number
  title: string
  message: string
  type: 'info' | 'warning' | 'success' | 'error' | 'deadline' | 'publication' | 'task'
  is_read: boolean
  url: string
  when: string
  created_at: string
}

export interface NotificationsListResponse {
  count?: number
  next?: string | null
  previous?: string | null
  results?: Notification[]
  unread_count?: number
  // Alguns endpoints retornam array direto
  [key: string]: unknown
}

export const notificationsApi = {
  list: () =>
    api.get<NotificationsListResponse>('/notifications/').then((r) => r.data),

  markRead: (id: number) =>
    api.post(`/notifications/${id}/read/`),

  markAllRead: () =>
    api.post('/notifications/read-all/'),
}
