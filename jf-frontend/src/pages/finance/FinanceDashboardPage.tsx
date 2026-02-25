import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  TrendingUp, TrendingDown, Receipt, FileText,
  ArrowRight, AlertTriangle, CheckCircle2, Clock
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/layout/PageHeader'
import { financeApi } from '@/api/finance'
import { formatCurrency, formatDate } from '@/lib/utils'
import { INVOICE_STATUS_LABELS, EXPENSE_CATEGORY_LABELS } from '@/lib/constants'
import { cn } from '@/lib/utils'

function useFinanceSummary() {
  const invoices = useQuery({
    queryKey: ['invoices-summary'],
    queryFn: () => financeApi.listInvoices({ page: 1 }),
    staleTime: 60_000,
  })
  const expenses = useQuery({
    queryKey: ['expenses-summary'],
    queryFn: () => financeApi.listExpenses({ page: 1 }),
    staleTime: 60_000,
  })
  const overdue = useQuery({
    queryKey: ['invoices-overdue'],
    queryFn: () => financeApi.listInvoices({ status: 'overdue' }),
    staleTime: 60_000,
  })
  return { invoices, expenses, overdue }
}

export function FinanceDashboardPage() {
  const navigate = useNavigate()
  const { invoices, expenses, overdue } = useFinanceSummary()

  const invoiceResults = invoices.data?.results ?? []
  const expenseResults = expenses.data?.results ?? []
  const overdueResults = overdue.data?.results ?? []

  // Compute totals from first page (indicative)
  const totalReceivable = invoiceResults
    .filter(i => !['paid', 'cancelled'].includes(i.status))
    .reduce((s, i) => s + parseFloat(i.net_amount || i.amount), 0)

  const totalPaid = invoiceResults
    .filter(i => i.status === 'paid')
    .reduce((s, i) => s + parseFloat(i.paid_amount || '0'), 0)

  const totalExpenses = expenseResults
    .reduce((s, e) => s + parseFloat(e.amount), 0)

  const overdueTotal = overdueResults
    .reduce((s, i) => s + parseFloat(i.balance || '0'), 0)

  const isLoading = invoices.isLoading || expenses.isLoading

  // Status breakdown for invoices
  const statusCounts: Record<string, number> = {}
  invoiceResults.forEach(i => {
    statusCounts[i.status] = (statusCounts[i.status] ?? 0) + 1
  })

  // Expense breakdown by category
  const catTotals: Record<string, number> = {}
  expenseResults.forEach(e => {
    catTotals[e.category] = (catTotals[e.category] ?? 0) + parseFloat(e.amount)
  })
  const topCategories = Object.entries(catTotals)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)

  return (
    <div className="max-w-7xl mx-auto page-enter">
      <PageHeader
        title="Financeiro"
        subtitle="Visão geral das finanças do escritório"
        breadcrumbs={[{ label: 'JuridicFlow' }, { label: 'Financeiro' }]}
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard
          label="A Receber"
          value={formatCurrency(totalReceivable)}
          icon={<TrendingUp size={18} />}
          color="text-blue-600"
          bg="bg-blue-50"
          loading={isLoading}
          action={() => navigate('/app/financeiro/faturas')}
        />
        <KpiCard
          label="Recebido"
          value={formatCurrency(totalPaid)}
          icon={<CheckCircle2 size={18} />}
          color="text-emerald-600"
          bg="bg-emerald-50"
          loading={isLoading}
        />
        <KpiCard
          label="Despesas"
          value={formatCurrency(totalExpenses)}
          icon={<TrendingDown size={18} />}
          color="text-red-500"
          bg="bg-red-50"
          loading={isLoading}
          action={() => navigate('/app/financeiro/despesas')}
        />
        <KpiCard
          label="Vencidas"
          value={formatCurrency(overdueTotal)}
          icon={<AlertTriangle size={18} />}
          color="text-amber-600"
          bg="bg-amber-50"
          loading={overdue.isLoading}
          alert={overdueResults.length > 0}
          action={() => navigate('/app/financeiro/faturas?status=overdue')}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-5">
        {/* Faturas recentes */}
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-3 flex-row items-center justify-between">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Receipt size={15} className="text-slate-400" /> Faturas Recentes
            </CardTitle>
            <Button
              variant="ghost" size="sm"
              className="h-7 text-xs text-blue-600 gap-1"
              onClick={() => navigate('/app/financeiro/faturas')}
            >
              Ver todas <ArrowRight size={12} />
            </Button>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {isLoading ? (
              <LoadingSkeleton rows={4} />
            ) : invoiceResults.length === 0 ? (
              <Empty text="Nenhuma fatura cadastrada." />
            ) : (
              <div className="space-y-2">
                {invoiceResults.slice(0, 5).map(inv => (
                  <div
                    key={inv.id}
                    onClick={() => navigate('/app/financeiro/faturas')}
                    className="flex items-center justify-between py-2 border-b border-slate-50 last:border-0 cursor-pointer hover:bg-slate-50 -mx-1 px-1 rounded transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-slate-800 truncate">
                        {inv.number || `Fatura #${inv.id}`}
                      </p>
                      <p className="text-[11px] text-slate-400">Vence {formatDate(inv.due_date)}</p>
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0 ml-3">
                      <span className={cn(
                        'text-[10px] px-1.5 py-0.5 rounded font-medium',
                        inv.status === 'paid' ? 'bg-emerald-50 text-emerald-700' :
                        inv.status === 'overdue' ? 'bg-red-50 text-red-600' :
                        'bg-slate-100 text-slate-600'
                      )}>
                        {INVOICE_STATUS_LABELS[inv.status] ?? inv.status}
                      </span>
                      <span className="text-xs font-semibold text-slate-700">
                        {formatCurrency(inv.net_amount)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Despesas por categoria */}
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-3 flex-row items-center justify-between">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <TrendingDown size={15} className="text-slate-400" /> Despesas por Categoria
            </CardTitle>
            <Button
              variant="ghost" size="sm"
              className="h-7 text-xs text-blue-600 gap-1"
              onClick={() => navigate('/app/financeiro/despesas')}
            >
              Ver todas <ArrowRight size={12} />
            </Button>
          </CardHeader>
          <CardContent className="px-4 pb-4">
            {isLoading ? (
              <LoadingSkeleton rows={4} />
            ) : topCategories.length === 0 ? (
              <Empty text="Nenhuma despesa registrada." />
            ) : (
              <div className="space-y-3">
                {topCategories.map(([cat, val]) => {
                  const pct = totalExpenses > 0 ? (val / totalExpenses) * 100 : 0
                  return (
                    <div key={cat}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-slate-600">{EXPENSE_CATEGORY_LABELS[cat] ?? cat}</span>
                        <span className="text-xs font-semibold text-slate-700">{formatCurrency(val)}</span>
                      </div>
                      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 rounded-full transition-all"
                          style={{ width: `${Math.min(pct, 100)}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: 'Contratos', desc: 'Acordos de honorários', icon: <FileText size={18} />, href: '/app/financeiro/contratos', color: 'text-violet-600 bg-violet-50' },
          { label: 'Faturas', desc: 'Cobranças e recebimentos', icon: <Receipt size={18} />, href: '/app/financeiro/faturas', color: 'text-blue-600 bg-blue-50' },
          { label: 'Despesas', desc: 'Custos operacionais', icon: <TrendingDown size={18} />, href: '/app/financeiro/despesas', color: 'text-red-500 bg-red-50' },
        ].map(({ label, desc, icon, href, color }) => (
          <Card
            key={href}
            onClick={() => navigate(href)}
            className="border-slate-200 shadow-sm cursor-pointer hover:shadow-md hover:border-slate-300 transition-all group"
          >
            <CardContent className="p-4 flex items-center gap-4">
              <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0', color)}>
                {icon}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-900">{label}</p>
                <p className="text-xs text-slate-400">{desc}</p>
              </div>
              <ArrowRight size={14} className="text-slate-300 group-hover:text-slate-500 transition-colors" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

function KpiCard({ label, value, icon, color, bg, loading, alert, action }: {
  label: string
  value: string
  icon: React.ReactNode
  color: string
  bg: string
  loading?: boolean
  alert?: boolean
  action?: () => void
}) {
  return (
    <Card
      onClick={action}
      className={cn(
        'border-slate-200 shadow-sm transition-all',
        action && 'cursor-pointer hover:shadow-md hover:border-slate-300',
        alert && 'border-amber-200',
      )}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center', bg, color)}>
            {icon}
          </div>
          {alert && <AlertTriangle size={14} className="text-amber-500" />}
        </div>
        {loading ? (
          <div className="space-y-1.5">
            <div className="h-6 bg-slate-100 rounded animate-pulse w-24" />
            <div className="h-3 bg-slate-50 rounded animate-pulse w-16" />
          </div>
        ) : (
          <>
            <p className="text-lg font-bold text-slate-900 leading-tight">{value}</p>
            <p className="text-xs text-slate-400 mt-0.5">{label}</p>
          </>
        )}
      </CardContent>
    </Card>
  )
}

function LoadingSkeleton({ rows }: { rows: number }) {
  return (
    <div className="space-y-3 animate-pulse">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex justify-between">
          <div className="h-4 bg-slate-100 rounded w-32" />
          <div className="h-4 bg-slate-100 rounded w-16" />
        </div>
      ))}
    </div>
  )
}

function Empty({ text }: { text: string }) {
  return <p className="text-xs text-slate-400 text-center py-6">{text}</p>
}
