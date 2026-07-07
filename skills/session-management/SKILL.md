---
name: session-management
description: Sistema de persistencia de sesiones entre conversaciones. Guardar estado, retomar trabajo, prevenir reintentos de enfoques fallidos. Usar con /save-session y /resume-session.
---

# Session Management

## Concepto
Persistir el contexto de trabajo entre sesiones de Claude Code para:
- Retomar donde se dejó sin perder progreso
- Evitar reintentar enfoques que ya fallaron
- Mantener decisiones y tradeoffs documentados

## Directorio: `~/.claude/sessions/`

## Formato de archivo
`YYYY-MM-DD-<descripcion>-session.md`

## Secciones obligatorias
1. **Qué estamos construyendo** — contexto para alguien nuevo
2. **Qué FUNCIONÓ** — éxitos confirmados con evidencia
3. **Qué NO funcionó** — CRÍTICO: previene reintentos inútiles
4. **Qué NO se ha intentado** — ideas prometedores pendientes
5. **Estado de archivos** — tabla de archivos modificados
6. **Decisiones tomadas** — con razón/tradeoff
7. **Blockers** — issues sin resolver
8. **Próximo paso exacto** — una sola acción para retomar

## Principios
- La sección "Qué NO funcionó" es la MÁS importante
- Incluir errores exactos, no descripciones vagas
- Nunca omitir secciones (usar "N/A" si no aplica)
- El archivo de sesión es READ-ONLY al retomar
- No auto-empezar trabajo al retomar — esperar dirección del usuario

## Workflow
```
Guardar: /save-session
Retomar: /resume-session [fecha | ruta]
Listar:  ls ~/.claude/sessions/
```
