import { Activity, Sparkles } from 'lucide-react'

export function ComingAndamentosPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="w-20 h-20 rounded-2xl bg-blue-100 flex items-center justify-center mb-6">
        <Activity size={36} className="text-blue-500" />
      </div>
      <h1 className="text-2xl font-bold text-slate-800 mb-2">Andamentos</h1>
      <p className="text-slate-500 max-w-sm mb-1">Módulo em desenvolvimento.</p>
      <p className="text-slate-400 text-sm max-w-xs">
        Acompanhe em tempo real os andamentos e movimentações processuais, com integração automática aos tribunais.
      </p>
      <div className="mt-6 flex items-center gap-2 text-xs text-blue-400 bg-blue-50 px-4 py-2 rounded-full">
        <Sparkles size={12} /> Em breve
      </div>
    </div>
  )
}
