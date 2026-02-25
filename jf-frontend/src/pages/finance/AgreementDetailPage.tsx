import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/layout/PageHeader'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { financeApi } from '@/api/finance'
import { formatCurrency, formatDate } from '@/lib/utils'
import { BILLING_TYPE_LABELS } from '@/lib/constants'

export function AgreementDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({
    queryKey: ['agreement', Number(id)],
    queryFn: () => financeApi.getAgreement(Number(id)),
    enabled: !!id,
  })

  if (isLoading) return <div className="h-64 bg-slate-100 rounded-xl animate-pulse max-w-3xl mx-auto" />
  if (!data) return (
    <div className="text-center py-20 text-slate-400">
      <p>Contrato não encontrado.</p>
      <Button variant="outline" size="sm" className="mt-4 gap-2" onClick={() => navigate('/app/financeiro/contratos')}>
        <ArrowLeft size={14} /> Voltar
      </Button>
    </div>
  )

  return (
    <div className="max-w-3xl mx-auto page-enter">
      <PageHeader
        title={data.title}
        breadcrumbs={[{ label: 'Financeiro', href: '/app/financeiro' }, { label: 'Contratos', href: '/app/financeiro/contratos' }, { label: data.title }]}
        actions={
          <Button variant="outline" size="sm" onClick={() => navigate('/app/financeiro/contratos')} className="gap-2">
            <ArrowLeft size={14} /> Voltar
          </Button>
        }
      />

      <div className="flex gap-2 mb-5">
        <StatusBadge value={data.status} variant="agreement-status" />
        <span className="text-xs px-2 py-1 rounded-md bg-slate-100 text-slate-600">
          {BILLING_TYPE_LABELS[data.billing_type] ?? data.billing_type}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-5">
        {[
          { label: 'Valor Total', value: formatCurrency(data.amount), color: 'text-slate-900' },
          { label: 'Total Faturado', value: formatCurrency(data.total_invoiced), color: 'text-blue-600' },
          { label: 'Saldo a Receber', value: formatCurrency(data.balance), color: parseFloat(data.balance) > 0 ? 'text-amber-600' : 'text-emerald-600' },
        ].map(item => (
          <Card key={item.label} className="border-slate-200 shadow-none">
            <CardContent className="p-4">
              <p className="text-xs text-slate-400 mb-1">{item.label}</p>
              <p className={`text-lg font-bold ${item.color}`}>{item.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border-slate-200 shadow-none">
        <CardHeader className="pb-2"><CardTitle className="text-sm text-slate-500 uppercase tracking-wide text-xs">Detalhes</CardTitle></CardHeader>
        <CardContent className="px-4 pb-4 space-y-2">
          {[
            { label: 'Parcelas', value: String(data.installments) },
            { label: 'Início', value: formatDate(data.start_date) },
            { label: 'Término', value: formatDate(data.end_date) },
          ].map(({ label, value }) => value && value !== '—' ? (
            <div key={label} className="flex justify-between">
              <span className="text-xs text-slate-500">{label}</span>
              <span className="text-xs font-medium text-slate-800">{value}</span>
            </div>
          ) : null)}
          {data.notes && <p className="text-xs text-slate-500 pt-2 border-t border-slate-100">{data.notes}</p>}
        </CardContent>
      </Card>
    </div>
  )
}
