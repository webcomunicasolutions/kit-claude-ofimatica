#!/bin/bash
# =============================================================================
# Instalador automático del skill web-scraper
# Ejecutar en cualquier equipo nuevo después de sincronizar desde GitHub
#
# Uso:
#   bash ~/.claude/skills/web-scraper/install.sh
# =============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
info() { echo -e "  ${BLUE}→${NC} $1"; }

echo ""
echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo -e "${BLUE}  Instalador: skill web-scraper${NC}"
echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo ""

ERRORS=0

# ─────────────────────────────────────────
# 1. Python 3
# ─────────────────────────────────────────
echo -e "${BLUE}[1/4]${NC} Verificando Python..."

if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    ok "Python $PY_VERSION instalado"
else
    fail "Python 3 no encontrado"
    info "Instalar con: sudo apt install python3 python3-pip"
    ERRORS=$((ERRORS + 1))
fi

# ─────────────────────────────────────────
# 2. Paquetes Python
# ─────────────────────────────────────────
echo ""
echo -e "${BLUE}[2/4]${NC} Verificando paquetes Python..."

PACKAGES=("beautifulsoup4:bs4" "requests:requests" "lxml:lxml" "html5lib:html5lib")
MISSING=()

for pkg in "${PACKAGES[@]}"; do
    NAME="${pkg%%:*}"
    MODULE="${pkg##*:}"
    if python3 -c "import $MODULE" 2>/dev/null; then
        ok "$NAME"
    else
        warn "$NAME no instalado — se instalará ahora"
        MISSING+=("$NAME")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    info "Instalando: ${MISSING[*]}"
    pip install --user --quiet "${MISSING[@]}" 2>/dev/null || \
    pip3 install --user --quiet "${MISSING[@]}" 2>/dev/null || \
    python3 -m pip install --user --quiet "${MISSING[@]}" 2>/dev/null

    if [ $? -eq 0 ]; then
        ok "Paquetes Python instalados correctamente"
    else
        fail "Error instalando paquetes. Intentar manualmente: pip install ${MISSING[*]}"
        ERRORS=$((ERRORS + 1))
    fi
fi

# ─────────────────────────────────────────
# 3. Node.js
# ─────────────────────────────────────────
echo ""
echo -e "${BLUE}[3/4]${NC} Verificando Node.js..."

# Cargar nvm si existe
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" 2>/dev/null

if command -v node &>/dev/null; then
    NODE_VERSION=$(node --version 2>&1)
    NODE_MAJOR=$(echo "$NODE_VERSION" | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_MAJOR" -ge 20 ]; then
        ok "Node.js $NODE_VERSION"
    else
        warn "Node.js $NODE_VERSION (se recomienda v20+)"
        info "Actualizar con: nvm install 20 && nvm alias default 20"
    fi
else
    fail "Node.js no encontrado"
    info "Instalar con nvm: curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash"
    info "Luego: nvm install 20"
    ERRORS=$((ERRORS + 1))
fi

# ─────────────────────────────────────────
# 4. Playwright Chromium
# ─────────────────────────────────────────
echo ""
echo -e "${BLUE}[4/4]${NC} Verificando Playwright Chromium..."

# Verificar si Playwright está instalado buscando el directorio
PW_DIR="$HOME/.cache/ms-playwright"
if [ -d "$PW_DIR" ] && ls "$PW_DIR"/chromium* &>/dev/null; then
    PW_FOLDER=$(ls -d "$PW_DIR"/chromium* 2>/dev/null | head -1)
    ok "Playwright Chromium instalado ($(basename "$PW_FOLDER"))"
else
    warn "Playwright Chromium no instalado — se instalará ahora (~111 MB)"
    info "Descargando..."
    if npx playwright install chromium 2>&1 | tail -1; then
        ok "Playwright Chromium instalado"
    else
        fail "Error instalando Playwright"
        info "Intentar manualmente: npx playwright install chromium"
        ERRORS=$((ERRORS + 1))
    fi
fi

# ─────────────────────────────────────────
# 5. Permisos de ejecución
# ─────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)/scripts"
if [ -d "$SCRIPT_DIR" ]; then
    chmod +x "$SCRIPT_DIR"/*.py "$SCRIPT_DIR"/*.js 2>/dev/null
fi

# ─────────────────────────────────────────
# Resumen
# ─────────────────────────────────────────
echo ""
echo -e "${BLUE}══════════════════════════════════════════${NC}"
if [ $ERRORS -eq 0 ]; then
    echo -e "  ${GREEN}Todo listo.${NC} El skill web-scraper está operativo."
    echo ""
    echo "  Uso rápido:"
    echo "    # Scrapear 1 página"
    echo "    python3 ~/.claude/skills/web-scraper/scripts/scrape_page.py \"URL\" -o salida.md"
    echo ""
    echo "    # Crawlear sitio completo"
    echo "    python3 ~/.claude/skills/web-scraper/scripts/crawl_site.py \"URL\" -o ./output"
    echo ""
    echo "    # Scrapear documentación"
    echo "    python3 ~/.claude/skills/web-scraper/scripts/scrape_docs.py \"URL\" -o ./docs -c"
else
    echo -e "  ${YELLOW}Instalación con $ERRORS error(es).${NC} Revisa los mensajes de arriba."
fi
echo -e "${BLUE}══════════════════════════════════════════${NC}"
echo ""
