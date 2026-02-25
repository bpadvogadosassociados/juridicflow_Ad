// Resposta paginada padrão DRF
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// Parâmetros de paginação
export interface PaginationParams {
  page?: number
  page_size?: number
  search?: string
  ordering?: string
}

// Erro de API
export interface ApiError {
  detail?: string
  code?: string
  [field: string]: string | string[] | undefined
}
