import axios, { type AxiosInstance } from 'axios'
import { toast } from 'sonner'
import { useAuthStore } from '@/store/authStore'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

export const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// ── Request interceptor ───────────────────────────────────────────────────────
// Injeta Authorization + X-Office-Id automaticamente em toda request

api.interceptors.request.use((config) => {
  const { accessToken, officeId } = useAuthStore.getState()

  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }

  // Não injeta X-Office-Id nos endpoints de auth que não precisam
  const noOfficeEndpoints = ['/auth/login/', '/auth/token/refresh/', '/auth/token/verify/', '/auth/me/', '/auth/memberships/']
  const needsOffice = !noOfficeEndpoints.some((ep) => config.url?.includes(ep))

  if (officeId && needsOffice) {
    config.headers['X-Office-Id'] = String(officeId)
  }

  return config
})

// ── Response interceptor ──────────────────────────────────────────────────────
// Lida com 401 (token expirado) e erros gerais

let isRefreshing = false
let refreshQueue: Array<(token: string) => void> = []

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // 401 → tenta renovar o access token
    if (error.response?.status === 401 && !originalRequest._retry) {
      const { refreshToken, setTokens, logout } = useAuthStore.getState()

      if (!refreshToken) {
        logout()
        window.location.href = '/login'
        return Promise.reject(error)
      }

      if (isRefreshing) {
        // Enfileira requests que chegaram enquanto o refresh está em andamento
        return new Promise((resolve) => {
          refreshQueue.push((newToken: string) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`
            resolve(api(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const { data } = await axios.post(`${BASE_URL}/auth/token/refresh/`, {
          refresh: refreshToken,
        })

        const newAccess = data.access
        const newRefresh = data.refresh ?? refreshToken

        setTokens(newAccess, newRefresh)

        // Drena a fila
        refreshQueue.forEach((cb) => cb(newAccess))
        refreshQueue = []

        originalRequest.headers.Authorization = `Bearer ${newAccess}`
        return api(originalRequest)
      } catch {
        logout()
        refreshQueue = []
        window.location.href = '/login'
        return Promise.reject(error)
      } finally {
        isRefreshing = false
      }
    }

    // 403 — sem permissão (silencia para não spammar durante hydration)
    if (error.response?.status === 403) {
      // Só mostra toast se for uma ação explícita do usuário (mutation),
      // não em queries de background. O componente pode tratar individualmente.
      console.warn('[API] 403 Forbidden:', error.config?.url)
    }

    // 404
    if (error.response?.status === 404) {
      // Silencia 404 — componente trata
      console.warn('[API] 404 Not Found:', error.config?.url)
    }

    // 500
    if (error.response?.status >= 500) {
      toast.error('Erro interno do servidor. Tente novamente.')
    }

    return Promise.reject(error)
  },
)

export default api
