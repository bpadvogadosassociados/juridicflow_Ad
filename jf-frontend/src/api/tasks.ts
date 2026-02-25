import api from './client'
import type { Task, TaskList, CreateTaskData } from '@/types/task'

export const tasksApi = {
  list: (params: Record<string, any> = {}) =>
    api.get<TaskList>('/tasks/', { params }).then(r => r.data),
  get: (id: number) =>
    api.get<Task>(`/tasks/${id}/`).then(r => r.data),
  create: (data: CreateTaskData) =>
    api.post<Task>('/tasks/', data).then(r => r.data),
  update: (id: number, data: Partial<CreateTaskData>) =>
    api.patch<Task>(`/tasks/${id}/`, data).then(r => r.data),
  delete: (id: number) =>
    api.delete(`/tasks/${id}/`),
}
