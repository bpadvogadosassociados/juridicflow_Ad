import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { User, Building2, Bell, Shield, LogOut, Check, Settings2, Plus, Pencil, Trash2, UserPlus, ChevronRight, Users } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { PageHeader } from '@/components/layout/PageHeader'
import { useAuthStore } from '@/store/authStore'
import { authApi } from '@/api/auth'
import api from '@/api/client'
import { initials, cn } from '@/lib/utils'

// ── Permission helpers ─────────────────────────────────────────────────────
const MANAGE_TEAM_PERMS = [
  'memberships.add_membership',
  'memberships.change_membership',
  'memberships.delete_membership',
]

function useHasTeamManagePermission() {
  const { permissions } = useAuthStore()
  return MANAGE_TEAM_PERMS.some(p => permissions.includes(p))
}

// ── Tabs ──────────────────────────────────────────────────────────────────
const BASE_TABS = [
  { id: 'profile', label: 'Perfil', icon: User },
  { id: 'escritorio', label: 'Escritório', icon: Building2 },
  { id: 'events', label: 'Eventos', icon: Settings2 },
  { id: 'notifications', label: 'Notificações', icon: Bell },
  { id: 'integrations', label: 'Integrações', icon: Settings2 },
  { id: 'security', label: 'Segurança', icon: Shield },
]

// ── Event Templates (stored in localStorage for now) ─────────────────────
interface EventTemplate {
  id: string
  name: string
  description: string
  color: string
  requiredFields: { id: string; label: string }[]
}

const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#f97316', '#6366f1']

function loadTemplates(): EventTemplate[] {
  try {
    return JSON.parse(localStorage.getItem('jf-event-templates') ?? '[]')
  } catch { return [] }
}
function saveTemplates(t: EventTemplate[]) {
  localStorage.setItem('jf-event-templates', JSON.stringify(t))
}

// ── Role label map ────────────────────────────────────────────────────────
const ROLE_LABELS: Record<string, string> = {
  org_admin: 'Admin Org.',
  office_admin: 'Admin Escrit.',
  lawyer: 'Advogado',
  intern: 'Estagiário',
  finance: 'Financeiro',
}

// ─────────────────────────────────────────────────────────────────────────
export function SettingsPage() {
  const [activeTab, setActiveTab] = useState('profile')
  const { user, logout, memberships, officeId } = useAuthStore()
  const canManageTeam = useHasTeamManagePermission()

  const { data: meData, isLoading: meLoading } = useQuery({
    queryKey: ['me'],
    queryFn: () => authApi.me(),
    staleTime: 300_000,
  })

  const profileUser = meData ?? user
  const name = profileUser ? `${profileUser.first_name} ${profileUser.last_name}`.trim() || profileUser.email : '?'

  const handleLogout = () => {
    logout()
    window.location.href = '/login'
  }

  return (
    <div className="page-enter max-w-5xl">
      <PageHeader
        title="Configurações"
        subtitle="Gerencie sua conta e preferências"
        breadcrumbs={[{ label: 'JuridicFlow' }, { label: 'Configurações' }]}
      />

      <div className="flex gap-6">
        {/* Sidebar */}
        <aside className="w-52 flex-shrink-0">
          <nav className="space-y-0.5">
            {BASE_TABS.map(tab => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm transition-colors text-left',
                    activeTab === tab.id
                      ? 'bg-blue-50 text-blue-600 font-medium'
                      : 'text-slate-600 hover:bg-slate-100',
                  )}
                >
                  <Icon size={15} />
                  {tab.label}
                </button>
              )
            })}
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm text-red-500 hover:bg-red-50 transition-colors"
            >
              <LogOut size={15} /> Sair
            </button>
          </nav>
        </aside>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {activeTab === 'profile' && <ProfileTab user={profileUser} loading={meLoading} name={name} />}
          {activeTab === 'escritorio' && <OfficeTab canManage={canManageTeam} officeId={officeId} memberships={memberships} />}
          {activeTab === 'events' && <EventsTab />}
          {activeTab === 'notifications' && <NotificationsTab />}
          {activeTab === 'integrations' && <IntegrationsTab />}
          {activeTab === 'security' && <SecurityTab />}
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Profile Tab
// ═══════════════════════════════════════════════════════════════════════════
function ProfileTab({ user, loading, name }: { user: any; loading: boolean; name: string }) {
  if (loading) return <div className="animate-pulse space-y-3"><div className="h-16 w-16 rounded-full bg-slate-100" /><div className="h-8 bg-slate-100 rounded-lg" /></div>
  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Perfil</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-blue-600 flex items-center justify-center text-white text-xl font-semibold">
            {initials(name)}
          </div>
          <div>
            <p className="font-medium text-slate-900">{name}</p>
            <p className="text-sm text-slate-500">{user?.email}</p>
            {user?.is_staff && <Badge className="mt-1 bg-purple-100 text-purple-700 text-[10px]">Staff</Badge>}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 pt-2">
          {[
            { label: 'Nome', value: user?.first_name },
            { label: 'Sobrenome', value: user?.last_name },
            { label: 'E-mail', value: user?.email, className: 'col-span-2' },
          ].map(f => (
            <div key={f.label} className={cn('space-y-1', f.className)}>
              <Label className="text-xs text-slate-500">{f.label}</Label>
              <Input value={f.value ?? ''} readOnly className="bg-slate-50 text-sm" />
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-400">Para alterar seus dados, entre em contato com o administrador.</p>
      </CardContent>
    </Card>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Office Tab — two views based on permission
// ═══════════════════════════════════════════════════════════════════════════
interface OfficeMember {
  id: number
  user: { id: number; first_name: string; last_name: string; email: string }
  role: string
  is_active: boolean
}

interface LocalRole {
  id: number
  name: string
  description: string
  groups: { id: number; name: string }[]
}

function OfficeTab({ canManage, officeId, memberships }: { canManage: boolean; officeId: number | null; memberships: any[] }) {
  const currentMembership = memberships.find(m => m.office?.id === officeId)
  const officeName = currentMembership?.office?.name ?? 'Escritório atual'

  // Fetch office members (all members of the current office)
  const { data: officeMembers = [], isLoading: membersLoading } = useQuery<OfficeMember[]>({
    queryKey: ['office-members', officeId],
    queryFn: async () => {
      const r = await api.get('/auth/memberships/', { params: { office: officeId } })
      // If paginated
      const data = r.data
      return Array.isArray(data) ? data : (data.results ?? [])
    },
    enabled: !!officeId,
    staleTime: 60_000,
  })

  if (!officeId) return (
    <Card><CardContent className="py-8 text-center text-slate-400 text-sm">Nenhum escritório ativo selecionado.</CardContent></Card>
  )

  return canManage
    ? <OfficeAdminView officeId={officeId} officeName={officeName} members={officeMembers} loading={membersLoading} />
    : <OfficeMemberView officeName={officeName} members={officeMembers} loading={membersLoading} />
}

// Simple readonly view for non-admins
function OfficeMemberView({ officeName, members, loading }: { officeName: string; members: OfficeMember[]; loading: boolean }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Building2 size={16} className="text-slate-400" /> {officeName}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => <div key={i} className="h-12 bg-slate-100 rounded-lg animate-pulse" />)}
          </div>
        ) : members.length === 0 ? (
          <p className="text-sm text-slate-400 py-4 text-center">Nenhum membro encontrado.</p>
        ) : (
          <div className="space-y-2">
            {members.map(m => {
              const fullName = [m?.user?.first_name, m?.user?.last_name].filter(Boolean).join(' ') || m?.user?.email
              return (
                <div key={m.id} className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-slate-50">
                  <div className="w-9 h-9 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-semibold flex-shrink-0">
                    {initials(fullName)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800 truncate">{fullName}</p>
                    <p className="text-xs text-slate-400 truncate">{m?.user?.email}</p>
                  </div>
                  <Badge variant="outline" className="text-xs">
                    {ROLE_LABELS[m.role] ?? m.role}
                  </Badge>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Full admin view
function OfficeAdminView({ officeId, officeName, members, loading }: { officeId: number; officeName: string; members: OfficeMember[]; loading: boolean }) {
  const [activeSection, setActiveSection] = useState<'members' | 'roles'>('members')
  const [inviteOpen, setInviteOpen] = useState(false)
  const [roleOpen, setRoleOpen] = useState(false)
  const queryClient = useQueryClient()

  const deleteMemberMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/auth/memberships/${id}/`),
    onSuccess: () => { toast.success('Membro removido.'); queryClient.invalidateQueries({ queryKey: ['office-members', officeId] }) },
    onError: () => toast.error('Erro ao remover membro.'),
  })

  // Fetch available groups (permission groups from Django admin)
  const { data: availableGroups = [] } = useQuery({
    queryKey: ['permission-groups'],
    queryFn: async () => {
      const r = await api.get('/org/groups/')
      const data = r.data
      return Array.isArray(data) ? data : (data.results ?? [])
    },
    staleTime: 300_000,
  })

  // Fetch local roles for this office
  const { data: localRoles = [], isLoading: rolesLoading } = useQuery<LocalRole[]>({
    queryKey: ['local-roles', officeId],
    queryFn: async () => {
      const r = await api.get('/org/local-roles/', { params: { office: officeId } })
      const data = r.data
      return Array.isArray(data) ? data : (data.results ?? [])
    },
    enabled: !!officeId,
    staleTime: 60_000,
  })

  return (
    <div className="space-y-4">
      {/* Header with section tabs */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1 bg-slate-100 p-1 rounded-lg">
          <button onClick={() => setActiveSection('members')} className={cn('px-3 py-1.5 rounded-md text-xs font-medium transition-colors', activeSection === 'members' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700')}>
            <Users size={13} className="inline mr-1.5" />Membros
          </button>
          <button onClick={() => setActiveSection('roles')} className={cn('px-3 py-1.5 rounded-md text-xs font-medium transition-colors', activeSection === 'roles' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700')}>
            <Shield size={13} className="inline mr-1.5" />Funções
          </button>
        </div>
        {activeSection === 'members' && (
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700 gap-1.5 h-8 text-xs" onClick={() => setInviteOpen(true)}>
            <UserPlus size={13} /> Adicionar
          </Button>
        )}
        {activeSection === 'roles' && (
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700 gap-1.5 h-8 text-xs" onClick={() => setRoleOpen(true)}>
            <Plus size={13} /> Nova Função
          </Button>
        )}
      </div>

      {/* Members section */}
      {activeSection === 'members' && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold text-slate-700 flex items-center gap-2">
              <Building2 size={14} className="text-slate-400" /> {officeName} — Membros
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-2">{[1, 2, 3].map(i => <div key={i} className="h-12 bg-slate-100 rounded-lg animate-pulse" />)}</div>
            ) : members.length === 0 ? (
              <p className="text-sm text-slate-400 py-6 text-center">Nenhum membro neste escritório.</p>
            ) : (
              <div className="divide-y divide-slate-100">
                {members.map(m => {
                  const fullName = [m?.user?.first_name, m?.user?.last_name].filter(Boolean).join(' ') || m?.user?.email
                  return (
                    <div key={m.id} className="flex items-center gap-3 py-2.5 group">
                      <div className="w-9 h-9 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-semibold flex-shrink-0">
                        {initials(fullName)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-800 truncate">{fullName}</p>
                        <p className="text-xs text-slate-400 truncate">{m?.user?.email}</p>
                      </div>
                      <Badge variant="outline" className="text-xs">{ROLE_LABELS[m.role] ?? m.role}</Badge>
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button className="p-1 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-600">
                          <Pencil size={13} />
                        </button>
                        <button className="p-1 rounded hover:bg-red-50 text-slate-400 hover:text-red-500"
                          onClick={() => { if (confirm(`Remover ${fullName}?`)) deleteMemberMutation.mutate(m.id) }}>
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Roles section */}
      {activeSection === 'roles' && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold text-slate-700">Funções do Escritório</CardTitle>
            <p className="text-xs text-slate-400 mt-0.5">Crie funções usando os grupos de permissão configurados pelo administrador.</p>
          </CardHeader>
          <CardContent>
            {rolesLoading ? (
              <div className="space-y-2">{[1, 2].map(i => <div key={i} className="h-14 bg-slate-100 rounded-lg animate-pulse" />)}</div>
            ) : localRoles.length === 0 ? (
              <div className="text-center py-8">
                <Shield size={32} className="mx-auto text-slate-200 mb-2" />
                <p className="text-sm text-slate-400">Nenhuma função criada ainda.</p>
                <Button variant="outline" size="sm" className="mt-3 gap-1.5" onClick={() => setRoleOpen(true)}>
                  <Plus size={13} /> Criar primeira função
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {localRoles.map(r => (
                  <div key={r.id} className="flex items-center gap-3 p-3 rounded-lg border border-slate-200 group hover:border-slate-300 transition-colors">
                    <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                      <Shield size={14} className="text-indigo-600" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-800">{r.name}</p>
                      {r.description && <p className="text-xs text-slate-400 truncate">{r.description}</p>}
                      <div className="flex gap-1 mt-1 flex-wrap">
                        {r.groups.map(g => (
                          <span key={g.id} className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] bg-blue-50 text-blue-600 font-medium">
                            {g.name}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="p-1 rounded hover:bg-slate-100 text-slate-400"><Pencil size={13} /></button>
                      <button className="p-1 rounded hover:bg-red-50 text-slate-400 hover:text-red-500"><Trash2 size={13} /></button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Invite member modal */}
      <InviteMemberModal open={inviteOpen} onClose={() => setInviteOpen(false)} officeId={officeId} localRoles={localRoles} />
      {/* Create role modal */}
      <CreateRoleModal open={roleOpen} onClose={() => setRoleOpen(false)} officeId={officeId} availableGroups={availableGroups} />
    </div>
  )
}

function InviteMemberModal({ open, onClose, officeId, localRoles }: { open: boolean; onClose: () => void; officeId: number; localRoles: LocalRole[] }) {
  const queryClient = useQueryClient()
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('lawyer')
  const [localRoleId, setLocalRoleId] = useState<number | ''>('')

  const mutation = useMutation({
    mutationFn: () => api.post('/auth/memberships/', { email, office: officeId, role, local_role: localRoleId || undefined }),
    onSuccess: () => {
      toast.success('Membro adicionado.')
      queryClient.invalidateQueries({ queryKey: ['office-members', officeId] })
      onClose(); setEmail(''); setRole('lawyer'); setLocalRoleId('')
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Erro ao adicionar membro.'),
  })

  return (
    <Dialog open={open} onOpenChange={v => { if (!v) onClose() }}>
      <DialogContent className="max-w-sm">
        <DialogHeader><DialogTitle className="text-base">Adicionar Membro</DialogTitle></DialogHeader>
        <div className="space-y-3 py-1">
          <div className="space-y-1.5">
            <Label className="text-xs text-slate-600">E-mail do usuário *</Label>
            <Input value={email} onChange={e => setEmail(e.target.value)} placeholder="usuario@exemplo.com" className="text-sm" />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-slate-600">Função base</Label>
            <select value={role} onChange={e => setRole(e.target.value)} className="w-full text-sm rounded-md border border-slate-200 px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
              {Object.entries(ROLE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          {localRoles.length > 0 && (
            <div className="space-y-1.5">
              <Label className="text-xs text-slate-600">Função local (opcional)</Label>
              <select value={localRoleId} onChange={e => setLocalRoleId(e.target.value ? Number(e.target.value) : '')} className="w-full text-sm rounded-md border border-slate-200 px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="">— Sem função local —</option>
                {localRoles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
              </select>
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>Cancelar</Button>
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700" disabled={!email || mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending ? 'Adicionando…' : 'Adicionar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function CreateRoleModal({ open, onClose, officeId, availableGroups }: { open: boolean; onClose: () => void; officeId: number; availableGroups: any[] }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [selectedGroups, setSelectedGroups] = useState<number[]>([])

  const toggleGroup = (id: number) => setSelectedGroups(prev => prev.includes(id) ? prev.filter(g => g !== id) : [...prev, id])

  const mutation = useMutation({
    mutationFn: () => api.post('/org/local-roles/', { name, description, office: officeId, groups: selectedGroups }),
    onSuccess: () => {
      toast.success('Função criada.')
      queryClient.invalidateQueries({ queryKey: ['local-roles', officeId] })
      onClose(); setName(''); setDescription(''); setSelectedGroups([])
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Erro ao criar função.'),
  })

  return (
    <Dialog open={open} onOpenChange={v => { if (!v) onClose() }}>
      <DialogContent className="max-w-sm">
        <DialogHeader><DialogTitle className="text-base">Nova Função</DialogTitle></DialogHeader>
        <div className="space-y-3 py-1">
          <div className="space-y-1.5">
            <Label className="text-xs text-slate-600">Nome da função *</Label>
            <Input value={name} onChange={e => setName(e.target.value)} placeholder="Ex: Estagiário Jurídico" className="text-sm" />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-slate-600">Descrição (opcional)</Label>
            <Input value={description} onChange={e => setDescription(e.target.value)} placeholder="Breve descrição" className="text-sm" />
          </div>
          {availableGroups.length > 0 && (
            <div className="space-y-1.5">
              <Label className="text-xs text-slate-600">Grupos de permissão</Label>
              <div className="space-y-1 max-h-36 overflow-y-auto rounded-md border border-slate-200 p-2">
                {availableGroups.map((g: any) => (
                  <label key={g.id} className="flex items-center gap-2 py-1 px-1 rounded hover:bg-slate-50 cursor-pointer">
                    <input type="checkbox" checked={selectedGroups.includes(g.id)} onChange={() => toggleGroup(g.id)} className="accent-blue-600" />
                    <span className="text-xs text-slate-700">{g.name}</span>
                  </label>
                ))}
              </div>
              {availableGroups.length === 0 && <p className="text-xs text-slate-400">Nenhum grupo configurado pelo administrador.</p>}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>Cancelar</Button>
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700" disabled={!name || mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending ? 'Criando…' : 'Criar Função'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Events Tab — configure draggable event templates for calendar
// ═══════════════════════════════════════════════════════════════════════════
function EventsTab() {
  const [templates, setTemplates] = useState<EventTemplate[]>(loadTemplates)
  const [editTarget, setEditTarget] = useState<EventTemplate | null>(null)
  const [modalOpen, setModalOpen] = useState(false)

  const openNew = () => { setEditTarget(null); setModalOpen(true) }
  const openEdit = (t: EventTemplate) => { setEditTarget(t); setModalOpen(true) }
  const handleDelete = (id: string) => {
    const updated = templates.filter(t => t.id !== id)
    saveTemplates(updated); setTemplates(updated); toast.success('Evento removido.')
  }
  const handleSave = (t: EventTemplate) => {
    const updated = editTarget
      ? templates.map(x => x.id === t.id ? t : x)
      : [...templates, t]
    saveTemplates(updated); setTemplates(updated); setModalOpen(false); toast.success('Evento salvo.')
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">Modelos de Eventos</CardTitle>
              <p className="text-xs text-slate-400 mt-1">Crie modelos que aparecem na lateral da Agenda e podem ser arrastados para agendar.</p>
            </div>
            <Button size="sm" className="bg-blue-600 hover:bg-blue-700 gap-1.5 h-8 text-xs" onClick={openNew}>
              <Plus size={13} /> Novo Modelo
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {templates.length === 0 ? (
            <div className="text-center py-8">
              <Settings2 size={32} className="mx-auto text-slate-200 mb-2" />
              <p className="text-sm text-slate-400">Nenhum modelo criado.</p>
              <Button variant="outline" size="sm" className="mt-3 gap-1.5" onClick={openNew}>
                <Plus size={13} /> Criar primeiro modelo
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              {templates.map(t => (
                <div key={t.id} className="flex items-start gap-3 p-3 rounded-lg border border-slate-200 group hover:border-slate-300">
                  <div className="w-3 h-3 rounded-full mt-1 flex-shrink-0" style={{ backgroundColor: t.color }} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800">{t.name}</p>
                    {t.description && <p className="text-xs text-slate-400">{t.description}</p>}
                    {t.requiredFields.length > 0 && (
                      <p className="text-xs text-slate-400 mt-1">
                        Campos: {t.requiredFields.map(f => f.label).join(', ')}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button className="p-1 rounded hover:bg-slate-100 text-slate-400" onClick={() => openEdit(t)}><Pencil size={13} /></button>
                    <button className="p-1 rounded hover:bg-red-50 text-slate-400 hover:text-red-500" onClick={() => handleDelete(t.id)}><Trash2 size={13} /></button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
      <EventTemplateModal open={modalOpen} onClose={() => setModalOpen(false)} onSave={handleSave} template={editTarget} />
    </div>
  )
}

function EventTemplateModal({ open, onClose, onSave, template }: { open: boolean; onClose: () => void; onSave: (t: EventTemplate) => void; template: EventTemplate | null }) {
  const [name, setName] = useState(template?.name ?? '')
  const [description, setDescription] = useState(template?.description ?? '')
  const [color, setColor] = useState(template?.color ?? COLORS[0])
  const [fields, setFields] = useState<{ id: string; label: string }[]>(template?.requiredFields ?? [])

  // Sync when template changes
  useState(() => {
    setName(template?.name ?? '')
    setDescription(template?.description ?? '')
    setColor(template?.color ?? COLORS[0])
    setFields(template?.requiredFields ?? [])
  })

  const addField = () => setFields(f => [...f, { id: crypto.randomUUID(), label: '' }])
  const removeField = (id: string) => setFields(f => f.filter(x => x.id !== id))
  const updateField = (id: string, label: string) => setFields(f => f.map(x => x.id === id ? { ...x, label } : x))

  const handleSave = () => {
    onSave({
      id: template?.id ?? crypto.randomUUID(),
      name: name.trim(),
      description: description.slice(0, 60),
      color,
      requiredFields: fields.filter(f => f.label.trim()),
    })
  }

  return (
    <Dialog open={open} onOpenChange={v => { if (!v) onClose() }}>
      <DialogContent className="max-w-sm">
        <DialogHeader><DialogTitle className="text-base">{template ? 'Editar Modelo' : 'Novo Modelo'}</DialogTitle></DialogHeader>
        <div className="space-y-3 py-1">
          <div className="space-y-1.5">
            <Label className="text-xs text-slate-600">Nome *</Label>
            <Input value={name} onChange={e => setName(e.target.value)} placeholder="Ex: Audiência" className="text-sm" autoFocus />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-slate-600">Descrição curta <span className="text-slate-400">({description.length}/60)</span></Label>
            <Input value={description} onChange={e => setDescription(e.target.value.slice(0, 60))} placeholder="Breve descrição" className="text-sm" />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs text-slate-600">Cor</Label>
            <div className="flex gap-2 flex-wrap">
              {COLORS.map(c => (
                <button key={c} onClick={() => setColor(c)}
                  className={cn('w-6 h-6 rounded-full transition-transform', color === c ? 'ring-2 ring-offset-2 ring-blue-500 scale-110' : 'hover:scale-105')}
                  style={{ backgroundColor: c }} />
              ))}
            </div>
          </div>
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label className="text-xs text-slate-600">Campos obrigatórios</Label>
              <button onClick={addField} className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1">
                <Plus size={11} /> Adicionar
              </button>
            </div>
            {fields.length === 0 && <p className="text-xs text-slate-400">Nenhum campo extra. O evento só pedirá confirmação.</p>}
            <div className="space-y-1.5">
              {fields.map(f => (
                <div key={f.id} className="flex gap-2 items-center">
                  <Input value={f.label} onChange={e => updateField(f.id, e.target.value)} placeholder="Ex: Vara, Processo" className="text-xs h-8" />
                  <button onClick={() => removeField(f.id)} className="text-slate-400 hover:text-red-500 flex-shrink-0"><Trash2 size={13} /></button>
                </div>
              ))}
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={onClose}>Cancelar</Button>
          <Button size="sm" className="bg-blue-600 hover:bg-blue-700" disabled={!name.trim()} onClick={handleSave}>
            {template ? 'Atualizar' : 'Criar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Notifications Tab
// ═══════════════════════════════════════════════════════════════════════════
function NotificationsTab() {
  const [prefs, setPrefs] = useState({
    deadline_alerts: true, process_updates: true, financial_alerts: false,
    task_assignments: true, system_updates: false,
  })
  const toggle = (key: keyof typeof prefs) => setPrefs(p => ({ ...p, [key]: !p[key] }))
  const entries = [
    ['deadline_alerts', 'Alertas de prazos', 'Notifica quando um prazo está próximo ou venceu.'],
    ['process_updates', 'Atualizações de processos', 'Mudanças de status e movimentações.'],
    ['financial_alerts', 'Alertas financeiros', 'Faturas vencidas e recebimentos.'],
    ['task_assignments', 'Atribuição de tarefas', 'Quando uma tarefa é atribuída a você.'],
    ['system_updates', 'Atualizações do sistema', 'Novidades e manutenções.'],
  ] as [keyof typeof prefs, string, string][]
  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Notificações</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        {entries.map(([key, label, desc]) => (
          <div key={key} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
            <div>
              <p className="text-sm font-medium text-slate-700">{label}</p>
              <p className="text-xs text-slate-400">{desc}</p>
            </div>
            <button onClick={() => toggle(key)} className={cn('relative w-9 h-5 rounded-full transition-colors', prefs[key] ? 'bg-blue-600' : 'bg-slate-200')}>
              <span className={cn('absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform', prefs[key] && 'translate-x-4')} />
            </button>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Integrations Tab — coming soon
// ═══════════════════════════════════════════════════════════════════════════
function IntegrationsTab() {
  const items = [
    { name: 'WhatsApp Business', description: 'Envie e receba mensagens diretamente no JuridicFlow.', status: 'coming' },
    { name: 'E-mail / IMAP', description: 'Sincronize caixas de entrada com processos e contatos.', status: 'coming' },
    { name: 'Google Calendar', description: 'Sincronize prazos e agenda com Google Calendar.', status: 'coming' },
    { name: 'Tribunal Digital', description: 'Integração com sistemas de processos públicos.', status: 'coming' },
  ]
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Integrações</CardTitle>
        <p className="text-xs text-slate-400">Conecte o JuridicFlow com outras ferramentas.</p>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {items.map(item => (
            <div key={item.name} className="flex items-center gap-3 p-3 rounded-lg border border-slate-200 opacity-70">
              <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0">
                <Settings2 size={18} className="text-slate-400" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-700">{item.name}</p>
                <p className="text-xs text-slate-400">{item.description}</p>
              </div>
              <span className="text-[10px] px-2 py-1 bg-amber-50 text-amber-600 rounded-full font-medium">Em breve</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

// ═══════════════════════════════════════════════════════════════════════════
// Security Tab
// ═══════════════════════════════════════════════════════════════════════════
function SecurityTab() {
  const [form, setForm] = useState({ current: '', newPwd: '', confirm: '' })
  const [error, setError] = useState('')
  const handleSubmit = () => {
    if (form.newPwd.length < 8) { setError('Mínimo de 8 caracteres.'); return }
    if (form.newPwd !== form.confirm) { setError('Senhas não coincidem.'); return }
    setError('')
    toast.info('Alteração de senha será disponibilizada em breve.')
  }
  return (
    <Card>
      <CardHeader><CardTitle className="text-base">Segurança</CardTitle></CardHeader>
      <CardContent className="space-y-4 max-w-sm">
        {[
          { label: 'Senha atual', key: 'current', type: 'password' },
          { label: 'Nova senha', key: 'newPwd', type: 'password' },
          { label: 'Confirmar nova senha', key: 'confirm', type: 'password' },
        ].map(f => (
          <div key={f.key} className="space-y-1.5">
            <Label className="text-xs text-slate-600">{f.label}</Label>
            <Input type={f.type} value={(form as any)[f.key]} onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))} className="text-sm" />
          </div>
        ))}
        {error && <p className="text-xs text-red-500">{error}</p>}
        <Button size="sm" className="bg-blue-600 hover:bg-blue-700" onClick={handleSubmit}>Alterar Senha</Button>
      </CardContent>
    </Card>
  )
}
