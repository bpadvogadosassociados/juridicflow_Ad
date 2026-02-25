import api from './client'
import type { Customer, CustomerList, CustomerFilters, CreateCustomerData, CustomerInteraction } from '@/types/customer'

export const customersApi = {
  list: (params: CustomerFilters = {}) =>
    api.get<CustomerList>('/customers/', { params }).then((r) => r.data),

  get: (id: number) =>
    api.get<Customer>(`/customers/${id}/`).then((r) => r.data),

  create: (data: CreateCustomerData) =>
    api.post<Customer>('/customers/', data).then((r) => r.data),

  update: (id: number, data: Partial<CreateCustomerData>) =>
    api.patch<Customer>(`/customers/${id}/`, data).then((r) => r.data),

  delete: (id: number) =>
    api.delete(`/customers/${id}/`),

  getInteractions: (id: number) =>
    api.get<CustomerInteraction[]>(`/customers/${id}/interactions/`).then((r) => r.data),

  addInteraction: (id: number, data: { type: string; date: string; subject: string; description?: string }) =>
    api.post<CustomerInteraction>(`/customers/${id}/interactions/`, data).then((r) => r.data),
}
