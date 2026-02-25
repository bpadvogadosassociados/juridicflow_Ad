import { Construction } from 'lucide-react'

interface PlaceholderPageProps {
  title: string
  description?: string
}

export function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3 text-slate-400">
      <Construction size={32} />
      <h2 className="text-lg font-semibold text-slate-600">{title}</h2>
      <p className="text-sm text-slate-400">
        {description ?? 'Esta página será implementada nas próximas sprints.'}
      </p>
    </div>
  )
}
