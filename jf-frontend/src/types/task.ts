import type { PaginatedResponse } from './api'

export interface Task {
  id: number
  title: string
  description: string
  status: string
  priority: string
  assigned_to: number | null
  assigned_to_name: string | null
  due_date: string | null
  created_by: number | null
  created_by_name: string | null
  created_at: string
  updated_at: string
}

export type TaskList = PaginatedResponse<Task>

export interface CreateTaskData {
  title: string
  description?: string
  status?: string
  priority?: string
  assigned_to?: number | null
  due_date?: string | null
}
