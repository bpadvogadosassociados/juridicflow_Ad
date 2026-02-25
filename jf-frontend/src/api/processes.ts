import api from './client'
import type { Process, ProcessList, ProcessFilters, CreateProcessData, ProcessNote } from '@/types/process'

export const processesApi = {
  list: (params: ProcessFilters = {}) =>
    api.get<ProcessList>('/processes/', { params }).then((r) => r.data),

  get: (id: number) =>
    api.get<Process>(`/processes/${id}/`).then((r) => r.data),

  create: (data: CreateProcessData) =>
    api.post<Process>('/processes/', data).then((r) => r.data),

  update: (id: number, data: Partial<CreateProcessData>) =>
    api.patch<Process>(`/processes/${id}/`, data).then((r) => r.data),

  delete: (id: number) =>
    api.delete(`/processes/${id}/`),

  // Notas
  getNotes: (id: number) =>
    api.get<ProcessNote[]>(`/processes/${id}/notes/`).then((r) => r.data),

  addNote: (id: number, data: { text: string; is_private?: boolean }) =>
    api.post<ProcessNote>(`/processes/${id}/notes/`, data).then((r) => r.data),

  updateNote: (processId: number, noteId: number, data: Partial<ProcessNote>) =>
    api.patch<ProcessNote>(`/processes/${processId}/notes/${noteId}/`, data).then((r) => r.data),

  deleteNote: (processId: number, noteId: number) =>
    api.delete(`/processes/${processId}/notes/${noteId}/`),
}
