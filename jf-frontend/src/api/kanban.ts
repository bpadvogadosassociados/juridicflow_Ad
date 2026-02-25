import api from './client'

export interface KanbanCard {
  id: number
  number: number
  title: string
  body_md: string
  order: number
  column: number
  created_by: number | null
  created_by_name: string | null
  created_at: string
}

export interface KanbanColumn {
  id: number
  title: string
  order: number
  cards: KanbanCard[]
}

export interface KanbanBoard {
  id: number
  title: string
  columns: KanbanColumn[]
}

export const kanbanApi = {
  getBoard: () =>
    api.get<KanbanBoard>('/kanban/board/').then((r) => r.data),

  createColumn: (data: { title: string; order?: number }) =>
    api.post<KanbanColumn>('/kanban/columns/', data).then((r) => r.data),

  updateColumn: (id: number, data: Partial<{ title: string; order: number }>) =>
    api.patch<KanbanColumn>(`/kanban/columns/${id}/`, data).then((r) => r.data),

  deleteColumn: (id: number) =>
    api.delete(`/kanban/columns/${id}/`),

  createCard: (data: { title: string; column: number; body_md?: string; order?: number }) =>
    api.post<KanbanCard>('/kanban/cards/', data).then((r) => r.data),

  updateCard: (id: number, data: Partial<{ title: string; body_md: string; column: number; order: number }>) =>
    api.patch<KanbanCard>(`/kanban/cards/${id}/`, data).then((r) => r.data),

  deleteCard: (id: number) =>
    api.delete(`/kanban/cards/${id}/`),
}
