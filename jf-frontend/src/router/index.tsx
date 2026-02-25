import { createBrowserRouter, Navigate } from 'react-router-dom'
import { ProtectedRoute } from './ProtectedRoute'
import { AppLayout } from '@/components/layout/AppLayout'
import { LoginPage } from '@/pages/auth/LoginPage'
import { ChooseOfficePage } from '@/pages/auth/ChooseOfficePage'
import { DashboardPage } from '@/pages/dashboard/DashboardPage'

// Lazy placeholders para sprints futuras
import { lazy } from 'react'

const ProcessListPage = lazy(() => import('@/pages/processes/ProcessListPage').then(m => ({ default: m.ProcessListPage })))
const ProcessDetailPage = lazy(() => import('@/pages/processes/ProcessDetailPage').then(m => ({ default: m.ProcessDetailPage })))
const ProcessFormPage = lazy(() => import('@/pages/processes/ProcessFormPage').then(m => ({ default: m.ProcessFormPage })))

const CustomerListPage = lazy(() => import('@/pages/customers/CustomerListPage').then(m => ({ default: m.CustomerListPage })))
const CustomerPipelinePage = lazy(() => import('@/pages/customers/CustomerPipelinePage').then(m => ({ default: m.CustomerPipelinePage })))
const CustomerDetailPage = lazy(() => import('@/pages/customers/CustomerDetailPage').then(m => ({ default: m.CustomerDetailPage })))
const CustomerFormPage = lazy(() => import('@/pages/customers/CustomerFormPage').then(m => ({ default: m.CustomerFormPage })))

const DeadlineListPage = lazy(() => import('@/pages/deadlines/DeadlineListPage').then(m => ({ default: m.DeadlineListPage })))
const DeadlineCalendarPage = lazy(() => import('@/pages/deadlines/DeadlineCalendarPage').then(m => ({ default: m.DeadlineCalendarPage })))

const KanbanPage = lazy(() => import('@/pages/kanban/KanbanPage').then(m => ({ default: m.KanbanPage })))

const TaskListPage = lazy(() => import('@/pages/tasks/TaskListPage').then(m => ({ default: m.TaskListPage })))
const TaskKanbanPage = lazy(() => import('@/pages/tasks/TaskKanbanPage').then(m => ({ default: m.TaskKanbanPage })))

const DocumentListPage = lazy(() => import('@/pages/documents/DocumentListPage').then(m => ({ default: m.DocumentListPage })))
const DocumentDetailPage = lazy(() => import('@/pages/documents/DocumentDetailPage').then(m => ({ default: m.DocumentDetailPage })))

const FinanceDashboardPage = lazy(() => import('@/pages/finance/FinanceDashboardPage').then(m => ({ default: m.FinanceDashboardPage })))
const AgreementListPage = lazy(() => import('@/pages/finance/AgreementListPage').then(m => ({ default: m.AgreementListPage })))
const AgreementDetailPage = lazy(() => import('@/pages/finance/AgreementDetailPage').then(m => ({ default: m.AgreementDetailPage })))
const InvoiceListPage = lazy(() => import('@/pages/finance/InvoiceListPage').then(m => ({ default: m.InvoiceListPage })))
const ExpenseListPage = lazy(() => import('@/pages/finance/ExpenseListPage').then(m => ({ default: m.ExpenseListPage })))
const ProposalListPage = lazy(() => import('@/pages/finance/ProposalListPage').then(m => ({ default: m.ProposalListPage })))

const CalendarPage = lazy(() => import('@/pages/calendar/CalendarPage').then(m => ({ default: m.CalendarPage })))

const ReportsDashboardPage = lazy(() => import('@/pages/reports/ReportsDashboardPage').then(m => ({ default: m.ReportsDashboardPage })))

const TeamListPage = lazy(() => import('@/pages/team/TeamListPage').then(m => ({ default: m.TeamListPage })))
const TeamRolesPage = lazy(() => import('@/pages/team/TeamRolesPage').then(m => ({ default: m.TeamRolesPage })))

const SettingsPage = lazy(() => import('@/pages/settings/SettingsPage').then(m => ({ default: m.SettingsPage })))

export const router = createBrowserRouter([
  // Públicas
  { path: '/login', element: <LoginPage /> },

  // Seleção de escritório (autenticado, sem officeId)
  {
    element: <ProtectedRoute requireOffice={false} />,
    children: [{ path: '/escolher-escritorio', element: <ChooseOfficePage /> }],
  },

  // Área protegida — dentro do AppLayout
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: '/app',
        element: <AppLayout />,
        children: [
          { index: true, element: <Navigate to="/app/dashboard" replace /> },
          { path: 'dashboard', element: <DashboardPage /> },

          // Processos
          { path: 'processos', element: <ProcessListPage /> },
          { path: 'processos/novo', element: <ProcessFormPage /> },
          { path: 'processos/:id', element: <ProcessDetailPage /> },
          { path: 'processos/:id/editar', element: <ProcessFormPage /> },

          // Contatos
          { path: 'contatos', element: <CustomerListPage /> },
          { path: 'contatos/pipeline', element: <CustomerPipelinePage /> },
          { path: 'contatos/novo', element: <CustomerFormPage /> },
          { path: 'contatos/:id', element: <CustomerDetailPage /> },
          { path: 'contatos/:id/editar', element: <CustomerFormPage /> },

          // Prazos
          { path: 'prazos', element: <DeadlineListPage /> },
          { path: 'prazos/calendario', element: <DeadlineCalendarPage /> },

          // Kanban de atividades
          { path: 'kanban', element: <KanbanPage /> },

          // Tarefas
          { path: 'tarefas', element: <TaskListPage /> },
          { path: 'tarefas/kanban', element: <TaskKanbanPage /> },

          // Documentos
          { path: 'documentos', element: <DocumentListPage /> },
          { path: 'documentos/:id', element: <DocumentDetailPage /> },

          // Financeiro
          { path: 'financeiro', element: <FinanceDashboardPage /> },
          { path: 'financeiro/contratos', element: <AgreementListPage /> },
          { path: 'financeiro/contratos/:id', element: <AgreementDetailPage /> },
          { path: 'financeiro/faturas', element: <InvoiceListPage /> },
          { path: 'financeiro/despesas', element: <ExpenseListPage /> },
          { path: 'financeiro/propostas', element: <ProposalListPage /> },

          // Agenda
          { path: 'agenda', element: <CalendarPage /> },

          // Relatórios
          { path: 'relatorios', element: <ReportsDashboardPage /> },

          // Equipe
          { path: 'equipe', element: <TeamListPage /> },
          { path: 'equipe/funcoes', element: <TeamRolesPage /> },

          // Configurações
          { path: 'configuracoes', element: <SettingsPage /> },
        ],
      },
    ],
  },

  // Redirect raiz
  { path: '/', element: <Navigate to="/app/dashboard" replace /> },
  { path: '*', element: <Navigate to="/app/dashboard" replace /> },
])
