---
name: prompt-optimizer
description: Analiza, critica y mejora prompts sin ejecutar la tarea. Pipeline de 6 fases para optimizar instrucciones a Claude. Usar cuando se quiera mejorar la calidad de un prompt.
---

# Prompt Optimizer

Skill advisory-only: analiza y mejora prompts, NO ejecuta la tarea.

## Triggers
- "optimiza este prompt", "mejora mi prompt", "ayúdame a escribir mejor prompt"

## Pipeline de 6 fases

### Fase 0: Detección de proyecto
Scan CLAUDE.md, package.json, go.mod, pyproject.toml para contexto.

### Fase 1: Detección de intención
Clasifica en: New Feature, Bug Fix, Refactor, Research, Testing, Review, Documentation, Infrastructure, Design.

### Fase 2: Evaluación de alcance
Trivial - Small - Medium - Large - Epic

### Fase 3: Matching de componentes
Mapea intención + tech stack a commands, skills, agentes recomendados.

| Intención | Componentes |
|-----------|-------------|
| New Feature | /plan, /tdd, /code-review |
| Bug Fix | /tdd, /build-fix |
| Refactor | refactor-cleaner, /code-review |
| Testing | /tdd, test-generator |

### Fase 4: Detección de contexto faltante
Si 3+ items críticos faltan, pedir clarificación antes de optimizar.

### Fase 5: Workflow y modelo recomendado
- Trivial-Medium: Sonnet
- Large-Epic planning: Opus
- Sugiere etapas y orden

## Output (5 secciones)
1. **Diagnóstico** — fortalezas, problemas, clarificaciones
2. **Componentes recomendados** — commands, skills, agents, modelo
3. **Prompt optimizado (completo)** — copy-paste ready
4. **Prompt optimizado (rápido)** — comprimido para usuarios expertos
5. **Justificación** — por qué cada mejora importa
