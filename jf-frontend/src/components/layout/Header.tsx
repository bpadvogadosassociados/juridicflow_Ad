import { useState, useEffect } from 'react'
import { Menu, Search, ChevronDown, Building2, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu'
import { GlobalSearch } from '@/components/shared/GlobalSearch'
import { NotificationPanel } from '@/components/shared/NotificationPanel'
import { useUIStore } from '@/store/uiStore'
import { useAuthStore } from '@/store/authStore'
import { useQuery } from '@tanstack/react-query'
import { authApi } from '@/api/auth'
import { cn } from '@/lib/utils'

export function Header() {
  const { toggleSidebar } = useUIStore()
  const { officeId, setOffice, setPermissions, memberships } = useAuthStore()
  const [searchOpen, setSearchOpen] = useState(false)

  // Ctrl+K para abrir search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setSearchOpen(true)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const currentMembership = memberships.find((m) => m.office.id === officeId)
  const hasMultipleOffices = memberships.length > 1

  const handleSelectOffice = async (newOfficeId: number) => {
    setOffice(newOfficeId)
    // Re-fetch permissions for the new office
    try {
      const { permissions } = await authApi.permissions()
      setPermissions(permissions)
    } catch {}
  }

  return (
    <>
      <header className="h-16 bg-white border-b border-slate-200 flex items-center px-4 gap-3 flex-shrink-0">
        {/* Toggle sidebar */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className="text-slate-500 hover:text-slate-700 h-8 w-8 flex-shrink-0"
        >
          <Menu size={18} />
        </Button>

        {/* Search trigger */}
        <button
          onClick={() => setSearchOpen(true)}
          className="flex items-center gap-2 flex-1 max-w-md h-9 px-3 rounded-lg bg-slate-50 border border-slate-200 text-slate-400 text-sm hover:bg-slate-100 hover:border-slate-300 transition-all group"
        >
          <Search size={14} />
          <span className="flex-1 text-left">Buscar…</span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded border border-slate-200 bg-white text-slate-400 text-[10px] font-mono group-hover:border-slate-300">
            <span>⌘</span>K
          </kbd>
        </button>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Office switcher */}
        {hasMultipleOffices && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-9 gap-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 max-w-[200px]"
              >
                <Building2 size={15} className="text-slate-400 flex-shrink-0" />
                <span className="truncate text-sm font-medium">
                  {currentMembership?.office.name ?? 'Escritório'}
                </span>
                <ChevronDown size={13} className="text-slate-400 flex-shrink-0" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel className="text-xs text-slate-500 font-normal">
                Trocar escritório
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              {memberships.map((m) => (
                <DropdownMenuItem
                  key={m.id}
                  onClick={() => handleSelectOffice(m.office.id)}
                  className="gap-2 cursor-pointer"
                >
                  <Building2 size={14} className="text-slate-400" />
                  <span className="flex-1 truncate">{m.office.name}</span>
                  {m.office.id === officeId && (
                    <Check size={13} className="text-blue-600" />
                  )}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}

        {/* Notifications */}
        <NotificationPanel />
      </header>

      {/* Global search dialog */}
      <GlobalSearch open={searchOpen} onOpenChange={setSearchOpen} />
    </>
  )
}
