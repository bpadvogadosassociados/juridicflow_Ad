import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

interface ProtectedRouteProps {
  requireOffice?: boolean
  permission?: string
}

export function ProtectedRoute({ requireOffice = true, permission }: ProtectedRouteProps) {
  const { accessToken, officeId, hasPermission } = useAuthStore()
  const location = useLocation()

  // Não autenticado → login
  if (!accessToken) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // Autenticado mas sem escritório selecionado
  if (requireOffice && !officeId) {
    return <Navigate to="/escolher-escritorio" replace />
  }

  // Sem a permissão necessária
  if (permission && !hasPermission(permission)) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-500">
        <span className="text-4xl">🔒</span>
        <p className="text-sm">Você não tem permissão para acessar esta página.</p>
      </div>
    )
  }

  return <Outlet />
}
