import type { PaginatedResponse } from './api'

export interface CustomerInteraction {
  id: number
  type: string
  date: string
  subject: string
  description: string
  created_by: number
  created_by_name: string
  created_at: string
}

export interface Customer {
  id: number
  name: string
  document: string
  type: 'PF' | 'PJ'
  status: string
  email: string
  phone: string
  phone_secondary: string
  whatsapp: string
  address_street: string
  address_number: string
  address_complement: string
  address_neighborhood: string
  address_city: string
  address_state: string
  address_zipcode: string
  profession: string
  birth_date: string | null
  nationality: string
  marital_status: string
  company_name: string
  state_registration: string
  municipal_registration: string
  origin: string
  referral_name: string
  tags: string | string[]
  notes: string
  internal_notes: string
  responsible: number | null
  responsible_name: string | null
  first_contact_date: string | null
  last_interaction_date: string | null
  pipeline_stage: string
  next_action: string
  next_action_date: string | null
  estimated_value: string | null
  loss_reason: string
  can_whatsapp: boolean
  can_email: boolean
  lgpd_consent_date: string | null
  created_at: string
  updated_at: string
}

export type CustomerList = PaginatedResponse<Customer>

export interface CustomerFilters {
  search?: string
  status?: string
  type?: string
  pipeline_stage?: string
  page?: number
}

export interface CreateCustomerData {
  name: string
  type?: string
  status?: string
  document?: string
  email?: string
  phone?: string
  phone_secondary?: string
  whatsapp?: string
  address_street?: string
  address_number?: string
  address_complement?: string
  address_neighborhood?: string
  address_city?: string
  address_state?: string
  address_zipcode?: string
  profession?: string
  birth_date?: string | null
  nationality?: string
  marital_status?: string
  company_name?: string
  origin?: string
  referral_name?: string
  notes?: string
  internal_notes?: string
  responsible?: number | null
  pipeline_stage?: string
  next_action?: string
  next_action_date?: string | null
  estimated_value?: string | null
  tags?: string
}
