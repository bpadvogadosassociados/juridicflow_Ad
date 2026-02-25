import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  CommandDialog, CommandInput, CommandList,
  CommandEmpty, CommandGroup, CommandItem,
} from '@/components/ui/command'
import { Scale, Users, Clock, FileText, Loader2 } from 'lucide-react'
import { searchApi } from '@/api/search'
import { useDebounce } from '@/hooks/useDebounce'
import { cn } from '@/lib/utils'

interface SearchResult {
  type: 'process' | 'customer' | 'deadline' | 'document'
  id: number
  title: string
  subtitle: string
}

const TYPE_CONFIG: Record<string, {
  label: string
  icon: React.ReactNode
  color: string
  href: (id: number) => string
}> = {
  process:  { label: 'Processos',  icon: <Scale size={14} />,    color: 'text-blue-600',   href: (id) => `/app/processos/${id}` },
  customer: { label: 'Contatos',   icon: <Users size={14} />,    color: 'text-emerald-600', href: (id) => `/app/contatos/${id}` },
  deadline: { label: 'Prazos',     icon: <Clock size={14} />,    color: 'text-amber-600',  href: (id) => `/app/prazos` },
  document: { label: 'Documentos', icon: <FileText size={14} />, color: 'text-slate-500',  href: (id) => `/app/documentos/${id}` },
}

const GROUP_ORDER = ['process', 'customer', 'deadline', 'document'] as const

interface GlobalSearchProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function GlobalSearch({ open, onOpenChange }: GlobalSearchProps) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const debouncedQuery = useDebounce(query, 250)

  const { data, isFetching } = useQuery({
    queryKey: ['search', debouncedQuery],
    queryFn: () => searchApi.search(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
    staleTime: 10_000,
    retry: false,
  })

  // Reset on close
  useEffect(() => {
    if (!open) setTimeout(() => setQuery(''), 200)
  }, [open])

  const results: SearchResult[] = (data as any)?.results ?? []

  // Group by type
  const grouped = GROUP_ORDER.reduce((acc, type) => {
    const items = results.filter((r) => r.type === type)
    if (items.length > 0) acc[type] = items
    return acc
  }, {} as Record<string, SearchResult[]>)

  const handleSelect = useCallback((result: SearchResult) => {
    const config = TYPE_CONFIG[result.type]
    if (config) navigate(config.href(result.id))
    onOpenChange(false)
  }, [navigate, onOpenChange])

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <div className="flex items-center border-b border-slate-200 px-3">
        <CommandInput
          placeholder="Buscar processos, clientes, prazos…"
          value={query}
          onValueChange={setQuery}
          className="border-0 focus:ring-0 text-sm h-12"
        />
        {isFetching && <Loader2 size={14} className="text-slate-400 animate-spin flex-shrink-0 mr-2" />}
      </div>
      <CommandList className="max-h-96 overflow-y-auto">
        {query.length < 2 ? (
          <div className="py-10 text-center">
            <p className="text-sm text-slate-400">Digite pelo menos 2 caracteres para buscar</p>
            <div className="flex justify-center gap-6 mt-6">
              {GROUP_ORDER.map((type) => {
                const cfg = TYPE_CONFIG[type]
                return (
                  <div key={type} className="flex flex-col items-center gap-1.5 text-slate-400">
                    <div className={cn('w-9 h-9 rounded-xl bg-slate-100 flex items-center justify-center', cfg.color)}>
                      {cfg.icon}
                    </div>
                    <span className="text-[10px] font-medium">{cfg.label}</span>
                  </div>
                )
              })}
            </div>
          </div>
        ) : results.length === 0 && !isFetching ? (
          <CommandEmpty>
            <div className="py-6 text-center text-sm text-slate-400">
              Nenhum resultado para "<span className="font-medium text-slate-600">{query}</span>"
            </div>
          </CommandEmpty>
        ) : (
          Object.entries(grouped).map(([type, items]) => {
            const cfg = TYPE_CONFIG[type as keyof typeof TYPE_CONFIG]
            return (
              <CommandGroup
                key={type}
                heading={
                  <span className={cn('flex items-center gap-1.5 text-xs font-semibold', cfg.color)}>
                    {cfg.icon} {cfg.label}
                  </span>
                }
              >
                {items.map((result) => (
                  <CommandItem
                    key={`${result.type}-${result.id}`}
                    value={`${result.type}-${result.id}-${result.title}`}
                    onSelect={() => handleSelect(result)}
                    className="flex items-start gap-3 py-2.5 cursor-pointer rounded-lg"
                  >
                    <div className={cn('mt-0.5 flex-shrink-0', cfg.color)}>{cfg.icon}</div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-900 truncate">{result.title}</p>
                      {result.subtitle && (
                        <p className="text-xs text-slate-400 truncate mt-0.5">{result.subtitle}</p>
                      )}
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>
            )
          })
        )}
      </CommandList>
    </CommandDialog>
  )
}
