import api from './client'

export interface Document {
  id: number
  title: string
  description: string
  file: string
  file_url: string | null
  uploaded_by: number
  created_at: string
  updated_at: string
}

export interface DocumentList {
  count: number
  next: string | null
  previous: string | null
  results: Document[]
}

export const documentsApi = {
  list: (params: Record<string, any> = {}) =>
    api.get<DocumentList>('/documents/', { params }).then(r => r.data),

  get: (id: number) =>
    api.get<Document>(`/documents/${id}/`).then(r => r.data),

  upload: (data: FormData) =>
    api.post<Document>('/documents/', data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data),

  update: (id: number, data: { title?: string; description?: string }) =>
    api.patch<Document>(`/documents/${id}/`, data).then(r => r.data),

  delete: (id: number) =>
    api.delete(`/documents/${id}/`),
}
