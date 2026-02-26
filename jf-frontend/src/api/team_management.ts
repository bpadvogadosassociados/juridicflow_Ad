import api from './client'

export interface TeamMember {
  id: number
  user_id: number
  full_name: string
  email: string
  role: string
  local_role: number | null
  local_role_name: string | null
  groups_ids: number[]
  is_active: boolean
  created_at: string
}

export interface LocalRole {
  id: number
  name: string
  description: string
  groups_ids: number[]
  is_active: boolean
}

export interface PermissionGroup {
  id: number
  name: string
  description: string
}

export const teamApi = {
  // Members
  listMembers: () =>
    api.get<TeamMember[]>('/team/members/').then(r => r.data),

  addMember: (data: { email: string; role: string; local_role?: number | null }) =>
    api.post<TeamMember>('/team/members/', data).then(r => r.data),

  updateMember: (id: number, data: Partial<{ role: string; local_role: number | null; groups: number[] }>) =>
    api.patch<TeamMember>(`/team/members/${id}/`, data).then(r => r.data),

  removeMember: (id: number) =>
    api.delete(`/team/members/${id}/`),

  // Local Roles
  listLocalRoles: () =>
    api.get<LocalRole[]>('/team/local-roles/').then(r => r.data),

  createLocalRole: (data: { name: string; description?: string; groups?: number[] }) =>
    api.post<LocalRole>('/team/local-roles/', data).then(r => r.data),

  updateLocalRole: (id: number, data: Partial<{ name: string; description: string; groups: number[] }>) =>
    api.patch<LocalRole>(`/team/local-roles/${id}/`, data).then(r => r.data),

  deleteLocalRole: (id: number) =>
    api.delete(`/team/local-roles/${id}/`),

  // Permission Groups
  listGroups: () =>
    api.get<PermissionGroup[]>('/team/groups/').then(r => r.data),
}
