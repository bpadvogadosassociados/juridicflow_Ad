import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, Edit, MoreHorizontal, X, Check } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/dialog'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { PageHeader } from '@/components/layout/PageHeader'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { kanbanApi, type KanbanCard, type KanbanColumn } from '@/api/kanban'
import { formatRelative } from '@/lib/utils'
import { cn } from '@/lib/utils'

export function KanbanPage() {
  const queryClient = useQueryClient()
  const [draggingCard, setDraggingCard] = useState<{ id: number; fromColumn: number } | null>(null)
  const [overColumn, setOverColumn] = useState<number | null>(null)
  const [newColumnTitle, setNewColumnTitle] = useState('')
  const [addingColumn, setAddingColumn] = useState(false)
  const [editingColumn, setEditingColumn] = useState<{ id: number; title: string } | null>(null)
  const [cardModal, setCardModal] = useState<{ open: boolean; columnId: number | null; card: KanbanCard | null }>({ open: false, columnId: null, card: null })
  const [cardForm, setCardForm] = useState({ title: '', body_md: '' })
  const [deleteCard, setDeleteCard] = useState<KanbanCard | null>(null)
  const [deleteColumn, setDeleteColumn] = useState<KanbanColumn | null>(null)

  const { data: board, isLoading } = useQuery({
    queryKey: ['kanban-board'],
    queryFn: kanbanApi.getBoard,
    staleTime: 30_000,
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['kanban-board'] })

  const createColumnMutation = useMutation({
    mutationFn: (title: string) => kanbanApi.createColumn({ title, order: (board?.columns.length ?? 0) }),
    onSuccess: () => { toast.success('Coluna criada.'); invalidate(); setAddingColumn(false); setNewColumnTitle('') },
    onError: () => toast.error('Erro ao criar coluna.'),
  })

  const updateColumnMutation = useMutation({
    mutationFn: ({ id, title }: { id: number; title: string }) => kanbanApi.updateColumn(id, { title }),
    onSuccess: () => { invalidate(); setEditingColumn(null) },
    onError: () => toast.error('Erro ao renomear.'),
  })

  const deleteColumnMutation = useMutation({
    mutationFn: (id: number) => kanbanApi.deleteColumn(id),
    onSuccess: () => { toast.success('Coluna excluída.'); invalidate(); setDeleteColumn(null) },
    onError: () => toast.error('Erro ao excluir coluna.'),
  })

  const createCardMutation = useMutation({
    mutationFn: ({ columnId, title, body_md }: { columnId: number; title: string; body_md: string }) =>
      kanbanApi.createCard({ column: columnId, title, body_md, order: 0 }),
    onSuccess: () => { toast.success('Card criado.'); invalidate(); setCardModal({ open: false, columnId: null, card: null }) },
    onError: () => toast.error('Erro ao criar card.'),
  })

  const updateCardMutation = useMutation({
    mutationFn: ({ id, title, body_md }: { id: number; title: string; body_md: string }) =>
      kanbanApi.updateCard(id, { title, body_md }),
    onSuccess: () => { toast.success('Card atualizado.'); invalidate(); setCardModal({ open: false, columnId: null, card: null }) },
    onError: () => toast.error('Erro ao atualizar card.'),
  })

  const moveCardMutation = useMutation({
    mutationFn: ({ id, column }: { id: number; column: number }) => kanbanApi.updateCard(id, { column }),
    onSuccess: () => invalidate(),
    onError: () => toast.error('Erro ao mover card.'),
  })

  const deleteCardMutation = useMutation({
    mutationFn: (id: number) => kanbanApi.deleteCard(id),
    onSuccess: () => { toast.success('Card excluído.'); invalidate(); setDeleteCard(null) },
    onError: () => toast.error('Erro ao excluir card.'),
  })

  const handleDrop = (targetColumnId: number) => {
    if (draggingCard && draggingCard.fromColumn !== targetColumnId) {
      moveCardMutation.mutate({ id: draggingCard.id, column: targetColumnId })
    }
    setDraggingCard(null)
    setOverColumn(null)
  }

  const openAddCard = (columnId: number) => {
    setCardForm({ title: '', body_md: '' })
    setCardModal({ open: true, columnId, card: null })
  }

  const openEditCard = (card: KanbanCard) => {
    setCardForm({ title: card.title, body_md: card.body_md })
    setCardModal({ open: true, columnId: card.column, card })
  }

  const handleCardSave = () => {
    if (!cardForm.title.trim()) return
    if (cardModal.card) {
      updateCardMutation.mutate({ id: cardModal.card.id, ...cardForm })
    } else if (cardModal.columnId !== null) {
      createCardMutation.mutate({ columnId: cardModal.columnId, ...cardForm })
    }
  }

  const isPendingCard = createCardMutation.isPending || updateCardMutation.isPending

  if (isLoading) return <BoardSkeleton />

  return (
    <div className="page-enter flex flex-col h-full">
      <PageHeader
        title="Kanban"
        subtitle={board?.title ?? 'Atividades'}
        breadcrumbs={[{ label: 'JuridicFlow' }, { label: 'Kanban' }]}
      />

      {/* Board */}
      <div className="flex gap-4 overflow-x-auto pb-6 flex-1 items-start">
        {board?.columns.map((column) => (
          <div
            key={column.id}
            className={cn(
              'flex-shrink-0 w-72 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col transition-all duration-150',
              overColumn === column.id && 'bg-blue-50/60 border-blue-300 ring-2 ring-blue-200',
            )}
            onDragOver={(e) => { e.preventDefault(); setOverColumn(column.id) }}
            onDragLeave={(e) => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setOverColumn(null) }}
            onDrop={() => handleDrop(column.id)}
          >
            {/* Column header */}
            <div className="flex items-center gap-2 px-3 py-2.5 border-b border-slate-200/70">
              {editingColumn?.id === column.id ? (
                <div className="flex gap-1.5 flex-1">
                  <Input
                    value={editingColumn.title}
                    onChange={(e) => setEditingColumn({ ...editingColumn, title: e.target.value })}
                    className="h-7 text-xs"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') updateColumnMutation.mutate({ id: column.id, title: editingColumn.title })
                      if (e.key === 'Escape') setEditingColumn(null)
                    }}
                  />
                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => updateColumnMutation.mutate({ id: column.id, title: editingColumn.title })}>
                    <Check size={12} className="text-emerald-600" />
                  </Button>
                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => setEditingColumn(null)}>
                    <X size={12} />
                  </Button>
                </div>
              ) : (
                <>
                  <span className="text-xs font-semibold text-slate-700 flex-1">{column.title}</span>
                  <span className="text-[10px] text-slate-400 font-medium">{column.cards.length}</span>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-slate-400 hover:text-slate-600">
                        <MoreHorizontal size={13} />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="text-xs">
                      <DropdownMenuItem onClick={() => setEditingColumn({ id: column.id, title: column.title })}>
                        <Edit size={12} className="mr-2" /> Renomear
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className="text-red-600"
                        onClick={() => setDeleteColumn(column)}
                      >
                        <Trash2 size={12} className="mr-2" /> Excluir coluna
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </>
              )}
            </div>

            {/* Cards */}
            <div className="p-2 flex flex-col gap-2 flex-1 min-h-[80px]">
              {column.cards
                .sort((a, b) => a.order - b.order)
                .map((card) => (
                  <div
                    key={card.id}
                    draggable
                    onDragStart={() => setDraggingCard({ id: card.id, fromColumn: column.id })}
                    onDragEnd={() => { setDraggingCard(null); setOverColumn(null) }}
                    className={cn(
                      'bg-white rounded-lg border border-slate-200 p-3',
                      'hover:shadow-sm hover:border-slate-300 transition-all duration-150 cursor-grab active:cursor-grabbing',
                      draggingCard?.id === card.id && 'opacity-40 scale-95',
                    )}
                  >
                    <div className="flex items-start gap-1 justify-between mb-1">
                      <p className="text-xs font-medium text-slate-900 leading-tight flex-1">{card.title}</p>
                      <div className="flex gap-0.5 flex-shrink-0 opacity-0 group-hover:opacity-100" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => openEditCard(card)}
                          className="p-1 text-slate-300 hover:text-blue-500 transition-colors"
                        >
                          <Edit size={11} />
                        </button>
                        <button
                          onClick={() => setDeleteCard(card)}
                          className="p-1 text-slate-300 hover:text-red-500 transition-colors"
                        >
                          <Trash2 size={11} />
                        </button>
                      </div>
                    </div>
                    {card.body_md && (
                      <p className="text-[11px] text-slate-400 leading-relaxed line-clamp-2">{card.body_md}</p>
                    )}
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-[10px] text-slate-300 font-mono">#{card.number}</span>
                      <div className="flex gap-0.5">
                        <button onClick={() => openEditCard(card)} className="text-[10px] text-slate-300 hover:text-blue-500 px-1 transition-colors">editar</button>
                        <button onClick={() => setDeleteCard(card)} className="text-[10px] text-slate-300 hover:text-red-400 px-1 transition-colors">excluir</button>
                      </div>
                    </div>
                  </div>
                ))}

              {column.cards.length === 0 && draggingCard && (
                <div className="h-12 border-2 border-dashed border-blue-200 rounded-lg bg-blue-50/30 flex items-center justify-center">
                  <span className="text-[10px] text-blue-300">Solte aqui</span>
                </div>
              )}
            </div>

            {/* Add card button */}
            <div className="p-2 border-t border-slate-100">
              <Button
                variant="ghost" size="sm"
                className="w-full h-8 text-xs text-slate-400 hover:text-slate-600 gap-1.5 justify-start"
                onClick={() => openAddCard(column.id)}
              >
                <Plus size={12} /> Adicionar card
              </Button>
            </div>
          </div>
        ))}

        {/* Add column */}
        <div className="flex-shrink-0 w-72">
          {addingColumn ? (
            <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-3 space-y-2">
              <Input
                value={newColumnTitle}
                onChange={(e) => setNewColumnTitle(e.target.value)}
                placeholder="Nome da coluna"
                className="h-9 text-sm"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && newColumnTitle.trim()) createColumnMutation.mutate(newColumnTitle.trim())
                  if (e.key === 'Escape') { setAddingColumn(false); setNewColumnTitle('') }
                }}
              />
              <div className="flex gap-2">
                <Button
                  size="sm" className="bg-blue-600 hover:bg-blue-700 flex-1 h-8"
                  disabled={!newColumnTitle.trim() || createColumnMutation.isPending}
                  onClick={() => createColumnMutation.mutate(newColumnTitle.trim())}
                >
                  Criar
                </Button>
                <Button variant="outline" size="sm" className="h-8 w-8 p-0"
                  onClick={() => { setAddingColumn(false); setNewColumnTitle('') }}>
                  <X size={14} />
                </Button>
              </div>
            </div>
          ) : (
            <Button
              variant="outline"
              className="w-full h-10 border-dashed text-slate-400 hover:text-slate-600 gap-2 text-sm"
              onClick={() => setAddingColumn(true)}
            >
              <Plus size={14} /> Nova Coluna
            </Button>
          )}
        </div>
      </div>

      {/* Card Modal */}
      <Dialog open={cardModal.open} onOpenChange={(v) => setCardModal({ open: v, columnId: null, card: null })}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base">{cardModal.card ? 'Editar Card' : 'Novo Card'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-1">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-600">Título *</label>
              <Input
                value={cardForm.title}
                onChange={(e) => setCardForm(f => ({ ...f, title: e.target.value }))}
                placeholder="Título do card"
                className="text-sm"
                autoFocus
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-600">Descrição</label>
              <Textarea
                value={cardForm.body_md}
                onChange={(e) => setCardForm(f => ({ ...f, body_md: e.target.value }))}
                placeholder="Detalhes, contexto, links…"
                rows={4}
                className="resize-none text-sm"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setCardModal({ open: false, columnId: null, card: null })}>
              Cancelar
            </Button>
            <Button
              size="sm" className="bg-blue-600 hover:bg-blue-700"
              disabled={!cardForm.title.trim() || isPendingCard}
              onClick={handleCardSave}
            >
              {isPendingCard ? 'Salvando…' : cardModal.card ? 'Atualizar' : 'Criar Card'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete card */}
      <ConfirmDialog
        open={!!deleteCard}
        onOpenChange={(v) => { if (!v) setDeleteCard(null) }}
        title="Excluir card?"
        description={`"${deleteCard?.title}" será excluído permanentemente.`}
        confirmLabel="Excluir"
        variant="destructive"
        onConfirm={() => deleteCard && deleteCardMutation.mutate(deleteCard.id)}
        loading={deleteCardMutation.isPending}
      />

      {/* Delete column */}
      <ConfirmDialog
        open={!!deleteColumn}
        onOpenChange={(v) => { if (!v) setDeleteColumn(null) }}
        title="Excluir coluna?"
        description={`A coluna "${deleteColumn?.title}" e todos os seus cards serão excluídos.`}
        confirmLabel="Excluir"
        variant="destructive"
        onConfirm={() => deleteColumn && deleteColumnMutation.mutate(deleteColumn.id)}
        loading={deleteColumnMutation.isPending}
      />
    </div>
  )
}

function BoardSkeleton() {
  return (
    <div className="page-enter">
      <div className="h-8 w-32 bg-slate-100 rounded animate-pulse mb-6" />
      <div className="flex gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex-shrink-0 w-72 h-80 bg-slate-100 rounded-xl animate-pulse" />
        ))}
        <div className="flex-shrink-0 w-72 h-12 bg-slate-50 border border-dashed border-slate-200 rounded-xl animate-pulse" />
      </div>
    </div>
  )
}
