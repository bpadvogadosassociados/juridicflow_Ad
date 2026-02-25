import api from './client'
import type { LoginRequest, LoginResponse, User, Membership, PermissionsResponse } from '@/types/auth'

export const authApi = {
  login: (data: LoginRequest) =>
    api.post<LoginResponse>('/auth/login/', data).then((r) => r.data),

  refresh: (refresh: string) =>
    api.post<{ access: string; refresh: string }>('/auth/token/refresh/', { refresh }).then((r) => r.data),

  verify: (token: string) =>
    api.post('/auth/token/verify/', { token }),

  me: () =>
    api.get<User>('/auth/me/').then((r) => r.data),

  memberships: () =>
    api.get<Membership[]>('/auth/memberships/').then((r) => r.data),

  permissions: () =>
    api.get<PermissionsResponse>('/auth/permissions/').then((r) => r.data),
}
