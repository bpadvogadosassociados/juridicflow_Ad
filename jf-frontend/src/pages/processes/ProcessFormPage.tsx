import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { ArrowLeft, Plus, Trash2, ChevronRight, ChevronLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/layout/PageHeader'
import { processesApi } from '@/api/processes'
import {
  PROCESS_STATUS_LABELS, PROCESS_PHASE_LABELS, PROCESS_AREA_LABELS,
  RISK_LABELS, PARTY_ROLE_LABELS,
} from '@/lib/constants'
import { cn } from '@/lib/utils'

// Validação do número CNJ
const CNJ_REGEX = /^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$/

const partySchema = z.object({
  role: z.string().min(1, 'Selecione o papel'),
  name: z.string().min(2, 'Nome obrigatório'),
  customer: z.number().nullable().optional(),
  document: z.string().optional().default(''),
  email: z.string().email('E-mail inválido').optional().or(z.literal('')),
  phone: z.string().optional().default(''),
  notes: z.string().optional().default(''),
})

const schema = z.object({
  // Step 1
  number: z.string().regex(CNJ_REGEX, 'Formato inválido. Use: 0000000-00.0000.0.00.0000'),
  court: z.string().optional().default(''),
  subject: z.string().optional().default(''),
  area: z.string().optional().default(''),
  phase: z.string().optional().default('initial'),
  status: z.string().optional().default('active'),
  // Step 2
  filing_date: z.string().optional().default(''),
  distribution_date: z.string().optional().default(''),
  first_hearing_date: z.string().optional().default(''),
  sentence_date: z.string().optional().default(''),
  court_unit: z.string().optional().default(''),
  judge_name: z.string().optional().default(''),
  cause_value: z.string().optional().default(''),
  risk: z.string().optional().default(''),
  success_probability: z.coerce.number().min(0).max(100).optional().nullable(),
  description: z.string().optional().default(''),
  next_action: z.string().optional().default(''),
  last_movement: z.string().optional().default(''),
  internal_notes: z.string().optional().default(''),
  // Step 3
  parties: z.array(partySchema).optional().default([]),
})

type FormData = z.infer<typeof schema>

const STEPS = [
  { label: 'Identificação', desc: 'Número CNJ e dados básicos' },
  { label: 'Detalhes', desc: 'Datas, valor e indicadores' },
  { label: 'Partes', desc: 'Autor, réu e outros' },
]

export function ProcessFormPage() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isEdit = !!id
  const processId = id ? Number(id) : null
  const [step, setStep] = useState(0)

  const { data: existing, isLoading: loadingExisting } = useQuery({
    queryKey: ['process', processId],
    queryFn: () => processesApi.get(processId!),
    enabled: isEdit && !!processId,
  })

  const {
    register, handleSubmit, formState: { errors }, setValue, watch, control, reset,
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      status: 'active',
      phase: 'initial',
      parties: [],
    },
  })

  const { fields: partyFields, append: appendParty, remove: removeParty } = useFieldArray({
    control,
    name: 'parties',
  })

  // Populate form when editing
  useEffect(() => {
    if (existing) {
      reset({
        number: existing.number,
        court: existing.court ?? '',
        subject: existing.subject ?? '',
        area: existing.area ?? '',
        phase: existing.phase ?? 'initial',
        status: existing.status ?? 'active',
        filing_date: existing.filing_date ?? '',
        distribution_date: existing.distribution_date ?? '',
        first_hearing_date: existing.first_hearing_date ?? '',
        sentence_date: existing.sentence_date ?? '',
        court_unit: existing.court_unit ?? '',
        judge_name: existing.judge_name ?? '',
        cause_value: existing.cause_value ?? '',
        risk: existing.risk ?? '',
        success_probability: existing.success_probability ?? undefined,
        description: existing.description ?? '',
        next_action: existing.next_action ?? '',
        last_movement: existing.last_movement ?? '',
        internal_notes: existing.internal_notes ?? '',
        parties: existing.parties.map((p) => ({
          role: p.role,
          name: p.name,
          customer: p.customer,
          document: p.document ?? '',
          email: p.email ?? '',
          phone: p.phone ?? '',
          notes: p.notes ?? '',
        })),
      })
    }
  }, [existing, reset])

  const createMutation = useMutation({
    mutationFn: (data: FormData) =>
      processesApi.create({
        ...data,
        cause_value: data.cause_value || null,
        filing_date: data.filing_date || null,
        distribution_date: data.distribution_date || null,
        first_hearing_date: data.first_hearing_date || null,
        sentence_date: data.sentence_date || null,
        success_probability: data.success_probability ?? null,
        parties: data.parties ?? [],
      }),
    onSuccess: (res) => {
      toast.success('Processo cadastrado com sucesso!')
      queryClient.invalidateQueries({ queryKey: ['processes'] })
      navigate(`/app/processos/${res.id}`)
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.number?.[0]
        ?? err?.response?.data?.detail
        ?? 'Erro ao salvar processo.'
      toast.error(msg)
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: FormData) =>
      processesApi.update(processId!, {
        ...data,
        cause_value: data.cause_value || null,
        filing_date: data.filing_date || null,
        distribution_date: data.distribution_date || null,
        first_hearing_date: data.first_hearing_date || null,
        sentence_date: data.sentence_date || null,
        success_probability: data.success_probability ?? null,
        parties: data.parties ?? [],
      }),
    onSuccess: () => {
      toast.success('Processo atualizado.')
      queryClient.invalidateQueries({ queryKey: ['processes'] })
      queryClient.invalidateQueries({ queryKey: ['process', processId] })
      navigate(`/app/processos/${processId}`)
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.number?.[0] ?? err?.response?.data?.detail ?? 'Erro ao atualizar.'
      toast.error(msg)
    },
  })

  const onSubmit = (data: FormData) => {
    if (isEdit) updateMutation.mutate(data)
    else createMutation.mutate(data)
  }

  const isPending = createMutation.isPending || updateMutation.isPending

  if (isEdit && loadingExisting) {
    return (
      <div className="max-w-3xl mx-auto space-y-4 animate-pulse">
        <div className="h-8 bg-slate-100 rounded w-48" />
        <div className="h-64 bg-slate-100 rounded-xl" />
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto page-enter">
      <PageHeader
        title={isEdit ? 'Editar Processo' : 'Novo Processo'}
        subtitle={isEdit ? existing?.number : 'Preencha os dados do novo processo'}
        breadcrumbs={[
          { label: 'Processos', href: '/app/processos' },
          { label: isEdit ? 'Editar' : 'Novo' },
        ]}
        actions={
          <Button variant="outline" size="sm" onClick={() => navigate(-1)} className="gap-2">
            <ArrowLeft size={14} /> Voltar
          </Button>
        }
      />

      {/* Step indicator */}
      <div className="flex items-center gap-0 mb-8">
        {STEPS.map((s, i) => (
          <div key={i} className="flex items-center flex-1">
            <div className="flex items-center gap-2 flex-1">
              <div
                className={cn(
                  'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 transition-all',
                  i < step ? 'bg-blue-600 text-white' :
                  i === step ? 'bg-blue-600 text-white ring-4 ring-blue-100' :
                  'bg-slate-100 text-slate-400',
                )}
              >
                {i < step ? '✓' : i + 1}
              </div>
              <div className="hidden sm:block">
                <p className={cn('text-xs font-semibold', i === step ? 'text-blue-700' : i < step ? 'text-slate-600' : 'text-slate-400')}>
                  {s.label}
                </p>
                <p className="text-[10px] text-slate-400">{s.desc}</p>
              </div>
            </div>
            {i < STEPS.length - 1 && (
              <div className={cn('flex-1 h-0.5 mx-3', i < step ? 'bg-blue-600' : 'bg-slate-200')} />
            )}
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit(onSubmit)}>
        {/* ── Step 0: Identificação ───────────────────────────── */}
        {step === 0 && (
          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Identificação do Processo</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <FormField label="Número CNJ *" error={errors.number?.message}>
                <Input
                  {...register('number')}
                  placeholder="0000000-00.0000.0.00.0000"
                  className={cn('font-mono', errors.number && 'border-red-300')}
                />
                <p className="text-[11px] text-slate-400 mt-1">Formato: NNNNNNN-DD.AAAA.J.TT.OOOO</p>
              </FormField>

              <div className="grid grid-cols-2 gap-4">
                <FormField label="Área" error={errors.area?.message}>
                  <SelectField
                    value={watch('area') ?? ''}
                    onChange={(v) => setValue('area', v)}
                    options={PROCESS_AREA_LABELS}
                    placeholder="Selecione a área"
                  />
                </FormField>
                <FormField label="Fase" error={errors.phase?.message}>
                  <SelectField
                    value={watch('phase') ?? 'initial'}
                    onChange={(v) => setValue('phase', v)}
                    options={PROCESS_PHASE_LABELS}
                    placeholder="Selecione a fase"
                  />
                </FormField>
              </div>

              <FormField label="Status" error={errors.status?.message}>
                <SelectField
                  value={watch('status') ?? 'active'}
                  onChange={(v) => setValue('status', v)}
                  options={PROCESS_STATUS_LABELS}
                  placeholder="Selecione o status"
                />
              </FormField>

              <FormField label="Assunto" error={errors.subject?.message}>
                <Input {...register('subject')} placeholder="Breve descrição do assunto do processo" />
              </FormField>

              <FormField label="Tribunal / Vara" error={errors.court?.message}>
                <Input {...register('court')} placeholder="Ex: 1ª Vara do Trabalho de São Paulo" />
              </FormField>
            </CardContent>
          </Card>
        )}

        {/* ── Step 1: Detalhes ─────────────────────────────────── */}
        {step === 1 && (
          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Dados Complementares</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <FormField label="Data de Ajuizamento">
                  <Input type="date" {...register('filing_date')} className="text-sm" />
                </FormField>
                <FormField label="Data de Distribuição">
                  <Input type="date" {...register('distribution_date')} className="text-sm" />
                </FormField>
                <FormField label="Audiência Inicial">
                  <Input type="date" {...register('first_hearing_date')} className="text-sm" />
                </FormField>
                <FormField label="Sentença">
                  <Input type="date" {...register('sentence_date')} className="text-sm" />
                </FormField>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <FormField label="Unidade Judiciária">
                  <Input {...register('court_unit')} placeholder="Unidade" />
                </FormField>
                <FormField label="Nome do Juiz">
                  <Input {...register('judge_name')} placeholder="Dr(a)." />
                </FormField>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <FormField label="Valor da Causa (R$)">
                  <Input {...register('cause_value')} placeholder="0,00" type="number" step="0.01" />
                </FormField>
                <FormField label="Risco">
                  <SelectField
                    value={watch('risk') ?? ''}
                    onChange={(v) => setValue('risk', v)}
                    options={RISK_LABELS}
                    placeholder="Selecionar"
                  />
                </FormField>
              </div>

              <FormField label="Probabilidade de Êxito (%)">
                <Input
                  {...register('success_probability')}
                  type="number" min="0" max="100"
                  placeholder="Ex: 75"
                />
              </FormField>

              <FormField label="Descrição">
                <Textarea {...register('description')} placeholder="Contexto e detalhes do processo" rows={3} className="resize-none" />
              </FormField>

              <FormField label="Próxima Ação">
                <Textarea {...register('next_action')} placeholder="O que precisa ser feito" rows={2} className="resize-none" />
              </FormField>

              <FormField label="Notas Internas">
                <Textarea {...register('internal_notes')} placeholder="Observações privadas" rows={2} className="resize-none" />
              </FormField>
            </CardContent>
          </Card>
        )}

        {/* ── Step 2: Partes ───────────────────────────────────── */}
        {step === 2 && (
          <div className="space-y-4">
            <Card className="border-slate-200 shadow-sm">
              <CardHeader className="pb-3 flex-row items-center justify-between">
                <CardTitle className="text-base">Partes do Processo</CardTitle>
                <Button
                  type="button" variant="outline" size="sm"
                  className="gap-2"
                  onClick={() => appendParty({ role: 'autor', name: '', document: '', email: '', phone: '', notes: '', customer: null })}
                >
                  <Plus size={14} /> Adicionar Parte
                </Button>
              </CardHeader>
              <CardContent className="space-y-4">
                {partyFields.length === 0 ? (
                  <div className="text-center py-8 text-slate-400 text-sm">
                    Clique em "Adicionar Parte" para incluir as partes do processo.
                  </div>
                ) : (
                  partyFields.map((field, idx) => (
                    <div key={field.id} className="p-4 border border-slate-200 rounded-xl bg-slate-50/50 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-500">Parte {idx + 1}</span>
                        <Button type="button" variant="ghost" size="sm" onClick={() => removeParty(idx)} className="text-red-400 hover:text-red-600 h-7 w-7 p-0">
                          <Trash2 size={13} />
                        </Button>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <FormField label="Papel *" error={errors.parties?.[idx]?.role?.message}>
                          <SelectField
                            value={watch(`parties.${idx}.role`) ?? ''}
                            onChange={(v) => setValue(`parties.${idx}.role`, v)}
                            options={PARTY_ROLE_LABELS}
                            placeholder="Papel"
                          />
                        </FormField>
                        <FormField label="Nome *" error={errors.parties?.[idx]?.name?.message}>
                          <Input {...register(`parties.${idx}.name`)} placeholder="Nome completo" className={errors.parties?.[idx]?.name ? 'border-red-300' : ''} />
                        </FormField>
                        <FormField label="CPF / CNPJ">
                          <Input {...register(`parties.${idx}.document`)} placeholder="000.000.000-00" />
                        </FormField>
                        <FormField label="E-mail" error={errors.parties?.[idx]?.email?.message}>
                          <Input {...register(`parties.${idx}.email`)} type="email" placeholder="email@exemplo.com" />
                        </FormField>
                        <FormField label="Telefone">
                          <Input {...register(`parties.${idx}.phone`)} placeholder="(00) 00000-0000" />
                        </FormField>
                      </div>
                      <FormField label="Observações">
                        <Textarea {...register(`parties.${idx}.notes`)} rows={2} className="resize-none text-sm" />
                      </FormField>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Navigation buttons */}
        <div className="flex items-center justify-between mt-6">
          <Button
            type="button" variant="outline"
            onClick={() => step > 0 ? setStep(step - 1) : navigate(-1)}
            className="gap-2"
          >
            <ChevronLeft size={14} />
            {step === 0 ? 'Cancelar' : 'Anterior'}
          </Button>

          {step < STEPS.length - 1 ? (
            <Button type="button" onClick={() => setStep(step + 1)} className="bg-blue-600 hover:bg-blue-700 gap-2">
              Próximo <ChevronRight size={14} />
            </Button>
          ) : (
            <Button
              type="submit"
              disabled={isPending}
              className="bg-blue-600 hover:bg-blue-700 gap-2"
            >
              {isPending ? (
                <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Salvando…</>
              ) : (
                isEdit ? 'Salvar Alterações' : 'Criar Processo'
              )}
            </Button>
          )}
        </div>
      </form>
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function FormField({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs font-medium text-slate-600">{label}</Label>
      {children}
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  )
}

function SelectField({ value, onChange, options, placeholder }: {
  value: string
  onChange: (v: string) => void
  options: Record<string, string>
  placeholder?: string
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="h-9 border-slate-200 text-sm bg-white">
        <SelectValue placeholder={placeholder ?? 'Selecionar'} />
      </SelectTrigger>
      <SelectContent>
        {Object.entries(options).map(([k, v]) => (
          <SelectItem key={k} value={k}>{v}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
