import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { Building2, ArrowRight, Scale, CheckCircle2, LogOut } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { useAuthStore } from '@/store/authStore'
import { authApi } from '@/api/auth'
import { cn } from '@/lib/utils'
import { MEMBERSHIP_ROLE_LABELS } from '@/lib/constants'
import type { Membership } from '@/types/auth'

export function ChooseOfficePage() {
  const navigate = useNavigate()
  const { memberships, officeId, setOffice, setPermissions, logout } = useAuthStore()
  const [loading, setLoading] = useState<number | null>(null)

  const handleSelectOffice = async (membership: Membership) => {
    setLoading(membership.office.id)
    try {
      setOffice(membership.office.id)
      const { permissions } = await authApi.permissions()
      setPermissions(permissions)
      navigate('/app/dashboard', { replace: true })
    } catch {
      toast.error('Erro ao selecionar escritório. Tente novamente.')
    } finally {
      setLoading(null)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  // Agrupar por organização
  const grouped = memberships.reduce<Record<string, Membership[]>>((acc, m) => {
    const key = m.organization.name
    if (!acc[key]) acc[key] = []
    acc[key].push(m)
    return acc
  }, {})

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6">
      {/* Card container */}
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-2xl bg-blue-600 flex items-center justify-center mx-auto mb-4">
            <Scale size={22} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Selecione o escritório
          </h1>
          <p className="text-slate-500 text-sm mt-1.5">
            Escolha em qual escritório deseja trabalhar agora
          </p>
        </div>

        {/* Memberships grouped by org */}
        <div className="space-y-4">
          {Object.entries(grouped).map(([orgName, orgMemberships]) => (
            <div key={orgName} className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
              {/* Org header */}
              <div className="px-5 py-3 bg-slate-50 border-b border-slate-100">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  {orgName}
                </p>
              </div>

              {/* Offices */}
              <div className="divide-y divide-slate-50">
                {orgMemberships.map((m) => {
                  const isSelected = officeId === m.office.id
                  const isLoading = loading === m.office.id

                  return (
                    <button
                      key={m.id}
                      onClick={() => handleSelectOffice(m)}
                      disabled={isLoading || !!loading}
                      className={cn(
                        'w-full flex items-center gap-4 px-5 py-4 text-left transition-all',
                        'hover:bg-blue-50/50 active:bg-blue-50',
                        isSelected && 'bg-blue-50',
                        (isLoading || !!loading) && 'cursor-wait',
                      )}
                    >
                      {/* Icon */}
                      <div
                        className={cn(
                          'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0',
                          isSelected
                            ? 'bg-blue-600 text-white'
                            : 'bg-slate-100 text-slate-500',
                        )}
                      >
                        <Building2 size={18} />
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <p className={cn(
                          'text-sm font-semibold truncate',
                          isSelected ? 'text-blue-700' : 'text-slate-900',
                        )}>
                          {m.office.name}
                        </p>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {MEMBERSHIP_ROLE_LABELS[m.role] ?? m.role}
                        </p>
                      </div>

                      {/* Arrow / check */}
                      <div className="flex-shrink-0">
                        {isLoading ? (
                          <span className="w-4 h-4 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin block" />
                        ) : isSelected ? (
                          <CheckCircle2 size={18} className="text-blue-600" />
                        ) : (
                          <ArrowRight size={16} className="text-slate-400" />
                        )}
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Logout */}
        <div className="mt-6 text-center">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className="text-slate-400 hover:text-slate-600 gap-2"
          >
            <LogOut size={14} />
            Sair da conta
          </Button>
        </div>
      </div>
    </div>
  )
}
