import { useQuery } from '@tanstack/react-query'
import { Users, Shield } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { PageHeader } from '@/components/layout/PageHeader'
import { useAuthStore } from '@/store/authStore'
import { initials, formatDate } from '@/lib/utils'
import { cn } from '@/lib/utils'
import api from '@/api/client'

// Membership records have: id, role, is_active, organization, office
interface OfficeMembership {
  id: number
  user: { id: number; email: string; first_name: string; last_name: string }
  role: string
  is_active: boolean
  office: { id: number; name: string }
}

const ROLE_LABELS: Record<string, string> = {
  org_admin: 'Admin Org.', office_admin: 'Admin Escritório', lawyer: 'Advogado',
  intern: 'Estagiário', finance: 'Financeiro',
}

const ROLE_COLORS: Record<string, string> = {
  org_admin: 'bg-violet-100 text-violet-700',
  office_admin: 'bg-blue-100 text-blue-700',
  lawyer: 'bg-emerald-100 text-emerald-700',
  intern: 'bg-amber-100 text-amber-700',
  finance: 'bg-slate-100 text-slate-600',
}

export function TeamListPage() {
  const navigate = useNavigate()
  const { officeId } = useAuthStore()

  // Use memberships endpoint — it returns the current user's memberships
  // For team view, we fetch all memberships for current office
  const { data: memberships, isLoading } = useQuery({
    queryKey: ['team-members', officeId],
    queryFn: () => api.get('/auth/memberships/').then(r => r.data as OfficeMembership[]),
    staleTime: 60_000,
  })

  const members = Array.isArray(memberships) ? memberships : []

  const fullName = (m: OfficeMembership) =>
    [m.user?.first_name, m.user?.last_name].filter(Boolean).join(' ') || m.user?.email || 'Usuário'

  return (
    <div className="max-w-5xl mx-auto page-enter">
      <PageHeader
        title="Equipe"
        subtitle={members.length ? `${members.length} membro${members.length !== 1 ? 's' : ''}` : undefined}
        breadcrumbs={[{ label: 'JuridicFlow' }, { label: 'Equipe' }]}
        actions={
          <Button variant="outline" size="sm" onClick={() => navigate('/app/equipe/funcoes')} className="gap-2 h-9">
            <Shield size={14} /> Funções e Permissões
          </Button>
        }
      />

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-28 bg-slate-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : members.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-400">
          <Users size={40} className="mb-3 opacity-30" />
          <p className="text-sm">Nenhum membro encontrado.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {members.map(member => {
            const name = fullName(member)
            return (
              <Card key={member.id} className="border-slate-200 shadow-sm hover:shadow-md transition-all">
                <CardContent className="p-4">
                  <div className="flex items-start gap-3 mb-3">
                    <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center font-bold text-sm flex-shrink-0">
                      {initials(name)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-slate-900 truncate">{name}</p>
                      <p className="text-[11px] text-slate-400 truncate">{member.user?.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className={cn(
                      'text-[10px] font-semibold px-2 py-0.5 rounded-md',
                      ROLE_COLORS[member.role] ?? 'bg-slate-100 text-slate-600',
                    )}>
                      {ROLE_LABELS[member.role] ?? member.role}
                    </span>
                    <span className={cn(
                      'text-[10px] px-1.5 py-0.5 rounded',
                      member.is_active ? 'text-emerald-600 bg-emerald-50' : 'text-slate-400 bg-slate-100',
                    )}>
                      {member.is_active ? 'Ativo' : 'Inativo'}
                    </span>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
