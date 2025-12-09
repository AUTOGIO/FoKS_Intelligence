#!/usr/bin/env bash
# Script helper para criar o atalho FoKS Intelligence

set -euo pipefail

echo "=========================================="
echo "  FoKS Intelligence - Shortcut Helper"
echo "=========================================="
echo ""
echo "Este script ajuda a criar o atalho macOS."
echo ""
echo "📋 Pré-requisitos:"
echo "  ✅ Backend rodando em http://localhost:8000"
echo "  ✅ LM Studio ativo"
echo ""
echo "📖 Instruções completas em:"
echo "  docs/SHORTCUT_SETUP.md"
echo ""
echo "🔹 Resumo rápido:"
echo ""
echo "1. Abra o app Atalhos"
echo "2. Crie novo atalho: 'FoKS Intelligence'"
echo "3. Adicione ações na ordem:"
echo "   - Perguntar (texto)"
echo "   - Dicionário (JSON payload)"
echo "   - Obter Conteúdo de URL (POST http://localhost:8000/chat/)"
echo "   - Obter valor para chave (reply)"
echo "   - Mostrar Notificação"
echo ""
echo "📝 Exemplo de Payload JSON:"
cat << 'EOF'
{
  "message": "Texto do usuário",
  "input_type": "text",
  "source": "shortcuts",
  "metadata": {
    "device": "iMac_M3",
    "shortcut_name": "FoKS Intelligence"
  }
}
EOF
echo ""
echo "🧪 Teste rápido:"
echo "  curl -X POST http://localhost:8000/chat/ \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"message\": \"Olá!\", \"source\": \"test\"}'"
echo ""

