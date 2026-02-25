import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, Membership } from '@/types/auth'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
  memberships: Membership[]
  officeId: number | null
  permissions: string[]

  // Actions
  setTokens: (access: string, refresh: string) => void
  setUser: (user: User) => void
  setMemberships: (memberships: Membership[]) => void
  setOffice: (officeId: number) => void
  setPermissions: (permissions: string[]) => void
  logout: () => void

  // Helpers
  hasPermission: (permission: string) => boolean
  isAuthenticated: () => boolean
  getCurrentMembership: () => Membership | null
  getFullName: () => string
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      memberships: [],
      officeId: null,
      permissions: [],

      setTokens: (access, refresh) =>
        set({ accessToken: access, refreshToken: refresh }),

      setUser: (user) => set({ user }),

      setMemberships: (memberships) => set({ memberships }),

      setOffice: (officeId) => set({ officeId }),

      setPermissions: (permissions) => set({ permissions }),

      logout: () =>
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          memberships: [],
          officeId: null,
          permissions: [],
        }),

      hasPermission: (permission) => {
        const { permissions } = get()
        return permissions.includes(permission)
      },

      isAuthenticated: () => {
        return !!get().accessToken
      },

      getCurrentMembership: () => {
        const { memberships, officeId } = get()
        return memberships.find((m) => m.office.id === officeId) ?? null
      },

      getFullName: () => {
        const { user } = get()
        if (!user) return ''
        return `${user.first_name} ${user.last_name}`.trim() || user.email
      },
    }),
    {
      name: 'jf-auth',
      // Persiste tudo exceto as actions (functions não são serializáveis)
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        officeId: state.officeId,
        user: state.user,
        memberships: state.memberships,
        permissions: state.permissions,
      }),
    },
  ),
)
