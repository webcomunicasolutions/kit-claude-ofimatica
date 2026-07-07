#!/usr/bin/env bash
# Instalador del Kit Claude Ofimatica
# 1) Copia las skills a ~/.claude/skills/
# 2) Instala y configura la barra de estado (statusline)
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE="$HOME/.claude"
DEST="$CLAUDE/skills"
SETTINGS="$CLAUDE/settings.json"

echo "==> Kit Claude Ofimatica - instalador"

if [ ! -d "$CLAUDE" ]; then
  echo "ERROR: No encuentro ~/.claude/"
  echo "Instala primero Claude Code: https://docs.anthropic.com/en/docs/claude-code"
  exit 1
fi

# --- 1) Skills ---
mkdir -p "$DEST"
installed=0
for skill in "$DIR"/skills/*/; do
  name="$(basename "$skill")"
  if [ -e "$DEST/$name" ]; then
    echo "  = skill $name ya existe, la omito (no sobrescribo)"
  else
    cp -r "$skill" "$DEST/$name"
    echo "  + skill $name instalada"
    installed=$((installed+1))
  fi
done

# --- 2) Statusline ---
echo ""
echo "==> Barra de estado (statusline)"
cp "$DIR/statusline/statusline.sh" "$CLAUDE/statusline.sh"
chmod +x "$CLAUDE/statusline.sh"
echo "  + statusline.sh copiado a ~/.claude/"

if ! command -v jq >/dev/null 2>&1; then
  echo "  ! jq no esta instalado; no puedo editar settings.json automaticamente."
  echo "    Instala jq (sudo apt install jq) y vuelve a ejecutar, o anade a mano"
  echo "    a ~/.claude/settings.json:"
  echo '      "statusLine": { "type": "command", "command": "bash ~/.claude/statusline.sh" }'
else
  # Merge seguro: crea settings.json si no existe, respeta el resto de claves,
  # y hace copia de seguridad antes de tocar nada.
  [ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"
  cp "$SETTINGS" "$SETTINGS.bak.$(date +%Y%m%d%H%M%S)"
  tmp="$(mktemp)"
  jq '.statusLine = {"type":"command","command":"bash ~/.claude/statusline.sh"}' \
     "$SETTINGS" > "$tmp" && mv "$tmp" "$SETTINGS"
  echo "  + statusLine configurada en settings.json (copia de seguridad creada)"
fi

echo ""
echo "==> Listo. Skills nuevas instaladas: $installed"
echo "    Requisitos de la barra de estado: jq y bc (sudo apt install jq bc)"
echo "    Reinicia Claude Code para aplicar los cambios."
