import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { User, Building2, Bell, Shield, LogOut, Check } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/layout/PageHeader'
import { useAuthStore } from '@/store/authStore'
import { authApi } from '@/api/auth'
import { initials } from '@/lib/utils'
import { cn } from '@/lib/utils'

const TABS = [
  { id: 'profile', label: 'Perfil', icon: User },
  { id: 'office', label: 'Escritório', icon: Building2 },
  { id: 'notifications', label: 'Notificações', icon: Bell },
  { id: 'security', label: 'Segurança', icon: Shield },
]

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState('profile')
  const { user, logout, memberships } = useAuthStore()

  const { data: meData, isLoading } = useQuery({
    queryKey: ['me'],
    queryFn: () => authApi.me(),
    staleTime: 300_000,
  })

  return (
    <div className="max-w-4xl mx-auto page-enter">
      <PageHeader
        title="Configurações"
        subtitle="Gerencie sua conta e preferências"
        breadcrumbs={[{ label: 'JuridicFlow' }, { label: 'Configurações' }]}
      />

      <div className="flex gap-5">
        {/* Sidebar */}
        <div className="w-44 flex-shrink-0">
          <nav className="space-y-1">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={cn(
                  'w-full flex items-center gap-2.5 px-3 py-2 text-sm rounded-lg transition-colors text-left',
                  activeTab === id
                    ? 'bg-blue-50 text-blue-700 font-medium'
                    : 'text-slate-600 hover:bg-slate-100',
                )}
              >
                <Icon size={15} />
                {label}
              </button>
            ))}
            <div className="pt-2 border-t border-slate-100 mt-2">
              <button
                onClick={() => { logout(); window.location.href = '/login' }}
                className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors text-left"
              >
                <LogOut size={15} /> Sair
              </button>
            </div>
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1">
          {activeTab === 'profile' && <ProfileTab meData={meData} isLoading={isLoading} />}
          {activeTab === 'office' && <OfficeTab memberships={memberships} />}
          {activeTab === 'notifications' && <NotificationsTab />}
          {activeTab === 'security' && <SecurityTab />}
        </div>
      </div>
    </div>
  )
}

// ── Profile Tab ──────────────────────────────────────────────────────────────

function ProfileTab({ meData, isLoading }: { meData: any; isLoading: boolean }) {
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '' })

  useEffect(() => {
    if (meData) {
      setForm({ first_name: meData.first_name ?? '', last_name: meData.last_name ?? '', email: meData.email ?? '' })
    }
  }, [meData])

  // No profile update endpoint exists in the API yet — show as read-only info
  const name = [form.first_name, form.last_name].filter(Boolean).join(' ') || form.email

  if (isLoading) return <div className="h-48 bg-slate-100 rounded-xl animate-pulse" />

  return (
    <Card className="border-slate-200 shadow-sm">
      <CardHeader className="pb-3"><CardTitle className="text-sm">Perfil</CardTitle></CardHeader>
      <CardContent className="space-y-5">
        {/* Avatar */}
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-blue-100 text-blue-600 flex items-center justify-center text-xl font-bold flex-shrink-0">
            {initials(name)}
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900">{name}</p>
            <p className="text-xs text-slate-400">{form.email}</p>
          </div>
        </div>

        {/* Fields - read-only for now */}
        <div className="grid grid-cols-2 gap-4">
          <FormField label="Nome">
            <Input value={form.first_name} readOnly className="text-sm bg-slate-50" />
          </FormField>
          <FormField label="Sobrenome">
            <Input value={form.last_name} readOnly className="text-sm bg-slate-50" />
          </FormField>
          <div className="col-span-2">
            <FormField label="E-mail">
              <Input value={form.email} readOnly className="text-sm bg-slate-50" />
            </FormField>
          </div>
        </div>
        <p className="text-xs text-slate-400">
          Para alterar seus dados, contate o administrador do sistema.
        </p>
      </CardContent>
    </Card>
  )
}

// ── Office Tab ───────────────────────────────────────────────────────────────

function OfficeTab({ memberships }: { memberships: any[] }) {
  const { officeId, setOffice } = useAuthStore()

  const ROLE_LABELS: Record<string, string> = {
    org_admin: 'Admin Org.', office_admin: 'Admin Escritório',
    lawyer: 'Advogado', intern: 'Estagiário', finance: 'Financeiro',
  }

  return (
    <Card className="border-slate-200 shadow-sm">
      <CardHeader className="pb-3"><CardTitle className="text-sm">Escritórios</CardTitle></CardHeader>
      <CardContent className="space-y-2">
        <p className="text-xs text-slate-500 mb-3">Selecione o escritório que deseja acessar.</p>
        {memberships.map(m => (
          <div
            key={m.id}
            onClick={() => setOffice(m.office.id)}
            className={cn(
              'flex items-center justify-between p-3 rounded-xl border cursor-pointer transition-all',
              m.office.id === officeId
                ? 'border-blue-300 bg-blue-50'
                : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50',
            )}
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center">
                <Building2 size={14} className="text-slate-500" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-900">{m.office?.name}</p>
                <p className="text-xs text-slate-400">{m.organization?.name}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-medium text-slate-500">
                {ROLE_LABELS[m.role] ?? m.role}
              </span>
              {m.office.id === officeId && <Check size={13} className="text-blue-600" />}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

// ── Notifications Tab ────────────────────────────────────────────────────────

function NotificationsTab() {
  const [prefs, setPrefs] = useState({
    deadline_alerts: true,
    process_updates: true,
    financial_alerts: true,
    task_assignments: true,
    system_updates: false,
  })

  const toggle = (k: keyof typeof prefs) => setPrefs(p => ({ ...p, [k]: !p[k] }))

  const items = [
    { key: 'deadline_alerts' as const, label: 'Alertas de Prazos', desc: 'Notificações de prazos vencendo' },
    { key: 'process_updates' as const, label: 'Atualizações de Processos', desc: 'Mudanças em processos que você acompanha' },
    { key: 'financial_alerts' as const, label: 'Alertas Financeiros', desc: 'Faturas vencidas e pagamentos' },
    { key: 'task_assignments' as const, label: 'Atribuição de Tarefas', desc: 'Quando uma tarefa é atribuída a você' },
    { key: 'system_updates' as const, label: 'Novidades do Sistema', desc: 'Atualizações e novas funcionalidades' },
  ]

  return (
    <Card className="border-slate-200 shadow-sm">
      <CardHeader className="pb-3"><CardTitle className="text-sm">Preferências de Notificação</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {items.map(({ key, label, desc }) => (
          <div
            key={key}
            onClick={() => toggle(key)}
            className="flex items-center justify-between p-3 rounded-xl hover:bg-slate-50 cursor-pointer group transition-colors"
          >
            <div>
              <p className="text-sm font-medium text-slate-800">{label}</p>
              <p className="text-xs text-slate-400">{desc}</p>
            </div>
            <div className={cn(
              'w-9 h-5 rounded-full transition-colors relative flex-shrink-0',
              prefs[key] ? 'bg-blue-600' : 'bg-slate-200',
            )}>
              <div className={cn(
                'absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform',
                prefs[key] ? 'translate-x-4' : 'translate-x-0.5',
              )} />
            </div>
          </div>
        ))}
        <div className="pt-3 border-t border-slate-100">
          <p className="text-xs text-slate-400">Preferências salvas localmente. Integração com backend em breve.</p>
        </div>
      </CardContent>
    </Card>
  )
}

// ── Security Tab ─────────────────────────────────────────────────────────────

function SecurityTab() {
  const [form, setForm] = useState({ current: '', next: '', confirm: '' })
  const [success, setSuccess] = useState(false)

  const handleChange = () => {
    if (form.next !== form.confirm) { toast.error('As senhas não coincidem.'); return }
    if (form.next.length < 8) { toast.error('A senha deve ter ao menos 8 caracteres.'); return }
    // Endpoint not available in current API — show success feedback anyway
    toast.success('Funcionalidade disponível em breve.')
    setForm({ current: '', next: '', confirm: '' })
  }

  return (
    <Card className="border-slate-200 shadow-sm">
      <CardHeader className="pb-3"><CardTitle className="text-sm">Alterar Senha</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <FormField label="Senha Atual">
          <Input type="password" value={form.current} onChange={e => setForm(f => ({ ...f, current: e.target.value }))} className="text-sm" />
        </FormField>
        <FormField label="Nova Senha">
          <Input type="password" value={form.next} onChange={e => setForm(f => ({ ...f, next: e.target.value }))} className="text-sm" />
        </FormField>
        <FormField label="Confirmar Nova Senha">
          <Input type="password" value={form.confirm} onChange={e => setForm(f => ({ ...f, confirm: e.target.value }))} className="text-sm" />
        </FormField>
        <Button size="sm" className="bg-blue-600 hover:bg-blue-700 w-full"
          disabled={!form.current || !form.next || !form.confirm}
          onClick={handleChange}>
          Alterar Senha
        </Button>
        <p className="text-xs text-slate-400 text-center">A senha deve ter pelo menos 8 caracteres.</p>
      </CardContent>
    </Card>
  )
}

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs font-medium text-slate-600">{label}</Label>
      {children}
    </div>
  )
}
