import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { Eye, EyeOff, Scale, Lock, Mail, ArrowRight, Shield, Zap, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { authApi } from '@/api/auth'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'

const schema = z.object({
  email: z.string().email('E-mail inválido'),
  password: z.string().min(1, 'Senha obrigatória'),
})
type FormData = z.infer<typeof schema>

const FEATURES = [
  {
    icon: <Scale size={16} />,
    title: 'Gestão de Processos',
    desc: 'Controle completo do ciclo de vida processual',
  },
  {
    icon: <Users size={16} />,
    title: 'CRM Jurídico',
    desc: 'Pipeline de clientes e leads integrado',
  },
  {
    icon: <Shield size={16} />,
    title: 'Multi-escritório',
    desc: 'Isolamento por tenant com permissões granulares',
  },
  {
    icon: <Zap size={16} />,
    title: 'Controle Financeiro',
    desc: 'Honorários, faturas e despesas em um só lugar',
  },
]

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)

  const { setTokens, setUser, setMemberships, setOffice, setPermissions } = useAuthStore()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: FormData) => {
    setLoading(true)
    try {
      // 1. Login → tokens
      const { access, refresh } = await authApi.login(data)
      setTokens(access, refresh)

      // 2. Dados do usuário
      const user = await authApi.me()
      setUser(user)

      // 3. Memberships
      const memberships = await authApi.memberships()
      setMemberships(memberships)

      // 4. Auto-selecionar se tiver só 1 escritório
      if (memberships.length === 1) {
        const officeId = memberships[0].office.id
        setOffice(officeId)

        const { permissions } = await authApi.permissions()
        setPermissions(permissions)

        const from = (location.state as { from?: Location })?.from?.pathname ?? '/app/dashboard'
        navigate(from, { replace: true })
      } else if (memberships.length > 1) {
        navigate('/escolher-escritorio', { replace: true })
      } else {
        toast.error('Nenhum escritório disponível para o seu usuário.')
      }
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ??
        err?.response?.data?.non_field_errors?.[0] ??
        'Credenciais inválidas.'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* ── Left panel — deep navy hero ───────────────────────────────────── */}
      <div className="hidden lg:flex lg:w-[52%] bg-slate-900 flex-col justify-between p-12 relative overflow-hidden">
        {/* Background decoration */}
        <div
          aria-hidden
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: `radial-gradient(circle at 20% 50%, #1d4ed8 0%, transparent 50%),
                              radial-gradient(circle at 80% 20%, #1e40af 0%, transparent 40%),
                              radial-gradient(circle at 60% 80%, #1e3a8a 0%, transparent 40%)`,
          }}
        />

        {/* Grid lines */}
        <div
          aria-hidden
          className="absolute inset-0 opacity-[0.04]"
          style={{
            backgroundImage: `linear-gradient(to right, #94a3b8 1px, transparent 1px),
                              linear-gradient(to bottom, #94a3b8 1px, transparent 1px)`,
            backgroundSize: '48px 48px',
          }}
        />

        {/* Content */}
        <div className="relative z-10">
          {/* Logo */}
          <div className="flex items-center gap-3 mb-16">
            <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center">
              <Scale size={18} className="text-white" />
            </div>
            <span className="text-xl font-bold text-white tracking-tight">
              Juridic<span className="text-blue-400">Flow</span>
            </span>
          </div>

          {/* Hero text */}
          <div className="mb-12">
            <h1 className="text-4xl font-bold text-white leading-tight mb-4">
              Gestão jurídica
              <br />
              <span className="text-blue-400">de alto nível.</span>
            </h1>
            <p className="text-slate-400 text-base leading-relaxed max-w-sm">
              Plataforma integrada para escritórios de advocacia modernos. Processos, clientes,
              prazos e financeiro em um único lugar.
            </p>
          </div>

          {/* Feature list */}
          <div className="grid grid-cols-2 gap-3">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="flex gap-3 p-3 rounded-xl bg-white/5 border border-white/10"
              >
                <div className="w-7 h-7 rounded-lg bg-blue-600/20 flex items-center justify-center text-blue-400 flex-shrink-0">
                  {f.icon}
                </div>
                <div>
                  <p className="text-xs font-semibold text-white mb-0.5">{f.title}</p>
                  <p className="text-[11px] text-slate-500 leading-tight">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom quote */}
        <div className="relative z-10">
          <blockquote className="text-slate-500 text-sm italic border-l-2 border-blue-600/40 pl-4">
            "A organização é o fundamento da advocacia eficiente."
          </blockquote>
        </div>
      </div>

      {/* ── Right panel — login form ───────────────────────────────────────── */}
      <div className="flex-1 flex flex-col items-center justify-center bg-slate-50 px-6 py-12">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2 mb-8">
            <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center">
              <Scale size={15} className="text-white" />
            </div>
            <span className="text-lg font-bold">
              Juridic<span className="text-blue-600">Flow</span>
            </span>
          </div>

          {/* Header */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Entrar</h2>
            <p className="text-slate-500 text-sm mt-1">
              Acesse o painel do seu escritório
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            {/* Email */}
            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-sm font-medium text-slate-700">
                E-mail
              </Label>
              <div className="relative">
                <Mail
                  size={15}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                />
                <Input
                  id="email"
                  type="email"
                  placeholder="advogado@escritorio.com"
                  autoComplete="email"
                  className={cn(
                    'pl-9 h-11 bg-white border-slate-200 focus-visible:ring-blue-500',
                    errors.email && 'border-red-300 focus-visible:ring-red-500',
                  )}
                  {...register('email')}
                />
              </div>
              {errors.email && (
                <p className="text-xs text-red-600">{errors.email.message}</p>
              )}
            </div>

            {/* Senha */}
            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-sm font-medium text-slate-700">
                Senha
              </Label>
              <div className="relative">
                <Lock
                  size={15}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                />
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  className={cn(
                    'pl-9 pr-10 h-11 bg-white border-slate-200 focus-visible:ring-blue-500',
                    errors.password && 'border-red-300 focus-visible:ring-red-500',
                  )}
                  {...register('password')}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
              {errors.password && (
                <p className="text-xs text-red-600">{errors.password.message}</p>
              )}
            </div>

            {/* Submit */}
            <Button
              type="submit"
              disabled={loading}
              className="w-full h-11 bg-blue-600 hover:bg-blue-700 text-white font-medium gap-2 mt-2"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Entrando…
                </>
              ) : (
                <>
                  Entrar
                  <ArrowRight size={15} />
                </>
              )}
            </Button>
          </form>

          {/* Footer */}
          <p className="text-center text-xs text-slate-400 mt-8">
            JuridicFlow · Sistema de Gestão Jurídica
          </p>
        </div>
      </div>
    </div>
  )
}
