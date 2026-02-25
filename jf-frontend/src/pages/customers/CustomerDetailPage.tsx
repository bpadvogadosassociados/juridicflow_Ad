import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Edit, Trash2, Phone, Mail, MapPin, Plus, AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PageHeader } from '@/components/layout/PageHeader'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { customersApi } from '@/api/customers'
import { formatDocument, formatDate, formatCurrency, formatRelative, initials } from '@/lib/utils'
import { CUSTOMER_STATUS_LABELS, PIPELINE_STAGE_LABELS, ORIGIN_LABELS } from '@/lib/constants'
import { cn } from '@/lib/utils'
import type { CustomerInteraction } from '@/types/customer'

const INTERACTION_TYPE_LABELS: Record<string, string> = {
  note: 'Nota',
  call: 'Ligação',
  email: 'E-mail',
  meeting: 'Reunião',
  whatsapp: 'WhatsApp',
  other: 'Outro',
}

const INTERACTION_COLORS: Record<string, string> = {
  call: 'bg-blue-100 text-blue-600',
  email: 'bg-violet-100 text-violet-600',
  meeting: 'bg-emerald-100 text-emerald-600',
  whatsapp: 'bg-green-100 text-green-600',
  note: 'bg-amber-100 text-amber-600',
  other: 'bg-slate-100 text-slate-600',
}

export function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const customerId = Number(id)

  const [deleteOpen, setDeleteOpen] = useState(false)
  const [interactionOpen, setInteractionOpen] = useState(false)
  const [interactionForm, setInteractionForm] = useState({
    type: 'note', date: new Date().toISOString().split('T')[0], subject: '', description: '',
  })

  const { data: customer, isLoading, isError } = useQuery({
    queryKey: ['customer', customerId],
    queryFn: () => customersApi.get(customerId),
    enabled: !!customerId,
  })

  const { data: interactions, isLoading: interactionsLoading } = useQuery({
    queryKey: ['customer-interactions', customerId],
    queryFn: () => customersApi.getInteractions(customerId),
    enabled: !!customerId,
  })

  const deleteMutation = useMutation({
    mutationFn: () => customersApi.delete(customerId),
    onSuccess: () => {
      toast.success('Contato excluído.')
      navigate('/app/contatos')
    },
    onError: () => toast.error('Erro ao excluir.'),
  })

  const addInteractionMutation = useMutation({
    mutationFn: () => customersApi.addInteraction(customerId, interactionForm),
    onSuccess: () => {
      toast.success('Interação registrada.')
      setInteractionOpen(false)
      setInteractionForm({ type: 'note', date: new Date().toISOString().split('T')[0], subject: '', description: '' })
      queryClient.invalidateQueries({ queryKey: ['customer-interactions', customerId] })
    },
    onError: () => toast.error('Erro ao registrar interação.'),
  })

  if (isLoading) return <DetailSkeleton />
  if (isError || !customer) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 text-slate-400">
        <AlertTriangle size={32} />
        <p className="text-sm">Contato não encontrado.</p>
        <Button variant="outline" size="sm" onClick={() => navigate('/app/contatos')}>
          <ArrowLeft size={14} className="mr-2" /> Voltar
        </Button>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto page-enter">
      <PageHeader
        title={customer.name}
        subtitle={customer.type === 'PJ' ? customer.company_name || 'Pessoa Jurídica' : 'Pessoa Física'}
        breadcrumbs={[
          { label: 'Contatos', href: '/app/contatos' },
          { label: customer.name },
        ]}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => navigate(`/app/contatos/${customerId}/editar`)} className="gap-2">
              <Edit size={14} /> Editar
            </Button>
            <Button variant="outline" size="sm" onClick={() => setDeleteOpen(true)} className="gap-2 text-red-600 border-red-200 hover:bg-red-50">
              <Trash2 size={14} /> Excluir
            </Button>
          </div>
        }
      />

      <div className="flex flex-wrap gap-2 mb-6">
        <StatusBadge value={customer.status} variant="customer-status" />
        {customer.pipeline_stage && (
          <span className="text-xs px-2 py-1 rounded-md bg-slate-100 text-slate-600 font-medium">
            {PIPELINE_STAGE_LABELS[customer.pipeline_stage] ?? customer.pipeline_stage}
          </span>
        )}
        <span className={cn(
          'text-xs px-2 py-1 rounded-md font-medium',
          customer.type === 'PJ' ? 'bg-violet-50 text-violet-700' : 'bg-blue-50 text-blue-700',
        )}>
          {customer.type === 'PJ' ? 'Pessoa Jurídica' : 'Pessoa Física'}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Main content */}
        <div className="lg:col-span-2">
          <Tabs defaultValue="info">
            <TabsList className="bg-slate-100 h-9 mb-5">
              <TabsTrigger value="info" className="text-xs">Dados</TabsTrigger>
              <TabsTrigger value="interactions" className="text-xs">
                Histórico ({interactions?.length ?? 0})
              </TabsTrigger>
              <TabsTrigger value="crm" className="text-xs">CRM / Pipeline</TabsTrigger>
            </TabsList>

            {/* Tab: Dados */}
            <TabsContent value="info" className="space-y-4">
              <InfoCard title="Contato">
                {customer.email && <InfoRow label="E-mail" value={<a href={`mailto:${customer.email}`} className="text-blue-600 hover:underline">{customer.email}</a>} />}
                {customer.phone && <InfoRow label="Telefone" value={customer.phone} />}
                {customer.phone_secondary && <InfoRow label="Tel. Secundário" value={customer.phone_secondary} />}
                {customer.whatsapp && <InfoRow label="WhatsApp" value={customer.whatsapp} />}
                {customer.document && <InfoRow label="CPF/CNPJ" value={<span className="font-mono">{formatDocument(customer.document)}</span>} />}
              </InfoCard>

              {(customer.address_city || customer.address_street) && (
                <InfoCard title="Endereço">
                  {customer.address_street && <InfoRow label="Logradouro" value={`${customer.address_street}${customer.address_number ? ', ' + customer.address_number : ''}`} />}
                  {customer.address_complement && <InfoRow label="Complemento" value={customer.address_complement} />}
                  {customer.address_neighborhood && <InfoRow label="Bairro" value={customer.address_neighborhood} />}
                  {customer.address_city && <InfoRow label="Cidade/UF" value={`${customer.address_city}${customer.address_state ? '/' + customer.address_state : ''}`} />}
                  {customer.address_zipcode && <InfoRow label="CEP" value={customer.address_zipcode} />}
                </InfoCard>
              )}

              {customer.type === 'PF' && (
                <InfoCard title="Dados Pessoais">
                  {customer.birth_date && <InfoRow label="Nascimento" value={formatDate(customer.birth_date)} />}
                  {customer.nationality && <InfoRow label="Nacionalidade" value={customer.nationality} />}
                  {customer.marital_status && <InfoRow label="Estado Civil" value={customer.marital_status} />}
                  {customer.profession && <InfoRow label="Profissão" value={customer.profession} />}
                </InfoCard>
              )}

              {customer.type === 'PJ' && (
                <InfoCard title="Dados Empresariais">
                  {customer.company_name && <InfoRow label="Nome Fantasia" value={customer.company_name} />}
                  {customer.state_registration && <InfoRow label="IE" value={customer.state_registration} />}
                  {customer.municipal_registration && <InfoRow label="IM" value={customer.municipal_registration} />}
                </InfoCard>
              )}

              {customer.notes && (
                <InfoCard title="Observações">
                  <p className="text-sm text-slate-600 leading-relaxed">{customer.notes}</p>
                </InfoCard>
              )}
            </TabsContent>

            {/* Tab: Histórico de Interações */}
            <TabsContent value="interactions" className="space-y-3">
              <Button variant="outline" size="sm" onClick={() => setInteractionOpen(true)} className="gap-2">
                <Plus size={14} /> Registrar Interação
              </Button>

              {interactionsLoading ? (
                <div className="space-y-2">
                  {[1,2,3].map(i => <div key={i} className="h-16 bg-slate-100 rounded-xl animate-pulse" />)}
                </div>
              ) : !interactions?.length ? (
                <div className="text-center py-12 text-slate-400 text-sm">
                  Nenhuma interação registrada.
                </div>
              ) : (
                <div className="relative pl-6">
                  <div className="absolute left-2.5 top-0 bottom-0 w-px bg-slate-200" />
                  {interactions.map((item) => (
                    <div key={item.id} className="relative mb-4 last:mb-0">
                      <div className={cn(
                        'absolute -left-4 top-1 w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold',
                        INTERACTION_COLORS[item.type] ?? 'bg-slate-100 text-slate-500',
                      )}>
                        {(INTERACTION_TYPE_LABELS[item.type] ?? 'I')[0]}
                      </div>
                      <Card className="border-slate-200 shadow-none">
                        <CardContent className="p-3">
                          <div className="flex items-start justify-between gap-2 mb-1">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-semibold text-slate-700">{item.subject}</span>
                              <span className={cn('text-[10px] px-1.5 py-0.5 rounded', INTERACTION_COLORS[item.type] ?? 'bg-slate-100 text-slate-500')}>
                                {INTERACTION_TYPE_LABELS[item.type] ?? item.type}
                              </span>
                            </div>
                            <span className="text-[11px] text-slate-400 flex-shrink-0">{formatDate(item.date)}</span>
                          </div>
                          {item.description && (
                            <p className="text-xs text-slate-500 leading-relaxed">{item.description}</p>
                          )}
                          <p className="text-[10px] text-slate-400 mt-1.5">
                            {item.created_by_name} · {formatRelative(item.created_at)}
                          </p>
                        </CardContent>
                      </Card>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* Tab: CRM */}
            <TabsContent value="crm" className="space-y-4">
              <InfoCard title="Pipeline">
                <InfoRow label="Etapa" value={PIPELINE_STAGE_LABELS[customer.pipeline_stage] ?? '—'} />
                <InfoRow label="Valor Estimado" value={formatCurrency(customer.estimated_value)} />
                {customer.next_action && <InfoRow label="Próxima Ação" value={customer.next_action} />}
                {customer.next_action_date && <InfoRow label="Data da Ação" value={formatDate(customer.next_action_date)} />}
                {customer.loss_reason && <InfoRow label="Motivo da Perda" value={customer.loss_reason} />}
              </InfoCard>
              <InfoCard title="Origem">
                <InfoRow label="Origem" value={ORIGIN_LABELS[customer.origin] ?? customer.origin} />
                {customer.referral_name && <InfoRow label="Indicado por" value={customer.referral_name} />}
                <InfoRow label="Primeiro Contato" value={formatDate(customer.first_contact_date)} />
                <InfoRow label="Última Interação" value={formatDate(customer.last_interaction_date)} />
              </InfoCard>
            </TabsContent>
          </Tabs>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <Card className="border-slate-200 shadow-sm">
            <CardContent className="p-4 space-y-3">
              <div className="flex items-center gap-3">
                <div className={cn(
                  'w-12 h-12 rounded-xl flex items-center justify-center text-base font-bold',
                  customer.type === 'PJ' ? 'bg-violet-100 text-violet-600' : 'bg-blue-100 text-blue-600',
                )}>
                  {initials(customer.name)}
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-900">{customer.name}</p>
                  <p className="text-xs text-slate-400">{formatDocument(customer.document)}</p>
                </div>
              </div>

              {customer.phone && (
                <a href={`tel:${customer.phone}`} className="flex items-center gap-2 text-xs text-slate-600 hover:text-blue-600 transition-colors">
                  <Phone size={12} className="text-slate-400" /> {customer.phone}
                </a>
              )}
              {customer.email && (
                <a href={`mailto:${customer.email}`} className="flex items-center gap-2 text-xs text-slate-600 hover:text-blue-600 transition-colors">
                  <Mail size={12} className="text-slate-400" /> {customer.email}
                </a>
              )}
              {customer.address_city && (
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <MapPin size={12} className="text-slate-400" />
                  {customer.address_city}{customer.address_state ? `/${customer.address_state}` : ''}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="pb-2 pt-4 px-4">
              <CardTitle className="text-sm">Responsável</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <p className="text-sm text-slate-700">{customer.responsible_name ?? <span className="text-slate-400 italic">Não atribuído</span>}</p>
            </CardContent>
          </Card>

          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="pb-2 pt-4 px-4">
              <CardTitle className="text-sm">Histórico</CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4 space-y-2">
              <InfoRow label="Cadastrado" value={formatRelative(customer.created_at)} />
              <InfoRow label="Atualizado" value={formatRelative(customer.updated_at)} />
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Add Interaction Modal */}
      <Dialog open={interactionOpen} onOpenChange={setInteractionOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base">Registrar Interação</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-1">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label className="text-xs">Tipo</Label>
                <Select value={interactionForm.type} onValueChange={(v) => setInteractionForm(f => ({ ...f, type: v }))}>
                  <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(INTERACTION_TYPE_LABELS).map(([k, v]) => (
                      <SelectItem key={k} value={k}>{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Data</Label>
                <Input type="date" value={interactionForm.date} onChange={(e) => setInteractionForm(f => ({ ...f, date: e.target.value }))} className="h-9 text-sm" />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Assunto *</Label>
              <Input value={interactionForm.subject} onChange={(e) => setInteractionForm(f => ({ ...f, subject: e.target.value }))} placeholder="Resumo da interação" className="text-sm" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Descrição</Label>
              <Textarea value={interactionForm.description} onChange={(e) => setInteractionForm(f => ({ ...f, description: e.target.value }))} rows={3} className="resize-none text-sm" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setInteractionOpen(false)}>Cancelar</Button>
            <Button size="sm" className="bg-blue-600 hover:bg-blue-700"
              disabled={!interactionForm.subject || addInteractionMutation.isPending}
              onClick={() => addInteractionMutation.mutate()}>
              {addInteractionMutation.isPending ? 'Salvando…' : 'Registrar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Excluir contato?"
        description={`"${customer.name}" será excluído permanentemente.`}
        confirmLabel="Excluir"
        variant="destructive"
        onConfirm={() => deleteMutation.mutate()}
        loading={deleteMutation.isPending}
      />
    </div>
  )
}

function InfoCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="border-slate-200 shadow-none">
      <CardHeader className="pb-2 pt-4 px-4">
        <CardTitle className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{title}</CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4 space-y-2">{children}</CardContent>
    </Card>
  )
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  if (!value || value === '—') return null
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="text-xs text-slate-500 flex-shrink-0">{label}</span>
      <span className="text-xs text-slate-800 text-right font-medium">{value}</span>
    </div>
  )
}

function DetailSkeleton() {
  return (
    <div className="max-w-6xl mx-auto space-y-4 animate-pulse">
      <div className="h-8 bg-slate-100 rounded w-48" />
      <div className="grid grid-cols-3 gap-5">
        <div className="col-span-2 h-64 bg-slate-100 rounded-xl" />
        <div className="h-48 bg-slate-100 rounded-xl" />
      </div>
    </div>
  )
}
