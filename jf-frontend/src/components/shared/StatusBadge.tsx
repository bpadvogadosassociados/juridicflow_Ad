import { cn } from '@/lib/utils'
import {
  PROCESS_STATUS_LABELS,
  PROCESS_PHASE_LABELS,
  PROCESS_AREA_LABELS,
  RISK_LABELS,
  CUSTOMER_STATUS_LABELS,
  DEADLINE_PRIORITY_LABELS,
  DEADLINE_STATUS_LABELS,
  DEADLINE_TYPE_LABELS,
  TASK_STATUS_LABELS,
  TASK_PRIORITY_LABELS,
  INVOICE_STATUS_LABELS,
  AGREEMENT_STATUS_LABELS,
  EXPENSE_STATUS_LABELS,
  PROPOSAL_STATUS_LABELS,
} from '@/lib/constants'

type BadgeVariant =
  | 'process-status'
  | 'process-phase'
  | 'process-area'
  | 'risk'
  | 'customer-status'
  | 'deadline-priority'
  | 'deadline-status'
  | 'deadline-type'
  | 'task-status'
  | 'task-priority'
  | 'invoice-status'
  | 'agreement-status'
  | 'expense-status'
  | 'proposal-status'

interface StatusBadgeProps {
  value: string
  variant: BadgeVariant
  className?: string
}

const COLOR_MAP: Record<BadgeVariant, Record<string, string>> = {
  'process-status': {
    active: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    suspended: 'bg-amber-50 text-amber-700 border-amber-200',
    finished: 'bg-slate-100 text-slate-600 border-slate-200',
  },
  'process-phase': {
    initial: 'bg-blue-50 text-blue-700 border-blue-200',
    instruction: 'bg-violet-50 text-violet-700 border-violet-200',
    sentence: 'bg-amber-50 text-amber-700 border-amber-200',
    appeal: 'bg-orange-50 text-orange-700 border-orange-200',
    execution: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    archived: 'bg-slate-100 text-slate-500 border-slate-200',
  },
  'process-area': {
    trabalhista: 'bg-cyan-50 text-cyan-700 border-cyan-200',
    previdenciario: 'bg-teal-50 text-teal-700 border-teal-200',
    civil: 'bg-blue-50 text-blue-700 border-blue-200',
    criminal: 'bg-red-50 text-red-700 border-red-200',
    familia: 'bg-pink-50 text-pink-700 border-pink-200',
    tributario: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    empresarial: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    consumidor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    administrativo: 'bg-violet-50 text-violet-700 border-violet-200',
    outro: 'bg-slate-100 text-slate-600 border-slate-200',
  },
  risk: {
    baixo: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    medio: 'bg-amber-50 text-amber-700 border-amber-200',
    alto: 'bg-orange-50 text-orange-700 border-orange-200',
    critico: 'bg-red-600 text-white border-transparent',
  },
  'customer-status': {
    lead: 'bg-amber-50 text-amber-700 border-amber-200',
    prospect: 'bg-blue-50 text-blue-700 border-blue-200',
    client: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    inactive: 'bg-slate-100 text-slate-500 border-slate-200',
    archived: 'bg-slate-100 text-slate-400 border-slate-200',
  },
  'deadline-priority': {
    low: 'bg-slate-100 text-slate-600 border-slate-200',
    medium: 'bg-blue-50 text-blue-700 border-blue-200',
    high: 'bg-orange-50 text-orange-700 border-orange-200',
    urgent: 'bg-red-600 text-white border-transparent',
  },
  'deadline-status': {
    pending: 'bg-amber-50 text-amber-700 border-amber-200',
    completed: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    overdue: 'bg-red-50 text-red-700 border-red-200',
    cancelled: 'bg-slate-100 text-slate-500 border-slate-200',
  },
  'deadline-type': {
    legal: 'bg-violet-50 text-violet-700 border-violet-200',
    hearing: 'bg-blue-50 text-blue-700 border-blue-200',
    meeting: 'bg-teal-50 text-teal-700 border-teal-200',
    task: 'bg-slate-100 text-slate-600 border-slate-200',
    other: 'bg-slate-100 text-slate-500 border-slate-200',
  },
  'task-status': {
    backlog: 'bg-slate-100 text-slate-500 border-slate-200',
    todo: 'bg-blue-50 text-blue-700 border-blue-200',
    in_progress: 'bg-amber-50 text-amber-700 border-amber-200',
    review: 'bg-violet-50 text-violet-700 border-violet-200',
    done: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    cancelled: 'bg-slate-100 text-slate-400 border-slate-200',
  },
  'task-priority': {
    low: 'bg-slate-100 text-slate-600 border-slate-200',
    medium: 'bg-blue-50 text-blue-700 border-blue-200',
    high: 'bg-orange-50 text-orange-700 border-orange-200',
    critical: 'bg-red-600 text-white border-transparent',
  },
  'invoice-status': {
    draft: 'bg-slate-100 text-slate-500 border-slate-200',
    issued: 'bg-blue-50 text-blue-700 border-blue-200',
    sent: 'bg-violet-50 text-violet-700 border-violet-200',
    paid: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    overdue: 'bg-red-50 text-red-700 border-red-200',
    cancelled: 'bg-slate-100 text-slate-400 border-slate-200',
  },
  'agreement-status': {
    draft: 'bg-slate-100 text-slate-500 border-slate-200',
    active: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    suspended: 'bg-amber-50 text-amber-700 border-amber-200',
    completed: 'bg-blue-50 text-blue-700 border-blue-200',
    cancelled: 'bg-slate-100 text-slate-400 border-slate-200',
  },
  'expense-status': {
    pending: 'bg-amber-50 text-amber-700 border-amber-200',
    paid: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    cancelled: 'bg-slate-100 text-slate-400 border-slate-200',
  },
  'proposal-status': {
    draft: 'bg-slate-100 text-slate-500 border-slate-200',
    sent: 'bg-blue-50 text-blue-700 border-blue-200',
    accepted: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    rejected: 'bg-red-50 text-red-700 border-red-200',
    expired: 'bg-slate-100 text-slate-400 border-slate-200',
  },
}

const LABEL_MAP: Record<BadgeVariant, Record<string, string>> = {
  'process-status': PROCESS_STATUS_LABELS,
  'process-phase': PROCESS_PHASE_LABELS,
  'process-area': PROCESS_AREA_LABELS,
  risk: RISK_LABELS,
  'customer-status': CUSTOMER_STATUS_LABELS,
  'deadline-priority': DEADLINE_PRIORITY_LABELS,
  'deadline-status': DEADLINE_STATUS_LABELS,
  'deadline-type': DEADLINE_TYPE_LABELS,
  'task-status': TASK_STATUS_LABELS,
  'task-priority': TASK_PRIORITY_LABELS,
  'invoice-status': INVOICE_STATUS_LABELS,
  'agreement-status': AGREEMENT_STATUS_LABELS,
  'expense-status': EXPENSE_STATUS_LABELS,
  'proposal-status': PROPOSAL_STATUS_LABELS,
}

export function StatusBadge({ value, variant, className }: StatusBadgeProps) {
  const colorClass =
    COLOR_MAP[variant]?.[value] ?? 'bg-slate-100 text-slate-500 border-slate-200'
  const label = LABEL_MAP[variant]?.[value] ?? value

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border',
        colorClass,
        className,
      )}
    >
      {label}
    </span>
  )
}
