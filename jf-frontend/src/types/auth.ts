export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  is_staff: boolean
}

export interface Organization {
  id: number
  name: string
  plan: string
  is_active: boolean
}

export interface Office {
  id: number
  name: string
  is_active: boolean
  organization_id: number
}

export interface Membership {
  id: number
  role: string
  is_active: boolean
  organization: Organization
  office: Office
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access: string
  refresh: string
}

export interface PermissionsResponse {
  permissions: string[]
}
