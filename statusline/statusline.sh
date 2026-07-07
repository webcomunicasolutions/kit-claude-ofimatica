#!/bin/bash

# Cargar nvm y Node.js 20
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" 2>/dev/null

# Leer el JSON de entrada desde stdin
input=$(cat)

# Verificar que jq está disponible
if ! command -v jq &> /dev/null; then
    echo "⚠️  Instala jq para ver métricas completas"
    exit 0
fi

# Extraer información del JSON
model=$(echo "$input" | jq -r '.model.display_name // "Claude"')
cwd=$(echo "$input" | jq -r '.workspace.current_dir // "."' | sed "s|$HOME|~|")

# Información de contexto
context_size=$(echo "$input" | jq -r '.context_window.context_window_size // 0')
input_tokens=$(echo "$input" | jq -r '.context_window.current_usage.input_tokens // 0')
output_tokens=$(echo "$input" | jq -r '.context_window.current_usage.output_tokens // 0')
cache_creation=$(echo "$input" | jq -r '.context_window.current_usage.cache_creation_input_tokens // 0')
cache_read=$(echo "$input" | jq -r '.context_window.current_usage.cache_read_input_tokens // 0')

# Calcular total de tokens usados (incluye TODOS los tokens: input, output, cache)
total_tokens=$((input_tokens + output_tokens + cache_creation + cache_read))
remaining_context=$((context_size - total_tokens))

# Calcular porcentaje usado
if [ "$context_size" -gt 0 ]; then
    percent_used=$(( (total_tokens * 100) / context_size ))
else
    percent_used=0
fi

# Obtener branch de git
if git rev-parse --git-dir > /dev/null 2>&1; then
    branch=$(git branch --show-current 2>/dev/null || echo "")
    [ -n "$branch" ] && git_info="🌿 $branch │ " || git_info=""
else
    git_info=""
fi

# ============================================
# CÁLCULO DE COSTOS
# ============================================
# Tarifas Claude Sonnet 4.5 (por millón de tokens)
PRICE_INPUT=3.00
PRICE_OUTPUT=15.00
PRICE_CACHE_WRITE=3.75
PRICE_CACHE_READ=0.30

# Calcular costos (forzar locale con punto decimal)
cost_input=$(LC_NUMERIC=C bc <<< "scale=6; $input_tokens * $PRICE_INPUT / 1000000")
cost_output=$(LC_NUMERIC=C bc <<< "scale=6; $output_tokens * $PRICE_OUTPUT / 1000000")
cost_cache_write=$(LC_NUMERIC=C bc <<< "scale=6; $cache_creation * $PRICE_CACHE_WRITE / 1000000")
cost_cache_read=$(LC_NUMERIC=C bc <<< "scale=6; $cache_read * $PRICE_CACHE_READ / 1000000")

# Total
total_cost=$(LC_NUMERIC=C bc <<< "scale=6; $cost_input + $cost_output + $cost_cache_write + $cost_cache_read")

# ============================================
# TRACKING DE SESIÓN Y PROMPTS
# ============================================
SESSION_FILE="/tmp/.claude-session-tracker"
current_time=$(date +%s)

# Leer o inicializar sesión
if [ -f "$SESSION_FILE" ]; then
    session_data=$(cat "$SESSION_FILE")
    session_start=$(echo "$session_data" | jq -r '.session_start // 0')
    prompt_count=$(echo "$session_data" | jq -r '.prompt_count // 0')
    prev_total_tokens=$(echo "$session_data" | jq -r '.tokens // 0')
    prev_cost=$(echo "$session_data" | jq -r '.cost // 0')

    # Verificar si han pasado más de 5 horas (18000 segundos)
    time_since_start=$((current_time - session_start))
    if [ "$time_since_start" -gt 18000 ]; then
        # Reset de sesión (nueva ventana de 5 horas)
        session_start=$current_time
        prompt_count=1
    else
        # Incrementar contador si hay nuevos tokens (nuevo prompt)
        if [ "$total_tokens" -gt "$prev_total_tokens" ]; then
            prompt_count=$((prompt_count + 1))
        fi
    fi
else
    # Nueva sesión
    session_start=$current_time
    prompt_count=1
    prev_total_tokens=0
    prev_cost=0
fi

# Calcular tiempo restante en la ventana de 5 horas
time_in_window=$((current_time - session_start))
seconds_until_window_reset=$((18000 - time_in_window))
hours_reset=$((seconds_until_window_reset / 3600))
minutes_reset=$(( (seconds_until_window_reset % 3600) / 60 ))

# Estimar % de uso del límite de 5 horas
# Plan Max $100: 50-200 prompts por ventana
# Usamos 125 como promedio (punto medio)
LIMIT_LOW=50
LIMIT_HIGH=200
LIMIT_AVG=125

percent_of_limit=$(LC_NUMERIC=C bc <<< "scale=1; ($prompt_count * 100) / $LIMIT_AVG")

# Determinar estado y color
if [ "$prompt_count" -lt 75 ]; then
    limit_color="\033[01;32m"  # Verde: seguro
    limit_status="✓"
elif [ "$prompt_count" -lt 125 ]; then
    limit_color="\033[01;33m"  # Amarillo: precaución
    limit_status="⚠"
else
    limit_color="\033[01;31m"  # Rojo: cerca del límite
    limit_status="⚠⚠"
fi

# Calcular burn rate
time_diff=$((current_time - session_start))
if [ "$time_diff" -gt 60 ]; then
    tokens_diff=$((total_tokens - prev_total_tokens))
    tokens_per_min=$(LC_NUMERIC=C bc <<< "scale=1; ($tokens_diff * 60) / $time_diff")
    burn_rate_info="⚡ ${tokens_per_min} tok/min"
else
    burn_rate_info="⚡ --"
fi

# Información de límite de 5 horas
limit_info="${limit_color}${limit_status} ${prompt_count}/~${LIMIT_AVG} prompts (${percent_of_limit}%)${reset}"

# Guardar estado actual
echo "{\"session_start\": $session_start, \"prompt_count\": $prompt_count, \"tokens\": $total_tokens, \"cost\": $total_cost}" > "$SESSION_FILE"

# Reset info ya calculado arriba en la sección de tracking
reset_info="${hours_reset}h ${minutes_reset}m"

# ============================================
# FORMATEO Y OUTPUT
# ============================================

format_number() {
    printf "%'d" "$1" 2>/dev/null || echo "$1"
}

create_progress_bar() {
    local percent=$1
    local width=20
    local filled=$(( (percent * width) / 100 ))
    local empty=$((width - filled))
    local bar=""
    for ((i=0; i<filled; i++)); do bar+="█"; done
    for ((i=0; i<empty; i++)); do bar+="░"; done
    echo "$bar"
}

progress_bar=$(create_progress_bar $percent_used)

# Colores según uso
if [ "$percent_used" -lt 50 ]; then
    ctx_color="\033[01;32m"  # Verde
elif [ "$percent_used" -lt 80 ]; then
    ctx_color="\033[01;33m"  # Amarillo
else
    ctx_color="\033[01;31m"  # Rojo
fi

reset="\033[00m"
blue="\033[01;34m"
cyan="\033[01;36m"
green="\033[01;32m"
yellow="\033[01;33m"

# Formatear contexto en K (miles)
if [ "$total_tokens" -ge 1000 ]; then
    total_k=$(LC_NUMERIC=C bc <<< "scale=0; $total_tokens / 1000")
    context_k=$(LC_NUMERIC=C bc <<< "scale=0; $context_size / 1000")
    context_display="${total_k}K/${context_k}K"
else
    context_display="${total_tokens}/${context_size}"
fi

# Línea 1: Directorio, Modelo, Reset
printf "${blue}📁 %s${reset} │ ${cyan}🤖 %s${reset} │ ${yellow}⏰ Reset: %s${reset}\n" \
    "$cwd" "$model" "$reset_info"

# Línea 2: Contexto simplificado
printf "${ctx_color}🧠 %d%% (%s) %s${reset} │ In: %s │ Out: %s\n" \
    "$percent_used" \
    "$context_display" \
    "$progress_bar" \
    "$(format_number $input_tokens)" \
    "$(format_number $output_tokens)"
