import { useAuthStore } from '@/store/authStore'

/**
 * Verifica se o usuário tem uma permissão específica.
 *
 * Uso:
 *   const canCreate = usePermission('processes.add_process')
 *   if (!canCreate) return null
 */
export function usePermission(permission: string): boolean {
  return useAuthStore((s) => s.hasPermission(permission))
}

/**
 * Verifica múltiplas permissões (retorna true se tiver TODAS)
 */
export function usePermissions(permissions: string[]): boolean {
  const perms = useAuthStore((s) => s.permissions)
  return permissions.every((p) => perms.includes(p))
}

/**
 * Verifica múltiplas permissões (retorna true se tiver ALGUMA)
 */
export function useAnyPermission(permissions: string[]): boolean {
  const perms = useAuthStore((s) => s.permissions)
  return permissions.some((p) => perms.includes(p))
}
