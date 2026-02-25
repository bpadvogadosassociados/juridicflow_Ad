import { useState, useEffect, useRef, useCallback } from 'react'
import { Menu, Search, ChevronDown, Building2, Check, MessageCircle, Send, X, Users, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuSeparator, DropdownMenuTrigger, DropdownMenuLabel,
} from '@/components/ui/dropdown-menu'
import { GlobalSearch } from '@/components/shared/GlobalSearch'
import { NotificationPanel } from '@/components/shared/NotificationPanel'
import { useUIStore } from '@/store/uiStore'
import { useAuthStore } from '@/store/authStore'
import { authApi } from '@/api/auth'
import api from '@/api/client'
import { cn, initials } from '@/lib/utils'

// ── Chat types ────────────────────────────────────────────────────────────
interface ChatThread {
  id: number
  type: 'direct' | 'group'
  title: string
  last_message?: { body: string; sender: string; created_at: string }
  unread_count?: number
}

interface ChatMessage {
  id: number
  sender_name: string
  sender_id: number
  body: string
  created_at: string
}

export function Header() {
  const { toggleSidebar } = useUIStore()
  const { officeId, setOffice, setPermissions, memberships, user } = useAuthStore()
  const [searchOpen, setSearchOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)

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
          variant="ghost" size="icon"
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

        <div className="flex-1" />

        {/* Office switcher */}
        {hasMultipleOffices && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="h-9 gap-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 max-w-[200px]">
                <Building2 size={15} className="text-slate-400 flex-shrink-0" />
                <span className="truncate text-sm font-medium">{currentMembership?.office.name ?? 'Escritório'}</span>
                <ChevronDown size={13} className="text-slate-400 flex-shrink-0" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel className="text-xs text-slate-500 font-normal">Trocar escritório</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {memberships.map((m) => (
                <DropdownMenuItem key={m.id} onClick={() => handleSelectOffice(m.office.id)} className="gap-2 cursor-pointer">
                  <Building2 size={14} className="text-slate-400" />
                  <span className="flex-1 truncate">{m.office.name}</span>
                  {m.office.id === officeId && <Check size={13} className="text-blue-600" />}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}

        {/* Chat button */}
        <Button
          variant="ghost" size="icon"
          onClick={() => setChatOpen(v => !v)}
          className={cn('h-9 w-9 relative', chatOpen && 'bg-slate-100')}
          title="Chat"
        >
          <MessageCircle size={18} className="text-slate-500" />
        </Button>

        {/* Notifications */}
        <NotificationPanel />
      </header>

      {/* Chat panel */}
      {chatOpen && (
        <ChatPanel userId={user?.id ?? 0} onClose={() => setChatOpen(false)} />
      )}

      {/* Global search dialog */}
      <GlobalSearch open={searchOpen} onOpenChange={setSearchOpen} />
    </>
  )
}

// ── Chat Panel ──────────────────────────────────────────────────────────────
function ChatPanel({ userId, onClose }: { userId: number; onClose: () => void }) {
  const [threads, setThreads] = useState<ChatThread[]>([])
  const [activeThread, setActiveThread] = useState<ChatThread | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [messageText, setMessageText] = useState('')
  const [loading, setLoading] = useState(false)
  const [polling, setPolling] = useState<ReturnType<typeof setInterval> | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })

  // Load threads
  const loadThreads = useCallback(async () => {
    try {
      const r = await api.get('/app/api/chat/threads/')
      const data = r.data
      setThreads(Array.isArray(data) ? data : (data.threads ?? data.results ?? []))
    } catch {
      // Chat API not available yet
      setThreads([])
    }
  }, [])

  useEffect(() => {
    loadThreads()
  }, [loadThreads])

  // Load messages for active thread
  const loadMessages = useCallback(async (threadId: number) => {
    try {
      const r = await api.get(`/app/api/chat/thread/${threadId}/messages/`)
      const data = r.data
      setMessages(Array.isArray(data) ? data : (data.messages ?? []))
      setTimeout(scrollToBottom, 100)
    } catch {
      setMessages([])
    }
  }, [])

  useEffect(() => {
    if (!activeThread) return
    loadMessages(activeThread.id)
    const interval = setInterval(() => loadMessages(activeThread.id), 3000)
    setPolling(interval)
    return () => clearInterval(interval)
  }, [activeThread, loadMessages])

  const sendMessage = async () => {
    if (!messageText.trim() || !activeThread) return
    const body = messageText.trim()
    setMessageText('')
    try {
      await api.post(`/app/api/chat/thread/${activeThread.id}/send/`, { body })
      loadMessages(activeThread.id)
    } catch {
      setMessageText(body)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  return (
    <div className="fixed right-4 bottom-4 z-50 w-[480px] h-[460px] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 flex-shrink-0">
        <div className="flex items-center gap-2">
          <MessageCircle size={16} className="text-blue-600" />
          <span className="font-semibold text-sm text-slate-800">Chat</span>
          {activeThread && (
            <span className="text-slate-400 text-xs">
              · {activeThread.title || `Thread #${activeThread.id}`}
            </span>
          )}
        </div>
        <div className="flex gap-1">
          {activeThread && (
            <button onClick={() => { setActiveThread(null); setMessages([]) }}
              className="p-1 rounded hover:bg-slate-100 text-slate-400 text-xs mr-1">
              ← Voltar
            </button>
          )}
          <button className="p-1 rounded hover:bg-slate-100" title="Participantes">
            <Users size={14} className="text-slate-400" />
          </button>
          <button onClick={onClose} className="p-1 rounded hover:bg-slate-100">
            <X size={14} className="text-slate-400" />
          </button>
        </div>
      </div>

      {!activeThread ? (
        /* Thread list */
        <div className="flex-1 overflow-y-auto">
          {threads.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-6">
              <MessageCircle size={32} className="text-slate-200 mb-2" />
              <p className="text-sm text-slate-400">Nenhuma conversa</p>
              <p className="text-xs text-slate-300 mt-1">O chat estará disponível em breve.</p>
            </div>
          ) : (
            threads.map(t => (
              <button
                key={t.id}
                onClick={() => setActiveThread(t)}
                className="w-full flex items-start gap-3 px-4 py-3 hover:bg-slate-50 transition-colors text-left border-b border-slate-50"
              >
                <div className="w-9 h-9 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 text-sm font-semibold flex-shrink-0">
                  {t.title ? initials(t.title) : 'G'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">{t.title || `Thread #${t.id}`}</p>
                  {t.last_message && (
                    <p className="text-xs text-slate-400 truncate">{t.last_message.body}</p>
                  )}
                </div>
                {(t.unread_count ?? 0) > 0 && (
                  <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-[10px] flex items-center justify-center flex-shrink-0">
                    {t.unread_count}
                  </span>
                )}
              </button>
            ))
          )}
        </div>
      ) : (
        /* Messages view */
        <>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && (
              <p className="text-xs text-slate-400 text-center py-4">Nenhuma mensagem ainda. Diga olá!</p>
            )}
            {messages.map(msg => {
              const isMe = msg.sender_id === userId
              return (
                <div key={msg.id} className={cn('flex gap-2', isMe && 'flex-row-reverse')}>
                  <div className={cn(
                    'max-w-[75%] px-3 py-2 rounded-2xl text-sm',
                    isMe
                      ? 'bg-blue-600 text-white rounded-br-sm'
                      : 'bg-slate-100 text-slate-800 rounded-bl-sm',
                  )}>
                    {!isMe && (
                      <p className="text-[10px] font-semibold mb-0.5 text-slate-500">{msg.sender_name}</p>
                    )}
                    <p className="leading-relaxed">{msg.body}</p>
                    <p className={cn('text-[10px] mt-1', isMe ? 'text-blue-200' : 'text-slate-400')}>
                      {new Date(msg.created_at).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                </div>
              )
            })}
            <div ref={messagesEndRef} />
          </div>

          {/* Message input */}
          <div className="flex items-end gap-2 p-3 border-t border-slate-100 flex-shrink-0">
            <textarea
              value={messageText}
              onChange={e => setMessageText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Digite uma mensagem…"
              className="flex-1 resize-none rounded-xl border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 max-h-24 min-h-[40px]"
              rows={1}
            />
            <button
              onClick={sendMessage}
              disabled={!messageText.trim()}
              className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center text-white disabled:opacity-40 hover:bg-blue-700 transition-colors flex-shrink-0"
            >
              <Send size={15} />
            </button>
          </div>
        </>
      )}
    </div>
  )
}
