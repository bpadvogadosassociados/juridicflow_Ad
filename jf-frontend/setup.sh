#!/bin/bash
# ============================================================
# setup.sh — JuridicFlow Frontend Setup
# Execute após: cd juridicflow-frontend && bash setup.sh
# ============================================================

set -e

echo "🚀 Instalando dependências..."
npm install

echo ""
echo "🎨 Inicializando shadcn/ui (responda às perguntas)..."
echo "   → Style: New York"
echo "   → Base color: Slate"
echo "   → CSS variables: Yes"
echo ""
npx shadcn@latest init

echo ""
echo "📦 Adicionando componentes shadcn necessários..."

COMPONENTS=(
  "button"
  "card"
  "input"
  "label"
  "select"
  "textarea"
  "badge"
  "dialog"
  "sheet"
  "popover"
  "dropdown-menu"
  "table"
  "pagination"
  "tabs"
  "separator"
  "avatar"
  "command"
  "sonner"
  "form"
  "alert-dialog"
  "scroll-area"
  "skeleton"
  "calendar"
  "checkbox"
  "switch"
  "tooltip"
  "progress"
)

for component in "${COMPONENTS[@]}"; do
  echo "  → $component"
  npx shadcn@latest add "$component" --yes 2>/dev/null || true
done

echo ""
echo "✅ Setup concluído!"
echo ""
echo "Para iniciar o desenvolvimento:"
echo "  cp .env.local.example .env.local"
echo "  npm run dev"
echo ""
echo "O frontend estará disponível em: http://localhost:5173"
echo "Certifique-se que o Django está rodando em: http://localhost:8000"
