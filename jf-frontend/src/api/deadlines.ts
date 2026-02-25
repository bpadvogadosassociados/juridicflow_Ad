import api from './client'
import type { Deadline, DeadlineList, DeadlineFilters, CreateDeadlineData } from '@/types/deadline'

export const deadlinesApi = {
  list: (params: DeadlineFilters = {}) =>
    api.get<DeadlineList>('/deadlines/', { params }).then((r) => r.data),

  get: (id: number) =>
    api.get<Deadline>(`/deadlines/${id}/`).then((r) => r.data),

  create: (data: CreateDeadlineData) =>
    api.post<Deadline>('/deadlines/', data).then((r) => r.data),

  update: (id: number, data: Partial<CreateDeadlineData>) =>
    api.patch<Deadline>(`/deadlines/${id}/`, data).then((r) => r.data),

  delete: (id: number) =>
    api.delete(`/deadlines/${id}/`),
}
