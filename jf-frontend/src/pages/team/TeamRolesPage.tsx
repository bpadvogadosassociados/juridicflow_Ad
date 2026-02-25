import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Shield, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/layout/PageHeader'

const ROLES = [
  {
    key: 'org_admin',
    label: 'Admin Organização',
    color: 'bg-violet-100 text-violet-700',
    description: 'Controle total sobre a organização e todos os escritórios.',
    permissions: [
      'Gerenciar membros e funções',
      'Criar/excluir escritórios',
      'Acesso a todos os módulos',
      'Configurações globais',
      'Relatórios financeiros completos',
    ],
  },
  {
    key: 'office_admin',
    label: 'Admin Escritório',
    color: 'bg-blue-100 text-blue-700',
    description: 'Controle completo dentro do escritório selecionado.',
    permissions: [
      'Gerenciar membros do escritório',
      'Todos os processos e prazos',
      'Documentos e financeiro',
      'Relatórios do escritório',
      'Configurações do escritório',
    ],
  },
  {
    key: 'lawyer',
    label: 'Advogado',
    color: 'bg-emerald-100 text-emerald-700',
    description: 'Acesso operacional completo para trabalho diário.',
    permissions: [
      'Criar e editar processos',
      'Gerenciar prazos e agenda',
      'Upload de documentos',
      'CRM de clientes',
      'Tarefas e Kanban',
    ],
  },
  {
    key: 'intern',
    label: 'Estagiário',
    color: 'bg-amber-100 text-amber-700',
    description: 'Acesso de leitura e operações básicas supervisionadas.',
    permissions: [
      'Visualizar processos',
      'Gerenciar próprias tarefas',
      'Upload de documentos',
      'Visualizar agenda',
      'CRM (somente leitura)',
    ],
  },
  {
    key: 'finance',
    label: 'Financeiro',
    color: 'bg-slate-100 text-slate-700',
    description: 'Foco em operações financeiras do escritório.',
    permissions: [
      'Contratos de honorários',
      'Faturas e pagamentos',
      'Despesas operacionais',
      'Propostas comerciais',
      'Relatórios financeiros',
    ],
  },
]

export function TeamRolesPage() {
  const navigate = useNavigate()

  return (
    <div className="max-w-5xl mx-auto page-enter">
      <PageHeader
        title="Funções e Permissões"
        subtitle="Entenda o que cada função pode fazer no sistema"
        breadcrumbs={[{ label: 'Equipe', href: '/app/equipe' }, { label: 'Funções' }]}
        actions={
          <Button variant="outline" size="sm" onClick={() => navigate('/app/equipe')} className="gap-2">
            <ArrowLeft size={14} /> Voltar
          </Button>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {ROLES.map(role => (
          <Card key={role.key} className="border-slate-200 shadow-sm">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2 mb-1">
                <Shield size={15} className="text-slate-400" />
                <span className={`text-xs font-bold px-2 py-0.5 rounded-md ${role.color}`}>
                  {role.label}
                </span>
              </div>
              <CardTitle className="text-xs text-slate-500 font-normal">{role.description}</CardTitle>
            </CardHeader>
            <CardContent className="pt-0 space-y-1.5">
              {role.permissions.map(perm => (
                <div key={perm} className="flex items-center gap-2">
                  <Check size={11} className="text-emerald-500 flex-shrink-0" />
                  <span className="text-xs text-slate-600">{perm}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-xl">
        <p className="text-xs text-amber-800">
          <strong>Nota:</strong> As permissões são gerenciadas via Django Admin pelo administrador do sistema.
          Para ajustes granulares de permissões, acesse o painel administrativo do backend.
        </p>
      </div>
    </div>
  )
}
