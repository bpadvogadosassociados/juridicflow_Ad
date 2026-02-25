import { Suspense, useEffect, useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { useUIStore } from '@/store/uiStore'
import { useAuthStore } from '@/store/authStore'
import { authApi } from '@/api/auth'
import { cn } from '@/lib/utils'

function PageLoadingFallback() {
  return (
    <div className="flex flex-col gap-4 p-6 animate-pulse">
      <div className="h-7 bg-slate-100 rounded-lg w-48" />
      <div className="h-4 bg-slate-100 rounded-lg w-72" />
      <div className="grid grid-cols-4 gap-4 mt-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 bg-slate-100 rounded-xl" />
        ))}
      </div>
      <div className="h-64 bg-slate-100 rounded-xl" />
    </div>
  )
}

function FullPageLoader() {
  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <div className="w-64 bg-slate-900 animate-pulse" />
      <div className="flex flex-col flex-1">
        <div className="h-16 bg-white border-b border-slate-200 animate-pulse" />
        <div className="flex-1 p-6">
          <PageLoadingFallback />
        </div>
      </div>
    </div>
  )
}

export function AppLayout() {
  const { sidebarCollapsed } = useUIStore()
  const { accessToken, officeId, user, memberships, setUser, setMemberships, setPermissions, logout } = useAuthStore()
  const navigate = useNavigate()
  const [hydrating, setHydrating] = useState(!user || memberships.length === 0)

  // Re-hidrata user/memberships/permissions ao carregar com token salvo mas sem dados
  useEffect(() => {
    if (!accessToken) return

    // Se já temos user e memberships no store (persistidos), só confirma permissões
    const doHydrate = async () => {
      try {
        // Garante que temos user
        if (!user) {
          const me = await authApi.me()
          setUser(me)
        }

        // Garante que temos memberships
        if (memberships.length === 0) {
          const mbs = await authApi.memberships()
          setMemberships(mbs)
        }

        // Sempre re-busca permissões ao entrar no layout (garantia de sync)
        if (officeId) {
          const { permissions } = await authApi.permissions()
          setPermissions(permissions)
        }
      } catch (err: any) {
        // Token inválido ou expirado sem refresh possível → logout
        if (err?.response?.status === 401) {
          logout()
          navigate('/login', { replace: true })
        }
        // 403 aqui significa que o officeId não é válido para este user
        // Redireciona para escolher escritório
        if (err?.response?.status === 403) {
          navigate('/escolher-escritorio', { replace: true })
        }
      } finally {
        setHydrating(false)
      }
    }

    doHydrate()
  // Roda apenas uma vez ao montar o layout
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (hydrating) return <FullPageLoader />

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Sidebar */}
      <Sidebar />

      {/* Main area */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Header />

        {/* Page content */}
        <main
          className={cn(
            'flex-1 overflow-auto',
            'transition-all duration-300',
          )}
        >
          <div className="p-6 min-h-full">
            <Suspense fallback={<PageLoadingFallback />}>
              <div className="page-enter">
                <Outlet />
              </div>
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  )
}
