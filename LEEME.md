# Kit Claude Ofimática

Un conjunto de habilidades ("skills") para **Claude Code** orientadas a trabajo
de oficina: documentos, hojas de cálculo, transcripción, extracción de datos y
diseño. No requiere saber programar.

## Qué incluye

### Documentos y datos
| Skill | Para qué sirve |
|-------|----------------|
| `pdf` | Leer, crear, unir, dividir y rellenar PDFs. Extraer texto y tablas de facturas/albaranes. |
| `docx` | Crear y editar documentos Word. |
| `xlsx` | Crear y editar hojas de cálculo Excel con fórmulas. |
| `pptx` | Crear presentaciones PowerPoint. |
| `documentos-corporativos` | Generar PDFs con cabecera/pie y colores de tu empresa (presupuestos, informes). Personalizable con tus datos. |
| `llmwhisperer` | OCR avanzado: extraer texto de documentos escaneados (requiere clave API de Unstract, servicio de pago). |

### Audio, vídeo y web
| Skill | Para qué sirve |
|-------|----------------|
| `whisper-transcribe` | Pasar audios y vídeos a texto (notas de voz, reuniones). |
| `youtube-transcript` | Sacar la transcripción de vídeos de YouTube. |
| `web-scraper` | Extraer información de páginas web a texto limpio. |

### Diseño y presentación
| Skill | Para qué sirve |
|-------|----------------|
| `frontend-design` | Crear páginas e interfaces web con buen diseño. |
| `web-artifacts-builder` | Construir artefactos web con componentes (catálogos, mini-apps). |
| `theme-factory` | 10 temas visuales listos para aplicar a cualquier artefacto. |
| `canvas-design` | Arte visual en PNG/PDF (carteles, gráficos). |

### Trabajo con Claude
| Skill | Para qué sirve |
|-------|----------------|
| `prompt-optimizer` | Te ayuda a redactar mejores instrucciones para Claude. |
| `internal-comms` | Plantillas de comunicaciones internas: informes, actualizaciones, FAQs. |
| `session-management` | Guardar y retomar sesiones de trabajo entre conversaciones. |

### Barra de estado
Una barra de estado (statusline) que muestra en tiempo real: uso del contexto,
tokens consumidos, **coste de la sesión**, modelo y tiempo hasta el reinicio de
límite. Se instala y configura sola con el instalador.

## Requisitos

- Tener **Claude Code** instalado: https://docs.anthropic.com/en/docs/claude-code
- Herramientas del sistema (se instalan una sola vez). En Ubuntu/Debian:
  ```bash
  sudo apt install pandoc libreoffice poppler-utils ffmpeg jq bc
  ```
  - Documentos: `pandoc`, `libreoffice`, `poppler-utils`
  - Transcripción: `ffmpeg`
  - Barra de estado: `jq`, `bc`

## Cómo instalar

1. Descomprime este paquete.
2. Abre una terminal dentro de la carpeta.
3. Ejecuta:

   ```bash
   bash instalar.sh
   ```

4. Reinicia Claude Code.

El instalador copia las skills a `~/.claude/skills/`, instala la barra de estado
y **no sobrescribe** skills que ya tengas. Hace copia de seguridad de
`settings.json` antes de tocarlo.

## Cómo se usan

No hay que hacer nada especial: Claude Code activa las skills solo cuando la
tarea lo pide. Pídele en lenguaje normal, por ejemplo:

- "Crea un PDF de presupuesto con estos datos"
- "Transcribe este audio de la reunión"
- "Extrae las líneas de esta factura en PDF a una hoja de Excel"
- "Diséñame un cartel para la oferta de perfiles de aluminio"
