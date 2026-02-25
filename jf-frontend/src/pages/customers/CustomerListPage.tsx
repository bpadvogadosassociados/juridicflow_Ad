import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/layout/PageHeader'
import { customersApi } from '@/api/customers'
import { CUSTOMER_STATUS_LABELS, PIPELINE_STAGE_LABELS, ORIGIN_LABELS } from '@/lib/constants'
import { cn } from '@/lib/utils'

const schema = z.object({
  name: z.string().min(2, 'Nome obrigatório'),
  type: z.enum(['PF', 'PJ']).default('PF'),
  status: z.string().default('lead'),
  document: z.string().optional().default(''),
  email: z.string().email('E-mail inválido').optional().or(z.literal('')),
  phone: z.string().optional().default(''),
  phone_secondary: z.string().optional().default(''),
  whatsapp: z.string().optional().default(''),
  address_street: z.string().optional().default(''),
  address_number: z.string().optional().default(''),
  address_complement: z.string().optional().default(''),
  address_neighborhood: z.string().optional().default(''),
  address_city: z.string().optional().default(''),
  address_state: z.string().max(2).optional().default(''),
  address_zipcode: z.string().optional().default(''),
  profession: z.string().optional().default(''),
  birth_date: z.string().optional().default(''),
  nationality: z.string().optional().default('Brasileira'),
  marital_status: z.string().optional().default(''),
  company_name: z.string().optional().default(''),
  origin: z.string().optional().default('other'),
  referral_name: z.string().optional().default(''),
  notes: z.string().optional().default(''),
  internal_notes: z.string().optional().default(''),
  pipeline_stage: z.string().optional().default(''),
  next_action: z.string().optional().default(''),
  next_action_date: z.string().optional().default(''),
  estimated_value: z.string().optional().default(''),
})

type FormData = z.infer<typeof schema>

const MARITAL_STATUS_OPTIONS = [
  { value: 'solteiro', label: 'Solteiro(a)' },
  { value: 'casado', label: 'Casado(a)' },
  { value: 'divorciado', label: 'Divorciado(a)' },
  { value: 'viuvo', label: 'Viúvo(a)' },
  { value: 'uniao_estavel', label: 'União Estável' },
]

export function CustomerFormPage() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isEdit = !!id
  const customerId = id ? Number(id) : null

  const { data: existing, isLoading: loadingExisting } = useQuery({
    queryKey: ['customer', customerId],
    queryFn: () => customersApi.get(customerId!),
    enabled: isEdit && !!customerId,
  })

  const { register, handleSubmit, formState: { errors }, setValue, watch, reset } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { type: 'PF', status: 'lead', origin: 'other' },
  })

  useEffect(() => {
    if (existing) {
      reset({
        name: existing.name,
        type: existing.type,
        status: existing.status,
        document: existing.document ?? '',
        email: existing.email ?? '',
        phone: existing.phone ?? '',
        phone_secondary: existing.phone_secondary ?? '',
        whatsapp: existing.whatsapp ?? '',
        address_street: existing.address_street ?? '',
        address_number: existing.address_number ?? '',
        address_complement: existing.address_complement ?? '',
        address_neighborhood: existing.address_neighborhood ?? '',
        address_city: existing.address_city ?? '',
        address_state: existing.address_state ?? '',
        address_zipcode: existing.address_zipcode ?? '',
        profession: existing.profession ?? '',
        birth_date: existing.birth_date ?? '',
        nationality: existing.nationality ?? 'Brasileira',
        marital_status: existing.marital_status ?? '',
        company_name: existing.company_name ?? '',
        origin: existing.origin ?? 'other',
        referral_name: existing.referral_name ?? '',
        notes: existing.notes ?? '',
        internal_notes: existing.internal_notes ?? '',
        pipeline_stage: existing.pipeline_stage ?? '',
        next_action: existing.next_action ?? '',
        next_action_date: existing.next_action_date ?? '',
        estimated_value: existing.estimated_value ?? '',
      })
    }
  }, [existing, reset])

  const createMutation = useMutation({
    mutationFn: (data: FormData) => customersApi.create({
      ...data,
      birth_date: data.birth_date || null,
      next_action_date: data.next_action_date || null,
      estimated_value: data.estimated_value || null,
    }),
    onSuccess: (res) => {
      toast.success('Contato cadastrado!')
      queryClient.invalidateQueries({ queryKey: ['customers'] })
      navigate(`/app/contatos/${res.id}`)
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail ?? 'Erro ao salvar.'),
  })

  const updateMutation = useMutation({
    mutationFn: (data: FormData) => customersApi.update(customerId!, {
      ...data,
      birth_date: data.birth_date || null,
      next_action_date: data.next_action_date || null,
      estimated_value: data.estimated_value || null,
    }),
    onSuccess: () => {
      toast.success('Contato atualizado.')
      queryClient.invalidateQueries({ queryKey: ['customers'] })
      queryClient.invalidateQueries({ queryKey: ['customer', customerId] })
      navigate(`/app/contatos/${customerId}`)
    },
    onError: () => toast.error('Erro ao atualizar.'),
  })

  const onSubmit = (data: FormData) => {
    if (isEdit) updateMutation.mutate(data)
    else createMutation.mutate(data)
  }

  const isPending = createMutation.isPending || updateMutation.isPending
  const watchedType = watch('type')

  if (isEdit && loadingExisting) return <div className="h-64 bg-slate-100 rounded-xl animate-pulse max-w-3xl mx-auto" />

  return (
    <div className="max-w-3xl mx-auto page-enter">
      <PageHeader
        title={isEdit ? 'Editar Contato' : 'Novo Contato'}
        breadcrumbs={[{ label: 'Contatos', href: '/app/contatos' }, { label: isEdit ? 'Editar' : 'Novo' }]}
        actions={
          <Button variant="outline" size="sm" onClick={() => navigate(-1)} className="gap-2">
            <ArrowLeft size={14} /> Voltar
          </Button>
        }
      />

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        {/* Dados Básicos */}
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Dados Básicos</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <F label="Nome / Razão Social *" error={errors.name?.message}>
              <Input {...register('name')} placeholder="Nome completo ou razão social" className={cn(errors.name && 'border-red-300')} />
            </F>
            <div className="grid grid-cols-3 gap-4">
              <F label="Tipo">
                <Select value={watchedType} onValueChange={(v) => setValue('type', v as 'PF' | 'PJ')}>
                  <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="PF">Pessoa Física</SelectItem>
                    <SelectItem value="PJ">Pessoa Jurídica</SelectItem>
                  </SelectContent>
                </Select>
              </F>
              <F label="Status">
                <Select value={watch('status')} onValueChange={(v) => setValue('status', v)}>
                  <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(CUSTOMER_STATUS_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                  </SelectContent>
                </Select>
              </F>
              <F label="CPF / CNPJ">
                <Input {...register('document')} placeholder={watchedType === 'PJ' ? '00.000.000/0001-00' : '000.000.000-00'} className="font-mono" />
              </F>
            </div>
          </CardContent>
        </Card>

        {/* Contato */}
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-3"><CardTitle className="text-sm">Contato</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <F label="E-mail" error={errors.email?.message}>
                <Input {...register('email')} type="email" placeholder="email@exemplo.com" />
              </F>
              <F label="Telefone">
                <Input {...register('phone')} placeholder="(00) 00000-0000" />
              </F>
              <F label="Tel. Secundário">
                <Input {...register('phone_secondary')} placeholder="(00) 00000-0000" />
              </F>
              <F label="WhatsApp">
                <Input {...register('whatsapp')} placeholder="(00) 00000-0000" />
              </F>
            </div>
          </CardContent>
        </Card>

        {/* Dados específicos PF/PJ */}
        {watchedType === 'PF' ? (
          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="pb-3"><CardTitle className="text-sm">Dados Pessoais</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <F label="Data de Nascimento">
                  <Input type="date" {...register('birth_date')} />
                </F>
                <F label="Estado Civil">
                  <Select value={watch('marital_status') || ''} onValueChange={(v) => setValue('marital_status', v)}>
                    <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue placeholder="Selecionar" /></SelectTrigger>
                    <SelectContent>
                      {MARITAL_STATUS_OPTIONS.map(({ value, label }) => <SelectItem key={value} value={value}>{label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </F>
                <F label="Profissão">
                  <Input {...register('profession')} placeholder="Ex: Empresário" />
                </F>
                <F label="Nacionalidade">
                  <Input {...register('nationality')} placeholder="Brasileira" />
                </F>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="pb-3"><CardTitle className="text-sm">Dados Empresariais</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <F label="Nome Fantasia">
                <Input {...register('company_name')} placeholder="Nome fantasia ou marca" />
              </F>
            </CardContent>
          </Card>
        )}

        {/* Endereço */}
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-3"><CardTitle className="text-sm">Endereço</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-2">
                <F label="Logradouro"><Input {...register('address_street')} placeholder="Rua, Av." /></F>
              </div>
              <F label="Número"><Input {...register('address_number')} placeholder="123" /></F>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <F label="Complemento"><Input {...register('address_complement')} placeholder="Sala, Apto" /></F>
              <F label="Bairro"><Input {...register('address_neighborhood')} /></F>
              <F label="Cidade"><Input {...register('address_city')} /></F>
              <div className="grid grid-cols-2 gap-2">
                <F label="UF"><Input {...register('address_state')} maxLength={2} placeholder="SP" className="uppercase" /></F>
                <F label="CEP"><Input {...register('address_zipcode')} placeholder="00000-000" /></F>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* CRM */}
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-3"><CardTitle className="text-sm">CRM / Pipeline</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <F label="Etapa do Pipeline">
                <Select value={watch('pipeline_stage') || ''} onValueChange={(v) => setValue('pipeline_stage', v)}>
                  <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue placeholder="Selecionar" /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(PIPELINE_STAGE_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                  </SelectContent>
                </Select>
              </F>
              <F label="Valor Estimado (R$)">
                <Input {...register('estimated_value')} type="number" step="0.01" placeholder="0,00" />
              </F>
              <F label="Origem">
                <Select value={watch('origin') || 'other'} onValueChange={(v) => setValue('origin', v)}>
                  <SelectTrigger className="h-9 text-sm border-slate-200"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(ORIGIN_LABELS).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                  </SelectContent>
                </Select>
              </F>
              <F label="Indicado por">
                <Input {...register('referral_name')} placeholder="Nome do indicador" />
              </F>
            </div>
            <F label="Próxima Ação">
              <Input {...register('next_action')} placeholder="O que precisa ser feito" />
            </F>
          </CardContent>
        </Card>

        {/* Notas */}
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-3"><CardTitle className="text-sm">Observações</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <F label="Notas Gerais">
              <Textarea {...register('notes')} rows={3} className="resize-none text-sm" placeholder="Observações visíveis para a equipe" />
            </F>
            <F label="Notas Internas">
              <Textarea {...register('internal_notes')} rows={2} className="resize-none text-sm" placeholder="Notas privadas / confidenciais" />
            </F>
          </CardContent>
        </Card>

        <div className="flex justify-end gap-3 pt-2 pb-6">
          <Button type="button" variant="outline" onClick={() => navigate(-1)}>Cancelar</Button>
          <Button type="submit" disabled={isPending} className="bg-blue-600 hover:bg-blue-700 min-w-32">
            {isPending ? (
              <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />Salvando…</>
            ) : isEdit ? 'Salvar Alterações' : 'Criar Contato'}
          </Button>
        </div>
      </form>
    </div>
  )
}

function F({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs font-medium text-slate-600">{label}</Label>
      {children}
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  )
}
