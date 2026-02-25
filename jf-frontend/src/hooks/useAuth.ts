import { useAuthStore } from '@/store/authStore'
import { authApi } from '@/api/auth'
import { useNavigate } from 'react-router-dom'

export function useAuth() {
  const store = useAuthStore()
  const navigate = useNavigate()

  const logout = () => {
    store.logout()
    navigate('/login', { replace: true })
  }

  return {
    user: store.user,
    officeId: store.officeId,
    memberships: store.memberships,
    permissions: store.permissions,
    isAuthenticated: store.isAuthenticated(),
    getFullName: store.getFullName,
    getCurrentMembership: store.getCurrentMembership,
    hasPermission: store.hasPermission,
    logout,
  }
}
