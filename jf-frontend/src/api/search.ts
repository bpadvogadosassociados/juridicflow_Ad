import api from './client'

export interface SearchResult {
  type: 'process' | 'customer' | 'deadline' | 'document'
  id: number
  title: string
  subtitle: string
}

export interface SearchResponse {
  results: SearchResult[]
}

export const searchApi = {
  search: (q: string) =>
    api.get<SearchResponse>('/search/', { params: { q } }).then((r) => r.data),
}
