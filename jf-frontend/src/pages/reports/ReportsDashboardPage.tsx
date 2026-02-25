import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  Scale, Users, Clock, DollarSign,
  TrendingUp, TrendingDown, AlertTriangle, CheckCircle2, ArrowRight,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/layout/PageHeader'
import api from '@/api/client'
import { formatCurrency } from '@/lib/utils'
import { cn } from '@/lib/utils'

interface DashboardData {
  processes: { total: number; active: number; suspended: number; finished: number }
  deadlines: { overdue: number; today: number; this_week: number; total_pending: number }
  finance: { receivable: string; received_month: string; pending_invoices: number; expenses_month: string }
  customers: { total: number; leads: number; clients: number }
  recent_activity: { verb: string; description: string; actor: string; when: string }[]
}

export function ReportsDashboardPage() {
  const navigate = useNavigate()

  const { data, isLoading } = useQuery<DashboardData>({
    queryKey: ['reports-dashboard'],
    queryFn: () => api.get('/dashboard/').then(r => r.data),
    staleTime: 60_000,
  })

  return (
    <div className="max-w-7xl mx-auto page-enter">
      <PageHeader
        title="Relatórios"
        subtitle="Visão geral operacional do escritório"
        breadcrumbs={[{ label: 'JuridicFlow' }, { label: 'Relatórios' }]}
      />

      {/* ── Processes ── */}
      <Section title="Processos" icon={<Scale size={14} className="text-blue-500" />} onMore={() => navigate('/app/processos')}>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Total', value: data?.processes.total, color: 'text-slate-800' },
            { label: 'Ativos', value: data?.processes.active, color: 'text-blue-600' },
            { label: 'Suspensos', value: data?.processes.suspended, color: 'text-amber-600' },
            { label: 'Finalizados', value: data?.processes.finished, color: 'text-emerald-600' },
          ].map(stat => (
            <StatCard key={stat.label} label={stat.label} value={stat.value} color={stat.color} loading={isLoading} />
          ))}
        </div>
      </Section>

      {/* ── Deadlines ── */}
      <Section title="Prazos" icon={<Clock size={14} className="text-amber-500" />} onMore={() => navigate('/app/prazos')}>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Vencidos', value: data?.deadlines.overdue, color: 'text-red-600', alert: (data?.deadlines.overdue ?? 0) > 0 },
            { label: 'Hoje', value: data?.deadlines.today, color: 'text-amber-600' },
            { label: 'Esta semana', value: data?.deadlines.this_week, color: 'text-blue-600' },
            { label: 'Total pendente', value: data?.deadlines.total_pending, color: 'text-slate-700' },
          ].map(stat => (
            <StatCard key={stat.label} label={stat.label} value={stat.value} color={stat.color} loading={isLoading} alert={stat.alert} />
          ))}
        </div>
      </Section>

      {/* ── Finance ── */}
      <Section title="Financeiro" icon={<DollarSign size={14} className="text-emerald-500" />} onMore={() => navigate('/app/financeiro')}>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'A Receber', value: data?.finance.receivable ? formatCurrency(data.finance.receivable) : undefined, isMonetary: true },
            { label: 'Recebido (mês)', value: data?.finance.received_month ? formatCurrency(data.finance.received_month) : undefined, isMonetary: true, positive: true },
            { label: 'Despesas (mês)', value: data?.finance.expenses_month ? formatCurrency(data.finance.expenses_month) : undefined, isMonetary: true, negative: true },
            { label: 'Fat. Pendentes', value: data?.finance.pending_invoices, alert: (data?.finance.pending_invoices ?? 0) > 0 },
          ].map(stat => (
            <StatCard
              key={stat.label}
              label={stat.label}
              value={stat.value}
              loading={isLoading}
              alert={stat.alert}
              color={stat.positive ? 'text-emerald-600' : stat.negative ? 'text-red-500' : 'text-slate-800'}
            />
          ))}
        </div>
      </Section>

      {/* ── Customers ── */}
      <Section title="Contatos" icon={<Users size={14} className="text-violet-500" />} onMore={() => navigate('/app/contatos')}>
        <div className="grid grid-cols-3 gap-3 max-w-lg">
          {[
            { label: 'Total', value: data?.customers.total, color: 'text-slate-800' },
            { label: 'Leads', value: data?.customers.leads, color: 'text-amber-600' },
            { label: 'Clientes', value: data?.customers.clients, color: 'text-emerald-600' },
          ].map(stat => (
            <StatCard key={stat.label} label={stat.label} value={stat.value} color={stat.color} loading={isLoading} />
          ))}
        </div>
      </Section>

      {/* ── Recent Activity ── */}
      <Section title="Atividade Recente" icon={<CheckCircle2 size={14} className="text-slate-400" />}>
        <div className="space-y-2">
          {isLoading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-10 bg-slate-100 rounded-lg animate-pulse" />
            ))
          ) : !data?.recent_activity?.length ? (
            <p className="text-xs text-slate-400 py-4 text-center">Nenhuma atividade recente.</p>
          ) : (
            data.recent_activity.map((a, i) => (
              <div key={i} className="flex items-start gap-3 py-2 border-b border-slate-50 last:border-0">
                <div className="w-5 h-5 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-slate-700">
                    <span className="font-medium">{a.actor}</span> {a.verb}
                    {a.description && <span className="text-slate-400"> — {a.description}</span>}
                  </p>
                </div>
                <span className="text-[10px] text-slate-400 flex-shrink-0">{a.when}</span>
              </div>
            ))
          )}
        </div>
      </Section>
    </div>
  )
}

function Section({ title, icon, children, onMore }: {
  title: string; icon: React.ReactNode; children: React.ReactNode; onMore?: () => void
}) {
  return (
    <Card className="border-slate-200 shadow-sm mb-5">
      <CardHeader className="pb-3 flex-row items-center justify-between">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          {icon} {title}
        </CardTitle>
        {onMore && (
          <button
            onClick={onMore}
            className="text-[11px] text-blue-600 hover:underline flex items-center gap-1"
          >
            Ver tudo <ArrowRight size={11} />
          </button>
        )}
      </CardHeader>
      <CardContent className="px-4 pb-4">{children}</CardContent>
    </Card>
  )
}

function StatCard({ label, value, color = 'text-slate-800', loading, alert }: {
  label: string; value: string | number | undefined; color?: string; loading?: boolean; alert?: boolean
}) {
  return (
    <div className={cn(
      'bg-white border rounded-xl p-3 relative',
      alert ? 'border-red-200 bg-red-50/50' : 'border-slate-100',
    )}>
      {loading ? (
        <div className="space-y-1.5 animate-pulse">
          <div className="h-5 bg-slate-100 rounded w-12" />
          <div className="h-3 bg-slate-50 rounded w-16" />
        </div>
      ) : (
        <>
          {alert && <AlertTriangle size={10} className="absolute top-2 right-2 text-red-400" />}
          <p className={cn('text-lg font-bold leading-tight', color)}>{value ?? '—'}</p>
          <p className="text-[11px] text-slate-400 mt-0.5">{label}</p>
        </>
      )}
    </div>
  )
}
