#!/usr/bin/env python3
"""
Analyze YouTube transcript using AI.
Provides summaries, key points, and custom analysis.
"""

import sys
import argparse
import json
from pathlib import Path

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    print("ERROR: youtube-transcript-api not found.")
    print("\nTo use this script, activate the venv:")
    print("  source ~/.claude/skills/youtube-transcript/venv/bin/activate")
    sys.exit(1)


def extract_video_id(url_or_id):
    """Extract video ID from YouTube URL or return ID if already an ID."""
    if 'youtube.com/watch?v=' in url_or_id:
        return url_or_id.split('watch?v=')[1].split('&')[0]
    elif 'youtu.be/' in url_or_id:
        return url_or_id.split('youtu.be/')[1].split('?')[0]
    else:
        return url_or_id


def get_transcript_text(video_id, languages=['es', 'es-ES', 'es-MX', 'en']):
    """Get plain text transcript from video."""
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=languages)
        full_text = ' '.join([s.text for s in transcript.snippets])
        return {
            'success': True,
            'video_id': video_id,
            'video_url': f'https://www.youtube.com/watch?v={video_id}',
            'language': transcript.language,
            'text': full_text,
            'word_count': len(full_text.split())
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'video_id': video_id
        }


def create_analysis_prompt(text, analysis_type='summary'):
    """Create analysis prompt based on type."""
    prompts = {
        'summary': f"""Analiza la siguiente transcripción de video de YouTube y proporciona:

1. **Resumen Ejecutivo** (2-3 párrafos): Resumen conciso del contenido principal
2. **Puntos Clave** (5-7 puntos): Ideas principales organizadas por importancia
3. **Conceptos Destacados**: Terminología o conceptos importantes mencionados
4. **Aplicación Práctica**: Cómo se puede aplicar esta información

Transcripción:
{text[:8000]}... (continúa)
""",
        'keypoints': f"""Extrae los puntos clave de esta transcripción de YouTube en formato de lista:

Transcripción:
{text[:8000]}... (continúa)
""",
        'technical': f"""Analiza esta transcripción de video técnico y proporciona:

1. **Stack Tecnológico**: Tecnologías, herramientas o frameworks mencionados
2. **Arquitectura**: Patrones arquitectónicos o de diseño discutidos
3. **Mejores Prácticas**: Recomendaciones o principios mencionados
4. **Casos de Uso**: Ejemplos prácticos o aplicaciones

Transcripción:
{text[:8000]}... (continúa)
""",
        'educational': f"""Analiza este contenido educativo y proporciona:

1. **Objetivo de Aprendizaje**: Qué se enseña
2. **Prerequisitos**: Conocimientos previos necesarios
3. **Conceptos Principales**: Ideas centrales explicadas
4. **Ejemplos Prácticos**: Ejercicios o demos mencionados
5. **Recursos Adicionales**: Referencias o links mencionados

Transcripción:
{text[:8000]}... (continúa)
"""
    }

    return prompts.get(analysis_type, prompts['summary'])


def main():
    parser = argparse.ArgumentParser(
        description='Analyze YouTube transcript content',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Analysis Types:
  summary     - General summary with key points (default)
  keypoints   - Extract main key points only
  technical   - Technical/engineering content analysis
  educational - Educational content analysis

Examples:
  # Basic summary
  python analyze_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"

  # Technical analysis
  python analyze_transcript.py VIDEO_ID --type technical

  # Save analysis prompt to file for manual review
  python analyze_transcript.py VIDEO_ID --output analysis_prompt.txt

  # Get transcript JSON for custom processing
  python analyze_transcript.py VIDEO_ID --json
        """
    )

    parser.add_argument('video', help='YouTube video URL or ID')
    parser.add_argument('--type', '-t',
                       choices=['summary', 'keypoints', 'technical', 'educational'],
                       default='summary',
                       help='Type of analysis (default: summary)')
    parser.add_argument('--languages', '-l', nargs='+',
                       default=['es', 'es-ES', 'es-MX', 'en'],
                       help='Language codes to try (default: es en)')
    parser.add_argument('--output', '-o', type=str,
                       help='Output file for analysis prompt')
    parser.add_argument('--json', action='store_true',
                       help='Output transcript as JSON for custom processing')
    parser.add_argument('--custom-prompt', type=str,
                       help='Custom analysis prompt (overrides --type)')

    args = parser.parse_args()

    # Extract video ID
    video_id = extract_video_id(args.video)

    # Get transcript
    print(f"Fetching transcript for video: {video_id}", file=sys.stderr)
    result = get_transcript_text(video_id, args.languages)

    if not result['success']:
        print(f"ERROR: {result['error']}", file=sys.stderr)
        sys.exit(1)

    print(f"Transcript retrieved: {result['word_count']} words in {result['language']}", file=sys.stderr)

    # Output format
    if args.json:
        # Output raw transcript JSON
        output = json.dumps(result, indent=2, ensure_ascii=False)
    else:
        # Create analysis prompt
        if args.custom_prompt:
            prompt = f"{args.custom_prompt}\n\nTranscripción:\n{result['text']}"
        else:
            prompt = create_analysis_prompt(result['text'], args.type)

        output = f"""# Análisis de Video de YouTube

**Video URL**: {result['video_url']}
**Idioma**: {result['language']}
**Palabras**: {result['word_count']:,}

---

{prompt}

---

**Nota**: Este es un prompt de análisis. Para obtener el análisis completo,
copia este prompt y úsalo con un modelo de IA (Claude, GPT, etc.)

Para obtener la transcripción completa en JSON:
  python analyze_transcript.py {video_id} --json
"""

    # Write output
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(output, encoding='utf-8')
        print(f"\nAnalysis prompt saved to: {output_path}", file=sys.stderr)
        print(f"Use this prompt with an AI model to get the analysis.", file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
