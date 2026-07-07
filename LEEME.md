# Kit Claude Ofimática

Un conjunto de habilidades ("skills") para **Claude Code** orientadas a trabajo
de oficina: documentos, hojas de cálculo, transcripción y extracción de datos.
No requiere saber programar.

## Qué incluye

| Skill | Para qué sirve |
|-------|----------------|
| `pdf` | Leer, crear, unir, dividir y rellenar PDFs. Extraer texto y tablas de facturas/albaranes. |
| `docx` | Crear y editar documentos Word. |
| `xlsx` | Crear y editar hojas de cálculo Excel con fórmulas. |
| `pptx` | Crear presentaciones PowerPoint. |
| `documentos-corporativos` | Generar PDFs con cabecera/pie y colores de tu empresa (presupuestos, informes). Personalizable con tus datos. |
| `whisper-transcribe` | Pasar audios y vídeos a texto (notas de voz, reuniones). |
| `web-scraper` | Extraer información de páginas web a texto limpio. |
| `llmwhisperer` | OCR avanzado: extraer texto de documentos escaneados (requiere clave API de Unstract, servicio de pago). |
| `youtube-transcript` | Sacar la transcripción de vídeos de YouTube. |

## Requisitos

- Tener **Claude Code** instalado: https://docs.anthropic.com/en/docs/claude-code
- Algunas skills necesitan herramientas del sistema (se instalan una sola vez):
  - Documentos: `pandoc`, `libreoffice`, `poppler-utils`
  - Transcripción: `ffmpeg` + el motor de Whisper
  - En Ubuntu/Debian: `sudo apt install pandoc libreoffice poppler-utils ffmpeg`

## Cómo instalar

1. Descomprime este paquete.
2. Abre una terminal dentro de la carpeta.
3. Ejecuta:

   ```bash
   bash instalar.sh
   ```

4. Reinicia Claude Code.

El instalador copia las skills a `~/.claude/skills/` y **no sobrescribe** nada
que ya tengas.

## Cómo se usan

No hay que hacer nada especial: Claude Code las activa solo cuando la tarea lo
pide. Por ejemplo, pídele en lenguaje normal:

- "Crea un PDF de presupuesto con estos datos"
- "Transcribe este audio de la reunión"
- "Extrae las líneas de esta factura en PDF a una hoja de Excel"
