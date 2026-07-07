#!/usr/bin/env bash
# Instalador del Kit Claude Ofimatica
# Copia las skills a ~/.claude/skills/ para que Claude Code las use.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.claude/skills"

echo "==> Kit Claude Ofimatica - instalador"

if [ ! -d "$HOME/.claude" ]; then
  echo "ERROR: No encuentro ~/.claude/"
  echo "Instala primero Claude Code: https://docs.anthropic.com/en/docs/claude-code"
  exit 1
fi

mkdir -p "$DEST"

installed=0
for skill in "$DIR"/skills/*/; do
  name="$(basename "$skill")"
  if [ -e "$DEST/$name" ]; then
    echo "  = $name ya existe, lo omito (no sobrescribo)"
  else
    cp -r "$skill" "$DEST/$name"
    echo "  + $name instalada"
    installed=$((installed+1))
  fi
done

echo ""
echo "==> Listo. Skills nuevas instaladas: $installed"
echo "    Reinicia Claude Code para que las detecte."
