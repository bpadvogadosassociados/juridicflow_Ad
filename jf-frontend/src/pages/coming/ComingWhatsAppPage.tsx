import { MessageSquare, Sparkles } from 'lucide-react'

export function ComingWhatsAppPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="w-20 h-20 rounded-2xl bg-emerald-100 flex items-center justify-center mb-6">
        <MessageSquare size={36} className="text-emerald-500" />
      </div>
      <h1 className="text-2xl font-bold text-slate-800 mb-2">WhatsApp</h1>
      <p className="text-slate-500 max-w-sm mb-1">Integração em desenvolvimento.</p>
      <p className="text-slate-400 text-sm max-w-xs">
        Envie e receba mensagens do WhatsApp Business diretamente no JuridicFlow, vinculadas a processos e contatos.
      </p>
      <div className="mt-6 flex items-center gap-2 text-xs text-emerald-500 bg-emerald-50 px-4 py-2 rounded-full">
        <Sparkles size={12} /> Em breve
      </div>
    </div>
  )
}
