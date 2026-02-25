import { Users, Sparkles } from 'lucide-react'

export function ComingTeamPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="w-20 h-20 rounded-2xl bg-indigo-100 flex items-center justify-center mb-6">
        <Users size={36} className="text-indigo-500" />
      </div>
      <h1 className="text-2xl font-bold text-slate-800 mb-2">Equipe</h1>
      <p className="text-slate-500 max-w-sm mb-1">Funcionalidade em desenvolvimento.</p>
      <p className="text-slate-400 text-sm max-w-xs">
        Em breve você poderá gerenciar toda a estrutura de equipes, hierarquias e colaboração aqui.
      </p>
      <div className="mt-6 flex items-center gap-2 text-xs text-indigo-400 bg-indigo-50 px-4 py-2 rounded-full">
        <Sparkles size={12} /> Em breve
      </div>
    </div>
  )
}
