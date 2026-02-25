import api from './client'
import type {
  FeeAgreement, AgreementList, CreateAgreementData,
  Invoice, InvoiceList, CreateInvoiceData,
  Expense, ExpenseList, CreateExpenseData,
  Payment,
} from '@/types/finance'

export const financeApi = {
  // Agreements
  listAgreements: (params: Record<string, any> = {}) =>
    api.get<AgreementList>('/finance/agreements/', { params }).then(r => r.data),
  getAgreement: (id: number) =>
    api.get<FeeAgreement>(`/finance/agreements/${id}/`).then(r => r.data),
  createAgreement: (data: CreateAgreementData) =>
    api.post<FeeAgreement>('/finance/agreements/', data).then(r => r.data),
  updateAgreement: (id: number, data: Partial<CreateAgreementData>) =>
    api.patch<FeeAgreement>(`/finance/agreements/${id}/`, data).then(r => r.data),
  deleteAgreement: (id: number) =>
    api.delete(`/finance/agreements/${id}/`),

  // Invoices
  listInvoices: (params: Record<string, any> = {}) =>
    api.get<InvoiceList>('/finance/invoices/', { params }).then(r => r.data),
  getInvoice: (id: number) =>
    api.get<Invoice>(`/finance/invoices/${id}/`).then(r => r.data),
  createInvoice: (data: CreateInvoiceData) =>
    api.post<Invoice>('/finance/invoices/', data).then(r => r.data),
  updateInvoice: (id: number, data: Partial<CreateInvoiceData>) =>
    api.patch<Invoice>(`/finance/invoices/${id}/`, data).then(r => r.data),
  deleteInvoice: (id: number) =>
    api.delete(`/finance/invoices/${id}/`),

  // Payments
  createPayment: (data: { invoice: number; paid_at: string; amount: string; method?: string; reference?: string; notes?: string }) =>
    api.post<Payment>('/finance/payments/', data).then(r => r.data),

  // Expenses
  listExpenses: (params: Record<string, any> = {}) =>
    api.get<ExpenseList>('/finance/expenses/', { params }).then(r => r.data),
  getExpense: (id: number) =>
    api.get<Expense>(`/finance/expenses/${id}/`).then(r => r.data),
  createExpense: (data: CreateExpenseData) =>
    api.post<Expense>('/finance/expenses/', data).then(r => r.data),
  updateExpense: (id: number, data: Partial<CreateExpenseData>) =>
    api.patch<Expense>(`/finance/expenses/${id}/`, data).then(r => r.data),
  deleteExpense: (id: number) =>
    api.delete(`/finance/expenses/${id}/`),
}
