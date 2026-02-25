import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Scale,
  Clock,
  TrendingUp,
  Users,
  AlertTriangle,
  ArrowUpRight,
  Activity,
  DollarSign,
  CalendarClock,
  ChevronRight,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/layout/PageHeader'
import { EmptyState } from '@/components/shared/EmptyState'
import { dashboardApi } from '@/api/dashboard'
import { formatCurrency } from '@/lib/utils'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'

// Dados placeholder para o gráfico de barras (substituir por endpoint dedicado futuramente)
const MOCK_MONTHLY = [
  { name: 'Ago', processos: 18 },
  { name: 'Set', processos: 22 },
  { name: 'Out', processos: 19 },
  { name: 'Nov', processos: 28 },
  { name: 'Dez', processos: 25 },
  { name: 'Jan', processos: 31 },
]

export function DashboardPage() {
  const { getFullName, officeId } = useAuthStore()

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['dashboard', officeId],
    queryFn: dashboardApi.get,
    staleTime: 30_000,
    retry: 1,
    enabled: !!officeId,
  })

  // Hora do dia para saudação
  const hour = new Date().getHours()
  const greeting =
    hour < 12 ? 'Bom dia' : hour < 18 ? 'Boa tarde' : 'Boa noite'

  if (isLoading || !officeId) return <DashboardSkeleton />
  if (isError || !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-slate-400">
        <div className="w-14 h-14 rounded-2xl bg-red-50 flex items-center justify-center">
          <AlertTriangle size={24} className="text-red-400" />
        </div>
        <div className="text-center">
          <h3 className="text-sm font-semibold text-slate-700 mb-1">Erro ao carregar dashboard</h3>
          <p className="text-xs text-slate-400 max-w-xs">
            Não foi possível buscar os dados. Verifique se o servidor Django está rodando
            e se o escritório está selecionado corretamente.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => refetch()}
            className="text-xs text-blue-600 hover:text-blue-700 underline"
          >
            Tentar novamente
          </button>
          <button
            onClick={() => window.location.reload()}
            className="text-xs text-slate-400 hover:text-slate-600 underline"
          >
            Recarregar página
          </button>
        </div>
      </div>
    )
  }

  const kpis = [
    {
      title: 'Processos Ativos',
      value: data.processes.active,
      sub: `${data.processes.total} total`,
      icon: <Scale size={18} />,
      iconBg: 'bg-blue-50',
      iconColor: 'text-blue-600',
      href: '/app/processos',
    },
    {
      title: 'Prazos Vencidos',
      value: data.deadlines.overdue,
      sub: `${data.deadlines.today} vencendo hoje`,
      icon: <AlertTriangle size={18} />,
      iconBg: data.deadlines.overdue > 0 ? 'bg-red-50' : 'bg-emerald-50',
      iconColor: data.deadlines.overdue > 0 ? 'text-red-600' : 'text-emerald-600',
      href: '/app/prazos',
      urgent: data.deadlines.overdue > 0,
    },
    {
      title: 'Receita do Mês',
      value: formatCurrency(data.finance.received_month),
      sub: `${data.finance.pending_invoices} faturas pendentes`,
      icon: <TrendingUp size={18} />,
      iconBg: 'bg-emerald-50',
      iconColor: 'text-emerald-600',
      href: '/app/financeiro',
    },
    {
      title: 'Clientes',
      value: data.customers.clients,
      sub: `${data.customers.leads} leads ativos`,
      icon: <Users size={18} />,
      iconBg: 'bg-violet-50',
      iconColor: 'text-violet-600',
      href: '/app/contatos',
    },
  ]

  return (
    <div className="max-w-7xl mx-auto space-y-6 page-enter">
      <PageHeader
        title={`${greeting}, ${getFullName().split(' ')[0]} 👋`}
        subtitle="Aqui está o resumo do seu escritório hoje."
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {kpis.map((kpi) => (
          <Link key={kpi.title} to={kpi.href}>
            <Card
              className={cn(
                'border-slate-200 shadow-sm hover:shadow-md transition-all duration-200 cursor-pointer',
                kpi.urgent && 'border-red-200 hover:border-red-300',
              )}
            >
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs font-medium text-slate-500 mb-1">{kpi.title}</p>
                    <p
                      className={cn(
                        'text-2xl font-bold text-slate-900',
                        kpi.urgent && typeof kpi.value === 'number' && kpi.value > 0 && 'text-red-600',
                      )}
                    >
                      {kpi.value}
                    </p>
                    <p className="text-xs text-slate-400 mt-1">{kpi.sub}</p>
                  </div>
                  <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0', kpi.iconBg)}>
                    <span className={kpi.iconColor}>{kpi.icon}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Row 2: Chart + Upcoming */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Bar chart */}
        <Card className="lg:col-span-2 border-slate-200 shadow-sm">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold text-slate-900">
                Processos — Últimos 6 meses
              </CardTitle>
              <Link
                to="/app/relatorios"
                className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                Ver relatórios <ArrowUpRight size={11} />
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-52">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={MOCK_MONTHLY} barSize={28}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                    tickLine={false}
                    axisLine={false}
                    width={28}
                  />
                  <Tooltip
                    contentStyle={{
                      fontSize: 12,
                      border: '1px solid #e2e8f0',
                      borderRadius: 8,
                      boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                    }}
                    cursor={{ fill: '#f8fafc' }}
                    formatter={(v) => [v, 'Processos']}
                  />
                  <Bar dataKey="processos" fill="#2563eb" radius={[5, 5, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Upcoming deadlines */}
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                <CalendarClock size={15} className="text-slate-400" />
                Prazos da Semana
              </CardTitle>
              <Link
                to="/app/prazos"
                className="text-xs text-blue-600 hover:text-blue-700"
              >
                Ver todos
              </Link>
            </div>
          </CardHeader>
          <CardContent className="space-y-1 pt-0">
            <WeekDeadlinesWidget total={data.deadlines.this_week} overdue={data.deadlines.overdue} today={data.deadlines.today} />
          </CardContent>
        </Card>
      </div>

      {/* Row 3: Finance summary + Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Finance summary */}
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                <DollarSign size={15} className="text-slate-400" />
                Financeiro
              </CardTitle>
              <Link to="/app/financeiro" className="text-xs text-blue-600 hover:text-blue-700">
                Detalhe
              </Link>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 pt-0">
            <FinanceRow label="A receber" value={data.finance.receivable} color="text-slate-900" />
            <FinanceRow label="Recebido (mês)" value={data.finance.received_month} color="text-emerald-600" />
            <FinanceRow label="Despesas (mês)" value={data.finance.expenses_month} color="text-red-500" />
            <div className="pt-2 border-t border-slate-100">
              <FinanceRow
                label="Faturas pendentes"
                value={`${data.finance.pending_invoices} fatura${data.finance.pending_invoices !== 1 ? 's' : ''}`}
                color="text-amber-600"
              />
            </div>
          </CardContent>
        </Card>

        {/* Processes breakdown */}
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-slate-900 flex items-center gap-2">
              <Scale size={15} className="text-slate-400" />
              Processos por Status
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5 pt-0">
            {[
              { label: 'Ativos', value: data.processes.active, total: data.processes.total, color: 'bg-blue-500' },
              { label: 'Suspensos', value: data.processes.suspended, total: data.processes.total, color: 'bg-amber-400' },
              { label: 'Finalizados', value: data.processes.finished, total: data.processes.total, color: 'bg-slate-300' },
            ].map(({ label, value, total, color }) => (
              <div key={label}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-600">{label}</span>
                  <span className="font-medium text-slate-900">{value}</span>
                </div>
                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className={cn('h-full rounded-full transition-all duration-700', color)}
                    style={{ width: total > 0 ? `${(value / total) * 100}%` : '0%' }}
                  />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Recent activity */}
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-slate-900 flex items-center gap-2">
              <Activity size={15} className="text-slate-400" />
              Atividade Recente
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {data.recent_activity.length === 0 ? (
              <EmptyState title="Sem atividades" description="As ações do escritório aparecerão aqui." className="py-6" />
            ) : (
              <div className="space-y-3">
                {data.recent_activity.slice(0, 5).map((a, i) => (
                  <div key={i} className="flex gap-3 items-start">
                    <div className="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <Activity size={11} className="text-slate-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-slate-700 leading-snug">{a.description}</p>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {a.actor} · {a.when}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

// ── Sub-componentes ───────────────────────────────────────────────────────────

function FinanceRow({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-slate-500">{label}</span>
      <span className={cn('text-sm font-semibold tabular-nums', color)}>
        {typeof value === 'number' ? formatCurrency(value) : value}
      </span>
    </div>
  )
}

function WeekDeadlinesWidget({
  total,
  overdue,
  today,
}: {
  total: number
  overdue: number
  today: number
}) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'Vencidos', value: overdue, color: overdue > 0 ? 'text-red-600' : 'text-slate-500', bg: overdue > 0 ? 'bg-red-50' : 'bg-slate-50' },
          { label: 'Hoje', value: today, color: today > 0 ? 'text-amber-600' : 'text-slate-500', bg: today > 0 ? 'bg-amber-50' : 'bg-slate-50' },
          { label: 'Semana', value: total, color: 'text-blue-600', bg: 'bg-blue-50' },
        ].map(({ label, value, color, bg }) => (
          <div key={label} className={cn('rounded-xl p-3 text-center', bg)}>
            <p className={cn('text-xl font-bold', color)}>{value}</p>
            <p className="text-[10px] text-slate-500 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      <Link
        to="/app/prazos"
        className="flex items-center justify-between p-3 rounded-xl border border-slate-100 hover:border-blue-200 hover:bg-blue-50/30 transition-colors group"
      >
        <span className="text-xs text-slate-600 font-medium">Ver todos os prazos</span>
        <ChevronRight size={14} className="text-slate-400 group-hover:text-blue-500 transition-colors" />
      </Link>
    </div>
  )
}

function DashboardSkeleton() {
  return (
    <div className="max-w-7xl mx-auto space-y-6 animate-pulse">
      <div className="h-8 bg-slate-100 rounded-lg w-64" />
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-28 bg-slate-100 rounded-xl" />
        ))}
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 h-72 bg-slate-100 rounded-xl" />
        <div className="h-72 bg-slate-100 rounded-xl" />
      </div>
      <div className="grid grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-48 bg-slate-100 rounded-xl" />
        ))}
      </div>
    </div>
  )
}
