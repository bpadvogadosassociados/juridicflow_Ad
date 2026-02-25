# JuridicFlow — Frontend React

Frontend moderno em React + shadcn/ui para o JuridicFlow.

## Stack

- **Vite + React 18 + TypeScript**
- **Tailwind CSS + shadcn/ui** (New York style, Slate base)
- **Zustand** — estado global (auth, UI)
- **TanStack Query v5** — data fetching e cache
- **React Router v6** — roteamento
- **Axios** — HTTP client com interceptors JWT automáticos
- **Geist** — tipografia

## Setup

```bash
# 1. Instalar tudo de uma vez
bash setup.sh

# 2. Configurar variáveis de ambiente
cp .env.local.example .env.local
# Edite VITE_API_BASE_URL se necessário

# 3. Iniciar dev server
npm run dev
```

> ⚠️ O Django precisa estar rodando em `http://localhost:8000` com CORS habilitado para `http://localhost:5173`

## Configuração CORS no Django

No `settings.py`:

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
]

CORS_ALLOW_HEADERS = [
    *default_headers,
    "X-Office-Id",
]
```

## Estrutura

```
src/
├── api/          # Serviços HTTP por módulo
├── components/
│   ├── layout/   # AppLayout, Sidebar, Header
│   ├── shared/   # StatusBadge, EmptyState, GlobalSearch, etc.
│   └── ui/       # shadcn components (gerados)
├── hooks/        # useAuth, usePermission, useDebounce
├── lib/          # utils.ts, constants.ts
├── pages/        # Páginas organizadas por módulo
├── router/       # Rotas e ProtectedRoute
├── store/        # Zustand stores
└── types/        # TypeScript types
```

## Fluxo de autenticação

1. `POST /api/auth/login/` → salva tokens no Zustand (persistido)
2. `GET /api/auth/me/` → dados do usuário
3. `GET /api/auth/memberships/` → lista escritórios
4. Usuário seleciona escritório → `GET /api/auth/permissions/`
5. Axios injeta `Authorization` e `X-Office-Id` em toda request automaticamente
6. Em caso de 401 → tenta refresh → se falhar, redireciona para login

## Sprints

- ✅ **Sprint 1** — Fundação: auth, layout, dashboard, router
- 🔜 **Sprint 2** — Processos, Prazos, Search
- 🔜 **Sprint 3** — CRM/Pipeline, Kanban
- 🔜 **Sprint 4** — Financeiro
- 🔜 **Sprint 5** — Documentos, Agenda, Relatórios, Equipe
