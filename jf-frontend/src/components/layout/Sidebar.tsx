import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Scale,
  Users,
  Clock,
  CheckSquare,
  FileText,
  DollarSign,
  CalendarDays,
  BarChart3,
  UserCog,
  Settings,
  ChevronRight,
  LogOut,
  Building2,
  MessageSquare,
  Activity,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/authStore'
import { useUIStore } from '@/store/uiStore'
import { initials } from '@/lib/utils'
import { useState } from 'react'

interface NavItem {
  label: string
  href: string
  icon: React.ReactNode
  children?: { label: string; href: string }[]
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: '/app/dashboard', icon: <LayoutDashboard size={18} /> },
  { label: 'Processos', href: '/app/processos', icon: <Scale size={18} /> },
  {
    label: 'Contatos',
    href: '/app/contatos',
    icon: <Users size={18} />,
    children: [
      { label: 'Lista', href: '/app/contatos' },
      { label: 'Pipeline', href: '/app/contatos/pipeline' },
    ],
  },
  {
    label: 'Prazos',
    href: '/app/prazos',
    icon: <Clock size={18} />,
    children: [
      { label: 'Lista', href: '/app/prazos' },
      { label: 'Calendário', href: '/app/prazos/calendario' },
    ],
  },
  {
    label: 'Tarefas',
    href: '/app/tarefas',
    icon: <CheckSquare size={18} />,
    children: [
      { label: 'Kanban', href: '/app/tarefas/kanban' },
      { label: 'Lista', href: '/app/tarefas' },
    ],
  },
  { label: 'Documentos', href: '/app/documentos', icon: <FileText size={18} /> },
  {
    label: 'Financeiro',
    href: '/app/financeiro',
    icon: <DollarSign size={18} />,
    children: [
      { label: 'Visão Geral', href: '/app/financeiro' },
      { label: 'Contratos', href: '/app/financeiro/contratos' },
      { label: 'Faturas', href: '/app/financeiro/faturas' },
      { label: 'Despesas', href: '/app/financeiro/despesas' },
      { label: 'Propostas', href: '/app/financeiro/propostas' },
    ],
  },
  { label: 'Agenda', href: '/app/agenda', icon: <CalendarDays size={18} /> },
  { label: 'Andamentos', href: '/app/andamentos', icon: <Activity size={18} /> },
  { label: 'WhatsApp', href: '/app/whatsapp', icon: <MessageSquare size={18} /> },
  { label: 'Atividade', href: '/app/relatorios', icon: <Activity size={18} /> },
]

const BOTTOM_NAV: NavItem[] = [
  { label: 'Equipe', href: '/app/equipe', icon: <Users size={18} /> },
  { label: 'Configurações', href: '/app/configuracoes', icon: <Settings size={18} /> },
]

export function Sidebar() {
  const { sidebarCollapsed } = useUIStore()
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())

  const toggleExpand = (href: string) =>
    setExpandedItems(prev => {
      const next = new Set(prev)
      next.has(href) ? next.delete(href) : next.add(href)
      return next
    })

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <aside
      className={cn(
        'flex flex-col bg-slate-900 text-sidebar-foreground transition-all duration-300 flex-shrink-0',
        sidebarCollapsed ? 'w-[64px]' : 'w-60',
      )}
      style={{ colorScheme: 'dark' }}
    >
      {/* Logo */}
      <div className={cn('flex items-center h-16 border-b border-white/10 flex-shrink-0', sidebarCollapsed ? 'justify-center px-0' : 'px-5 gap-2')}>
        {!sidebarCollapsed ? (
          <span className="text-white font-bold text-base tracking-tight">JuridicFlow</span>
        ) : (
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">JF</div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5 scrollbar-thin">
        {NAV_ITEMS.map(item => (
          <NavItemComponent
            key={item.href}
            item={item}
            collapsed={sidebarCollapsed}
            expanded={expandedItems.has(item.href)}
            onToggleExpand={() => toggleExpand(item.href)}
          />
        ))}
      </nav>

      {/* Bottom nav */}
      <div className="px-3 py-3 border-t border-white/10 space-y-0.5">
        {BOTTOM_NAV.map(item => (
          <NavItemComponent
            key={item.href}
            item={item}
            collapsed={sidebarCollapsed}
            expanded={expandedItems.has(item.href)}
            onToggleExpand={() => toggleExpand(item.href)}
          />
        ))}
      </div>

      {/* User */}
      <div className={cn('flex items-center gap-2.5 px-3 py-3 border-t border-white/10', sidebarCollapsed && 'justify-center')}>
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white text-xs font-semibold flex-shrink-0">
          {initials(user ? `${user.first_name} ${user.last_name}` : user?.email ?? '?')}
        </div>

        {!sidebarCollapsed && (
          <>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-sidebar-foreground truncate">
                {user?.first_name} {user?.last_name}
              </p>
              <p className="text-[11px] text-sidebar-foreground/50 truncate">{user?.email}</p>
            </div>
            <button
              onClick={handleLogout}
              className="text-sidebar-foreground/40 hover:text-red-400 transition-colors p-1 rounded"
              title="Sair"
            >
              <LogOut size={15} />
            </button>
          </>
        )}
      </div>
    </aside>
  )
}

interface NavItemComponentProps {
  item: NavItem
  collapsed: boolean
  expanded: boolean
  onToggleExpand: () => void
}

function NavItemComponent({ item, collapsed, expanded, onToggleExpand }: NavItemComponentProps) {
  const hasChildren = item.children && item.children.length > 0

  const baseClass =
    'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 cursor-pointer select-none'
  const activeClass = 'bg-sidebar-accent text-white'
  const inactiveClass = 'text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground'

  if (hasChildren && !collapsed) {
    return (
      <div>
        <button
          className={cn(baseClass, inactiveClass, 'w-full justify-between')}
          onClick={onToggleExpand}
        >
          <span className="flex items-center gap-3">
            {item.icon}
            {item.label}
          </span>
          <ChevronRight
            size={14}
            className={cn('transition-transform duration-200', expanded && 'rotate-90')}
          />
        </button>

        {expanded && (
          <div className="ml-9 mt-0.5 space-y-0.5">
            {item.children!.map((child) => (
              <NavLink
                key={child.href}
                to={child.href}
                end={child.href === item.href}
                className={({ isActive }) =>
                  cn(
                    'flex items-center py-1.5 px-2 rounded-md text-xs transition-colors',
                    isActive
                      ? 'text-blue-400 font-medium'
                      : 'text-sidebar-foreground/50 hover:text-sidebar-foreground',
                  )
                }
              >
                {child.label}
              </NavLink>
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <NavLink
      to={item.href}
      end={!hasChildren}
      className={({ isActive }) => cn(baseClass, isActive ? activeClass : inactiveClass)}
      title={collapsed ? item.label : undefined}
    >
      <span className="flex-shrink-0">{item.icon}</span>
      {!collapsed && <span>{item.label}</span>}
    </NavLink>
  )
}
