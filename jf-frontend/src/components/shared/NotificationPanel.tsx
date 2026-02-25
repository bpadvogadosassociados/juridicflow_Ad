import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Bell, Info, AlertTriangle, CheckCircle, XCircle, Clock, FileText, CheckSquare } from 'lucide-react'
import { cn } from '@/lib/utils'
import { notificationsApi, type Notification } from '@/api/notifications'

const TYPE_ICON: Record<string, React.ReactNode> = {
  info: <Info size={14} className="text-blue-500" />,
  warning: <AlertTriangle size={14} className="text-amber-500" />,
  success: <CheckCircle size={14} className="text-emerald-500" />,
  error: <XCircle size={14} className="text-red-500" />,
  deadline: <Clock size={14} className="text-orange-500" />,
  publication: <FileText size={14} className="text-violet-500" />,
  task: <CheckSquare size={14} className="text-slate-500" />,
}

export function NotificationPanel() {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()

  const { data } = useQuery({
    queryKey: ['notifications'],
    queryFn: notificationsApi.list,
    refetchInterval: 60_000, // Polling a cada 60s
    retry: false,
    throwOnError: false,
  })

  const markReadMutation = useMutation({
    mutationFn: notificationsApi.markRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })

  const markAllMutation = useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })

  // Normaliza resposta: suporta array direto ou objeto paginado
  const notifications: Notification[] = Array.isArray(data)
    ? (data as unknown as Notification[])
    : (data?.results ?? [])

  const unreadCount = Array.isArray(data)
    ? (data as unknown as Notification[]).filter((n) => !n.is_read).length
    : (data?.unread_count ?? notifications.filter((n) => !n.is_read).length)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative text-sidebar-foreground hover:bg-sidebar-accent h-9 w-9">
          <Bell size={18} />
          {unreadCount > 0 && (
            <span className="absolute top-1.5 right-1.5 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center leading-none">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent align="end" className="w-80 p-0 shadow-lg border-slate-200">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-900">
            Notificações
            {unreadCount > 0 && (
              <span className="ml-2 text-xs text-slate-500 font-normal">
                {unreadCount} não lida{unreadCount !== 1 ? 's' : ''}
              </span>
            )}
          </h3>
          {unreadCount > 0 && (
            <button
              onClick={() => markAllMutation.mutate()}
              className="text-xs text-blue-600 hover:text-blue-700 font-medium"
            >
              Marcar todas
            </button>
          )}
        </div>

        {/* Lista */}
        <ScrollArea className="max-h-80">
          {!notifications.length ? (
            <div className="py-8 text-center text-sm text-slate-400">
              Nenhuma notificação
            </div>
          ) : (
            <div className="divide-y divide-slate-50">
              {notifications.map((n) => (
                <NotificationItem
                  key={n.id}
                  notification={n}
                  onMarkRead={() => markReadMutation.mutate(n.id)}
                />
              ))}
            </div>
          )}
        </ScrollArea>
      </PopoverContent>
    </Popover>
  )
}

function NotificationItem({
  notification: n,
  onMarkRead,
}: {
  notification: Notification
  onMarkRead: () => void
}) {
  return (
    <div
      className={cn(
        'flex gap-3 px-4 py-3 cursor-pointer hover:bg-slate-50 transition-colors',
        !n.is_read && 'bg-blue-50/40',
      )}
      onClick={() => {
        if (!n.is_read) onMarkRead()
        if (n.url) window.location.href = n.url
      }}
    >
      <div className="mt-0.5 flex-shrink-0">{TYPE_ICON[n.type] ?? <Bell size={14} />}</div>
      <div className="flex-1 min-w-0">
        <p className={cn('text-xs font-medium truncate', !n.is_read ? 'text-slate-900' : 'text-slate-600')}>
          {n.title}
        </p>
        <p className="text-xs text-slate-500 line-clamp-2 mt-0.5">{n.message}</p>
        <p className="text-[11px] text-slate-400 mt-1">{n.when}</p>
      </div>
      {!n.is_read && (
        <div className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 flex-shrink-0" />
      )}
    </div>
  )
}
