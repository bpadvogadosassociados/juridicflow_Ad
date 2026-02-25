import type { PaginatedResponse } from './api'

export interface FeeAgreement {
  id: number
  customer: number
  process: number | null
  title: string
  description: string
  amount: string
  billing_type: string
  installments: number
  status: string
  start_date: string | null
  end_date: string | null
  notes: string
  responsible: number | null
  total_invoiced: string
  total_received: string
  balance: string
  created_at: string
  updated_at: string
}

export interface Invoice {
  id: number
  agreement: number
  number: string
  issue_date: string
  due_date: string
  amount: string
  discount: string
  status: string
  description: string
  notes: string
  payment_method: string
  net_amount: string
  paid_amount: string
  balance: string
  is_overdue: boolean
  created_at: string
  updated_at: string
}

export interface Payment {
  id: number
  invoice: number
  paid_at: string
  amount: string
  method: string
  reference: string
  notes: string
  recorded_by: number
  recorded_by_name: string
  created_at: string
  updated_at: string
}

export interface Expense {
  id: number
  title: string
  description: string
  category: string
  date: string
  due_date: string | null
  amount: string
  status: string
  payment_method: string
  supplier: string
  reference: string
  notes: string
  responsible: number | null
  responsible_name: string | null
  created_at: string
  updated_at: string
}

export type AgreementList = PaginatedResponse<FeeAgreement>
export type InvoiceList = PaginatedResponse<Invoice>
export type ExpenseList = PaginatedResponse<Expense>

export interface CreateAgreementData {
  customer: number
  process?: number | null
  title: string
  description?: string
  amount: string
  billing_type?: string
  installments?: number
  status?: string
  start_date?: string | null
  end_date?: string | null
  notes?: string
  responsible?: number | null
}

export interface CreateInvoiceData {
  agreement: number
  number?: string
  issue_date: string
  due_date: string
  amount: string
  discount?: string
  status?: string
  description?: string
  notes?: string
  payment_method?: string
}

export interface CreateExpenseData {
  title: string
  description?: string
  category?: string
  date: string
  due_date?: string | null
  amount: string
  status?: string
  payment_method?: string
  supplier?: string
  reference?: string
  notes?: string
  responsible?: number | null
}
