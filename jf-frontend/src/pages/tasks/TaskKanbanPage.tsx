import { useNavigate } from 'react-router-dom'
import { List } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/layout/PageHeader'
import { KanbanPage } from '@/pages/kanban/KanbanPage'

// TaskKanbanPage reutiliza o KanbanPage de atividades
// mas com header e breadcrumbs de Tarefas
export function TaskKanbanPage() {
  const navigate = useNavigate()
  return (
    <div className="page-enter">
      <div className="flex items-center justify-between mb-1">
        <div />
        <Button variant="outline" size="sm" onClick={() => navigate('/app/tarefas')} className="gap-2 h-8 text-xs">
          <List size={13} /> Ver como Lista
        </Button>
      </div>
      <KanbanPage />
    </div>
  )
}
