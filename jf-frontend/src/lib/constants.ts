// ── Processos ─────────────────────────────────────────────────────────────────

export const PROCESS_STATUS_LABELS: Record<string, string> = {
  active: 'Ativo',
  suspended: 'Suspenso',
  finished: 'Finalizado',
}

export const PROCESS_PHASE_LABELS: Record<string, string> = {
  initial: 'Inicial',
  instruction: 'Instrução',
  sentence: 'Sentença',
  appeal: 'Recurso',
  execution: 'Execução',
  archived: 'Arquivado',
}

export const PROCESS_AREA_LABELS: Record<string, string> = {
  trabalhista: 'Trabalhista',
  previdenciario: 'Previdenciário',
  civil: 'Cível',
  criminal: 'Criminal',
  familia: 'Família',
  tributario: 'Tributário',
  empresarial: 'Empresarial',
  consumidor: 'Consumidor',
  administrativo: 'Administrativo',
  outro: 'Outro',
}

export const RISK_LABELS: Record<string, string> = {
  baixo: 'Baixo',
  medio: 'Médio',
  alto: 'Alto',
  critico: 'Crítico',
}

export const PARTY_ROLE_LABELS: Record<string, string> = {
  autor: 'Autor',
  reu: 'Réu',
  terceiro: 'Terceiro',
  advogado: 'Advogado',
  testemunha: 'Testemunha',
  perito: 'Perito',
  outro: 'Outro',
}

// ── Clientes / CRM ────────────────────────────────────────────────────────────

export const CUSTOMER_STATUS_LABELS: Record<string, string> = {
  lead: 'Lead',
  prospect: 'Prospect',
  client: 'Cliente',
  inactive: 'Inativo',
  archived: 'Arquivado',
}

export const CUSTOMER_TYPE_LABELS: Record<string, string> = {
  PF: 'Pessoa Física',
  PJ: 'Pessoa Jurídica',
}

export const PIPELINE_STAGE_LABELS: Record<string, string> = {
  novo: 'Novo',
  contato_feito: 'Contato Feito',
  reuniao_marcada: 'Reunião Marcada',
  proposta_enviada: 'Proposta Enviada',
  em_negociacao: 'Em Negociação',
  ganho: 'Ganho',
  perdido: 'Perdido',
}

export const ORIGIN_LABELS: Record<string, string> = {
  website: 'Website',
  referral: 'Indicação',
  social_media: 'Redes Sociais',
  advertising: 'Publicidade',
  event: 'Evento',
  partner: 'Parceiro',
  other: 'Outro',
}

export const MARITAL_STATUS_LABELS: Record<string, string> = {
  solteiro: 'Solteiro(a)',
  casado: 'Casado(a)',
  divorciado: 'Divorciado(a)',
  viuvo: 'Viúvo(a)',
  uniao_estavel: 'União Estável',
}

// ── Prazos ────────────────────────────────────────────────────────────────────

export const DEADLINE_TYPE_LABELS: Record<string, string> = {
  legal: 'Legal',
  hearing: 'Audiência',
  meeting: 'Reunião',
  task: 'Tarefa',
  other: 'Outro',
}

export const DEADLINE_PRIORITY_LABELS: Record<string, string> = {
  low: 'Baixa',
  medium: 'Média',
  high: 'Alta',
  urgent: 'Urgente',
}

export const DEADLINE_STATUS_LABELS: Record<string, string> = {
  pending: 'Pendente',
  completed: 'Concluído',
  overdue: 'Vencido',
  cancelled: 'Cancelado',
}

// ── Tarefas ───────────────────────────────────────────────────────────────────

export const TASK_STATUS_LABELS: Record<string, string> = {
  backlog: 'Backlog',
  todo: 'A Fazer',
  in_progress: 'Em Progresso',
  review: 'Revisão',
  done: 'Concluído',
  cancelled: 'Cancelado',
}

export const TASK_PRIORITY_LABELS: Record<string, string> = {
  low: 'Baixa',
  medium: 'Média',
  high: 'Alta',
  critical: 'Crítica',
}

// ── Financeiro ────────────────────────────────────────────────────────────────

export const BILLING_TYPE_LABELS: Record<string, string> = {
  one_time: 'Avulso',
  monthly: 'Mensal',
  success_fee: 'Êxito',
  hourly: 'Por Hora',
  installments: 'Parcelado',
}

export const AGREEMENT_STATUS_LABELS: Record<string, string> = {
  draft: 'Rascunho',
  active: 'Ativo',
  suspended: 'Suspenso',
  completed: 'Concluído',
  cancelled: 'Cancelado',
}

export const INVOICE_STATUS_LABELS: Record<string, string> = {
  draft: 'Rascunho',
  issued: 'Emitida',
  sent: 'Enviada',
  paid: 'Paga',
  overdue: 'Vencida',
  cancelled: 'Cancelada',
}

export const PAYMENT_METHOD_LABELS: Record<string, string> = {
  pix: 'PIX',
  bank_transfer: 'Transferência',
  debit_card: 'Cartão de Débito',
  credit_card: 'Cartão de Crédito',
  cash: 'Dinheiro',
  check: 'Cheque',
  boleto: 'Boleto',
  other: 'Outro',
}

export const EXPENSE_CATEGORY_LABELS: Record<string, string> = {
  salary: 'Salários',
  rent: 'Aluguel',
  utilities: 'Utilidades',
  supplies: 'Materiais',
  technology: 'Tecnologia',
  marketing: 'Marketing',
  legal_fees: 'Honorários',
  travel: 'Viagens',
  training: 'Treinamentos',
  consulting: 'Consultoria',
  other: 'Outros',
}

export const EXPENSE_STATUS_LABELS: Record<string, string> = {
  pending: 'Pendente',
  paid: 'Pago',
  cancelled: 'Cancelado',
}

export const PROPOSAL_STATUS_LABELS: Record<string, string> = {
  draft: 'Rascunho',
  sent: 'Enviada',
  accepted: 'Aceita',
  rejected: 'Rejeitada',
  expired: 'Expirada',
}

// ── Notificações ──────────────────────────────────────────────────────────────

export const NOTIFICATION_TYPE_LABELS: Record<string, string> = {
  info: 'Informação',
  warning: 'Aviso',
  success: 'Sucesso',
  error: 'Erro',
  deadline: 'Prazo',
  publication: 'Publicação',
  task: 'Tarefa',
}

// ── Memberships ───────────────────────────────────────────────────────────────

export const MEMBERSHIP_ROLE_LABELS: Record<string, string> = {
  org_admin: 'Admin da Organização',
  office_admin: 'Admin do Escritório',
  lawyer: 'Advogado',
  intern: 'Estagiário',
  finance: 'Financeiro',
}

// ── Nav Items — para sidebar ──────────────────────────────────────────────────

export const PAGE_SIZE = 25
