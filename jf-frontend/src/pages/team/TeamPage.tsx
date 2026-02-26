import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Users, BarChart2, MessageSquare, PinIcon, Plus, Trash2,
  TrendingUp, CheckSquare, Clock, AlertCircle, Pin,
  ChevronRight, Crown,
} from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { PageHeader } from '@/components/layout/PageHeader'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { activityApi } from '@/api/activity'
import { teamApi } from '@/api/team_management'
import { initials, formatRelative } from '@/lib/utils'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const ROLE_LABELS: Record<string, string> = {
  org_admin:    'Admin da Organização',
  office_admin: 'Admin do Escritório',
  lawyer:       'Advogado',
  staff:        'Equipe',
  finance:      'Financeiro',
}

const ROLE_COLORS: Record<string, string> = {
  org_admin:    'bg-red-100 text-red-700',
  office_admin: 'bg-orange-100 text-orange-700',
  lawyer:       'bg-blue-100 text-blue-700',
  staff:        'bg-slate-100 text-slate-700',
  finance:      'bg-emerald-100 text-emerald-700',
}

// ── Mural (Pinboard) — stored in localStorage ────────────────────────────────

interface MuralPost {
  id: string
  type: 'aviso' | 'procedimento' | 'urgente' | 'info'
  title: string
  body: string
  author: string
  pinned: boolean
  created_at: string
}

function loadMural(): MuralPost[] {
  try { return JSON.parse(localStorage.getItem('jf-mural') ?? '[]') } catch { return [] }
}
function saveMural(posts: MuralPost[]) {
  localStorage.setItem('jf-mural', JSON.stringify(posts))
}

const POST_TYPE_STYLES: Record<string, string> = {
  aviso:        'border-l-4 border-blue-400 bg-blue-50',
  procedimento: 'border-l-4 border-violet-400 bg-violet-50',
  urgente:      'border-l-4 border-red-400 bg-red-50',
  info:         'border-l-4 border-slate-300 bg-slate-50',
}

// ── Tabs ─────────────────────────────────────────────────────────────────────

export function TeamPage() {
  const { membership } = useAuthStore()
  const canManage = membership?.role && ['org_admin', 'office_admin'].includes(membership.role)

  return (
    <div className="page-enter">
      <PageHeader
        title="Equipe"
        subtitle="Visão geral da equipe, desempenho e comunicação interna"
        breadcrumbs={[{ label: 'Equipe' }]}
      />

      <Tabs defaultValue="overview">
        <TabsList className="mb-6">
          <TabsTrigger value="overview" className="gap-2"><BarChart2 size={14} /> Visão Geral</TabsTrigger>
          <TabsTrigger value="members" className="gap-2"><Users size={14} /> Membros</TabsTrigger>
          <TabsTrigger value="mural" className="gap-2"><PinIcon size={14} /> Mural</TabsTrigger>
          <TabsTrigger value="metrics" className="gap-2"><TrendingUp size={14} /> Métricas</TabsTrigger>
        </TabsList>

        <TabsContent value="overview"><OverviewTab /></TabsContent>
        <TabsContent value="members"><MembersTab canManage={!!canManage} /></TabsContent>
        <TabsContent value="mural"><MuralTab /></TabsContent>
        <TabsContent value="metrics"><MetricsTab /></TabsContent>
      </Tabs>
    </div>
  )
}

// ── Overview Tab ──────────────────────────────────────────────────────────────

function OverviewTab() {
  const { data: summary } = useQuery({
    queryKey: ['activity-summary', '7d'],
    queryFn: () => activityApi.summary('7d'),
    staleTime: 60_000,
  })
  const { data: members = [] } = useQuery({
    queryKey: ['team-members'],
    queryFn: teamApi.listMembers,
    staleTime: 60_000,
  })

  return (
    <div className="space-y-6">
      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          icon={<Users size={18} className="text-blue-600" />}
          label="Membros ativos"
          value={members.length}
          color="bg-blue-50"
        />
        <KpiCard
          icon={<CheckSquare size={18} className="text-emerald-600" />}
          label="Tarefas concluídas (7d)"
          value={summary?.tasks.completed ?? 0}
          color="bg-emerald-50"
        />
        <KpiCard
          icon={<AlertCircle size={18} className="text-amber-600" />}
          label="Prazos vencidos"
          value={summary?.deadlines.missed ?? 0}
          color="bg-amber-50"
        />
        <KpiCard
          icon={<TrendingUp size={18} className="text-violet-600" />}
          label="Eventos (7d)"
          value={summary?.total ?? 0}
          color="bg-violet-50"
        />
      </div>

      {/* Atividade diária + top atores */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {summary && summary.daily.length > 1 && (
          <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-4">
            <p className="text-xs font-semibold text-slate-500 mb-4 uppercase tracking-wide">Atividade dos últimos 7 dias</p>
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={summary.daily} margin={{ left: -20, right: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={d => d.slice(5)} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
                <Bar dataKey="count" fill="#3b82f6" radius={[3,3,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Top atores */}
        {summary && summary.top_actors.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <p className="text-xs font-semibold text-slate-500 mb-3 uppercase tracking-wide">Mais ativos (7d)</p>
            <div className="space-y-2">
              {summary.top_actors.slice(0, 6).map((actor, i) => (
                <div key={actor.id} className="flex items-center gap-2">
                  <span className="text-xs text-slate-400 w-4 text-right">{i + 1}</span>
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-[9px] font-bold flex-shrink-0">
                    {initials(actor.name)}
                  </div>
                  <span className="text-xs text-slate-700 flex-1 truncate">{actor.name}</span>
                  <span className="text-xs font-semibold text-slate-500">{actor.count}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* By module breakdown */}
      {summary && summary.by_module.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs font-semibold text-slate-500 mb-4 uppercase tracking-wide">Atividade por módulo</p>
          <div className="space-y-2">
            {summary.by_module.slice(0, 8).map(m => {
              const pct = summary.total > 0 ? Math.round((m.count / summary.total) * 100) : 0
              const MODULE_LABELS: Record<string, string> = {
                processes: 'Processos', deadlines: 'Prazos', customers: 'Contatos',
                documents: 'Documentos', finance: 'Financeiro', tasks: 'Tarefas',
                kanban: 'Kanban', calendar: 'Agenda', team: 'Equipe', auth: 'Auth',
              }
              return (
                <div key={m.module} className="flex items-center gap-3">
                  <span className="text-xs text-slate-600 w-24 truncate">{MODULE_LABELS[m.module] ?? m.module}</span>
                  <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-xs text-slate-500 w-8 text-right">{m.count}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

function KpiCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: number; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 flex items-center gap-3">
      <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center', color)}>
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-800">{value}</p>
        <p className="text-xs text-slate-500">{label}</p>
      </div>
    </div>
  )
}

// ── Members Tab ───────────────────────────────────────────────────────────────

function MembersTab({ canManage }: { canManage: boolean }) {
  const queryClient = useQueryClient()
  const { data: members = [], isLoading } = useQuery({
    queryKey: ['team-members'],
    queryFn: teamApi.listMembers,
    staleTime: 30_000,
  })

  const [addOpen, setAddOpen] = useState(false)
  const [removeTarget, setRemoveTarget] = useState<number | null>(null)
  const [email, setEmail] = useState('')
  const [role, setRole] = useState('lawyer')

  const addMutation = useMutation({
    mutationFn: () => teamApi.addMember({ email, role }),
    onSuccess: () => {
      toast.success('Membro adicionado.')
      queryClient.invalidateQueries({ queryKey: ['team-members'] })
      setAddOpen(false); setEmail('')
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Erro ao adicionar membro.'),
  })

  const removeMutation = useMutation({
    mutationFn: (id: number) => teamApi.removeMember(id),
    onSuccess: () => {
      toast.success('Membro removido.')
      queryClient.invalidateQueries({ queryKey: ['team-members'] })
      setRemoveTarget(null)
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Erro ao remover.'),
  })

  return (
    <div>
      {canManage && (
        <div className="flex justify-end mb-4">
          <Button size="sm" onClick={() => setAddOpen(true)} className="gap-2 h-9">
            <Plus size={14} /> Adicionar Membro
          </Button>
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1,2,3].map(i => <div key={i} className="h-24 bg-slate-100 rounded-xl animate-pulse" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {members.map(member => (
            <div key={member.id} className="bg-white rounded-xl border border-slate-200 p-4 flex items-start gap-3 group">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
                {initials(member.full_name)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <p className="text-sm font-semibold text-slate-800 truncate">{member.full_name}</p>
                  {member.role === 'org_admin' && <Crown size={12} className="text-amber-500 flex-shrink-0" />}
                </div>
                <p className="text-xs text-slate-400 truncate">{member.email}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className={cn('text-[10px] font-semibold px-1.5 py-0.5 rounded-full', ROLE_COLORS[member.role] ?? 'bg-slate-100 text-slate-600')}>
                    {member.local_role_name ?? ROLE_LABELS[member.role] ?? member.role}
                  </span>
                </div>
              </div>
              {canManage && (
                <button
                  onClick={() => setRemoveTarget(member.id)}
                  className="opacity-0 group-hover:opacity-100 text-slate-300 hover:text-red-500 transition-all"
                >
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Add member dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader><DialogTitle>Adicionar Membro</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div>
              <Label>E-mail do usuário</Label>
              <Input
                className="mt-1"
                type="email"
                placeholder="email@escritorio.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                autoFocus
              />
            </div>
            <div>
              <Label>Função</Label>
              <Select value={role} onValueChange={setRole}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {Object.entries(ROLE_LABELS).map(([v, l]) => (
                    <SelectItem key={v} value={v}>{l}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setAddOpen(false)}>Cancelar</Button>
            <Button onClick={() => addMutation.mutate()} disabled={!email || addMutation.isPending}>
              {addMutation.isPending ? 'Adicionando...' : 'Adicionar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!removeTarget}
        title="Remover Membro"
        description="Remover este membro do escritório? A conta do usuário não será excluída."
        onConfirm={() => removeTarget && removeMutation.mutate(removeTarget)}
        onCancel={() => setRemoveTarget(null)}
      />
    </div>
  )
}

// ── Mural Tab ────────────────────────────────────────────────────────────────

function MuralTab() {
  const user = useAuthStore(s => s.user)
  const [posts, setPosts] = useState<MuralPost[]>(() => loadMural().sort((a, b) => {
    if (a.pinned && !b.pinned) return -1
    if (!a.pinned && b.pinned) return 1
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  }))
  const [createOpen, setCreateOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [form, setForm] = useState({ title: '', body: '', type: 'info' as MuralPost['type'], pinned: false })

  const save = (updated: MuralPost[]) => {
    const sorted = [...updated].sort((a, b) => {
      if (a.pinned && !b.pinned) return -1
      if (!a.pinned && b.pinned) return 1
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })
    saveMural(sorted); setPosts(sorted)
  }

  const handleCreate = () => {
    const post: MuralPost = {
      id: crypto.randomUUID(),
      ...form,
      author: user?.first_name ? `${user.first_name} ${user.last_name ?? ''}`.trim() : user?.email ?? 'Você',
      created_at: new Date().toISOString(),
    }
    save([...posts, post])
    setCreateOpen(false)
    setForm({ title: '', body: '', type: 'info', pinned: false })
  }

  const togglePin = (id: string) => {
    save(posts.map(p => p.id === id ? { ...p, pinned: !p.pinned } : p))
  }

  const TYPE_LABELS = { aviso: 'Aviso', procedimento: 'Procedimento', urgente: '🚨 Urgente', info: 'Info' }

  return (
    <div>
      <div className="flex justify-end mb-4">
        <Button size="sm" onClick={() => setCreateOpen(true)} className="gap-2 h-9">
          <Plus size={14} /> Novo Post
        </Button>
      </div>

      {posts.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <MessageSquare size={32} className="mx-auto mb-3 text-slate-300" />
          <p className="text-sm">Mural vazio</p>
          <p className="text-xs mt-1">Crie o primeiro aviso para a equipe</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {posts.map(post => (
            <div key={post.id} className={cn('rounded-xl p-4 relative group', POST_TYPE_STYLES[post.type])}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {post.pinned && <Pin size={12} className="text-slate-500 flex-shrink-0" />}
                    <h3 className="text-sm font-semibold text-slate-800">{post.title}</h3>
                    <span className="text-[10px] text-slate-500 ml-auto">{TYPE_LABELS[post.type]}</span>
                  </div>
                  <p className="text-sm text-slate-700 whitespace-pre-wrap">{post.body}</p>
                  <p className="text-xs text-slate-400 mt-2">{post.author} · {formatRelative(post.created_at)}</p>
                </div>
              </div>
              {/* Actions */}
              <div className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 flex gap-1 transition-opacity">
                <button onClick={() => togglePin(post.id)} className="p-1 rounded hover:bg-white/50 transition-colors" title={post.pinned ? 'Desafixar' : 'Fixar'}>
                  <Pin size={12} className={post.pinned ? 'text-slate-600' : 'text-slate-400'} />
                </button>
                <button onClick={() => setDeleteTarget(post.id)} className="p-1 rounded hover:bg-white/50 transition-colors">
                  <Trash2 size={12} className="text-red-400" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader><DialogTitle>Novo Post no Mural</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label>Tipo</Label>
                <Select value={form.type} onValueChange={v => setForm(p => ({ ...p, type: v as any }))}>
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="info">Info</SelectItem>
                    <SelectItem value="aviso">Aviso</SelectItem>
                    <SelectItem value="procedimento">Procedimento</SelectItem>
                    <SelectItem value="urgente">🚨 Urgente</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-end pb-0.5">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={form.pinned} onChange={e => setForm(p => ({ ...p, pinned: e.target.checked }))} />
                  <span className="text-sm text-slate-700">Fixar no topo</span>
                </label>
              </div>
            </div>
            <div>
              <Label>Título</Label>
              <Input className="mt-1" value={form.title} onChange={e => setForm(p => ({ ...p, title: e.target.value }))} placeholder="Título do aviso" autoFocus />
            </div>
            <div>
              <Label>Mensagem</Label>
              <Textarea className="mt-1" rows={4} value={form.body} onChange={e => setForm(p => ({ ...p, body: e.target.value }))} placeholder="Escreva o conteúdo..." />
            </div>
          </div>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancelar</Button>
            <Button onClick={handleCreate} disabled={!form.title || !form.body}>Publicar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!deleteTarget}
        title="Excluir Post"
        description="Remover este post do mural?"
        onConfirm={() => { if (deleteTarget) save(posts.filter(p => p.id !== deleteTarget)); setDeleteTarget(null) }}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}

// ── Metrics Tab ───────────────────────────────────────────────────────────────

function MetricsTab() {
  const [period, setPeriod] = useState('30d')

  const { data: summary, isLoading } = useQuery({
    queryKey: ['activity-summary', period],
    queryFn: () => activityApi.summary(period),
    staleTime: 60_000,
  })

  const PERIOD_OPTIONS = [
    { value: '7d',  label: '7 dias' },
    { value: '30d', label: '30 dias' },
    { value: '90d', label: '90 dias' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-700">Métricas de desempenho</p>
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-32 h-8 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PERIOD_OPTIONS.map(o => (
              <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1,2,3,4].map(i => <div key={i} className="h-32 bg-slate-100 rounded-xl animate-pulse" />)}
        </div>
      ) : summary ? (
        <>
          {/* Task throughput */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <p className="text-xs text-slate-500 mb-1">Tarefas criadas</p>
              <p className="text-3xl font-bold text-slate-800">{summary.tasks.created}</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <p className="text-xs text-slate-500 mb-1">Tarefas concluídas</p>
              <p className="text-3xl font-bold text-emerald-600">{summary.tasks.completed}</p>
              {summary.tasks.created > 0 && (
                <p className="text-xs text-slate-400 mt-1">
                  {Math.round((summary.tasks.completed / summary.tasks.created) * 100)}% de conclusão
                </p>
              )}
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <p className="text-xs text-slate-500 mb-1">Prazos perdidos</p>
              <p className={cn('text-3xl font-bold', summary.deadlines.missed > 0 ? 'text-red-600' : 'text-emerald-600')}>
                {summary.deadlines.missed}
              </p>
            </div>
          </div>

          {/* Top actors detailed */}
          {summary.top_actors.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <p className="text-xs font-semibold text-slate-500 mb-4 uppercase tracking-wide">Atividade individual</p>
              <div className="space-y-3">
                {summary.top_actors.map((actor, i) => {
                  const maxCount = summary.top_actors[0]?.count ?? 1
                  const pct = Math.round((actor.count / maxCount) * 100)
                  return (
                    <div key={actor.id} className="flex items-center gap-3">
                      <span className="text-xs text-slate-400 w-4 text-right">{i + 1}</span>
                      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-[10px] font-bold flex-shrink-0">
                        {initials(actor.name)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-medium text-slate-700 truncate">{actor.name}</span>
                          <span className="text-xs text-slate-500 ml-2 flex-shrink-0">{actor.count} ações</span>
                        </div>
                        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div className="h-full bg-blue-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* By action */}
          {summary.by_action.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <p className="text-xs font-semibold text-slate-500 mb-4 uppercase tracking-wide">Tipo de ações</p>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart
                  data={summary.by_action.slice(0, 8).map(a => ({
                    ...a,
                    label: a.action.replace('_', ' '),
                  }))}
                  layout="vertical"
                  margin={{ left: 20, right: 20, top: 0, bottom: 0 }}
                >
                  <XAxis type="number" tick={{ fontSize: 10 }} />
                  <YAxis dataKey="label" type="category" tick={{ fontSize: 10 }} width={80} />
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Bar dataKey="count" fill="#8b5cf6" radius={[0,3,3,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      ) : null}
    </div>
  )
}
