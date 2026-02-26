import { createBrowserRouter, Navigate } from 'react-router-dom'
import { ProtectedRoute } from './ProtectedRoute'
import { AppLayout } from '@/components/layout/AppLayout'
import { LoginPage } from '@/pages/auth/LoginPage'
import { ChooseOfficePage } from '@/pages/auth/ChooseOfficePage'
import { DashboardPage } from '@/pages/dashboard/DashboardPage'

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
const SettingsPage = lazy(() => import('@/pages/settings/SettingsPage').then(m => ({ default: m.SettingsPage })))
const TeamPage = lazy(() => import('@/pages/team/TeamPage').then(m => ({ default: m.TeamPage })))

// Coming soon pages
const ComingWhatsAppPage = lazy(() => import('@/pages/coming/ComingWhatsAppPage').then(m => ({ default: m.ComingWhatsAppPage })))
const ComingAndamentosPage = lazy(() => import('@/pages/coming/ComingAndamentosPage').then(m => ({ default: m.ComingAndamentosPage })))

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/escolher-escritorio',
    element: <ChooseOfficePage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          // Dashboard
          { path: '/app/dashboard', element: <DashboardPage /> },

          // Processos
          { path: 'app/processos', element: <ProcessListPage /> },
          { path: 'app/processos/novo', element: <ProcessFormPage /> },
          { path: 'app/processos/:id', element: <ProcessDetailPage /> },
          { path: 'app/processos/:id/editar', element: <ProcessFormPage /> },

          // Contatos
          { path: 'app/contatos', element: <CustomerListPage /> },
          { path: 'app/contatos/pipeline', element: <CustomerPipelinePage /> },
          { path: 'app/contatos/novo', element: <CustomerFormPage /> },
          { path: 'app/contatos/:id', element: <CustomerDetailPage /> },
          { path: 'app/contatos/:id/editar', element: <CustomerFormPage /> },

          // Prazos
          { path: 'app/prazos', element: <DeadlineListPage /> },
          { path: 'app/prazos/calendario', element: <DeadlineCalendarPage /> },

          // Tarefas
          { path: 'app/tarefas', element: <TaskListPage /> },
          { path: 'app/tarefas/kanban', element: <TaskKanbanPage /> },

          // Documentos
          { path: 'app/documentos', element: <DocumentListPage /> },
          { path: 'app/documentos/:id', element: <DocumentDetailPage /> },

          // Financeiro
          { path: 'app/financeiro', element: <FinanceDashboardPage /> },
          { path: 'app/financeiro/contratos', element: <AgreementListPage /> },
          { path: 'app/financeiro/contratos/:id', element: <AgreementDetailPage /> },
          { path: 'app/financeiro/faturas', element: <InvoiceListPage /> },
          { path: 'app/financeiro/despesas', element: <ExpenseListPage /> },
          { path: 'app/financeiro/propostas', element: <ProposalListPage /> },

          // Agenda
          { path: 'app/agenda', element: <CalendarPage /> },

          // Andamentos (coming soon)
          { path: 'app/andamentos', element: <ComingAndamentosPage /> },

          // WhatsApp (coming soon)
          { path: 'app/whatsapp', element: <ComingWhatsAppPage /> },

          // Atividade (Relatórios)
          { path: 'app/relatorios', element: <ReportsDashboardPage /> },

          // Equipe
          { path: 'app/equipe', element: <TeamPage /> },

          // Configurações
          { path: 'app/configuracoes', element: <SettingsPage /> },
        ],
      },
    ],
  },

  // Redirect raiz
  { path: '/', element: <Navigate to="/app/dashboard" replace /> },
  { path: '*', element: <Navigate to="/app/dashboard" replace /> },
])
