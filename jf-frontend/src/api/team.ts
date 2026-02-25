import api from './client'

export interface TeamMember {
  id: number
  user: {
    id: number
    email: string
    first_name: string
    last_name: string
    full_name: string
  }
  role: string
  is_active: boolean
}

export const teamApi = {
  members: () =>
    api.get<{ results: TeamMember[] }>('/team/members/').then((r) => r.data),
}
