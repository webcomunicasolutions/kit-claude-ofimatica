---
name: whisper-transcribe
description: "Transcripcion de audio y video a texto con faster-whisper. Usar cuando el usuario quiera transcribir, pasar a texto, generar subtitulos, o extraer texto de audios (mp3, ogg, wav, m4a), videos (mp4, mkv), notas de voz de WhatsApp/Telegram, reuniones o entrevistas."
---

# Skill: whisper-transcribe

## Descripcion
Transcripcion de audio y video a texto usando faster-whisper instalado globalmente en el sistema.

## Instalación en el sistema

### Ubicación
- **Entorno**: `~/.local/share/whisper-env/` (venv dedicado, 532 MB)
- **Comando global**: `whisper-transcribe` (disponible en PATH via `~/.local/bin/`)
- **Script**: `~/.local/bin/whisper-transcribe`

### Si no está instalado (reinstalar)
```bash
python3 -m venv ~/.local/share/whisper-env
~/.local/share/whisper-env/bin/pip install faster-whisper
chmod +x ~/.local/bin/whisper-transcribe
```

## Uso del comando

```bash
# Básico (modelo small, autodetecta idioma, guarda .txt)
whisper-transcribe audio.mp3

# Especificar idioma (más rápido y preciso)
whisper-transcribe audio.wav --language es

# Modelo más preciso para audio difícil
whisper-transcribe reunion.mp4 --model medium --language es

# Generar subtítulos SRT
whisper-transcribe video.mp4 --output srt --language es

# Solo mostrar en pantalla (sin guardar archivo)
whisper-transcribe nota.ogg --output stdout

# Formato JSON con timestamps por segmento
whisper-transcribe entrevista.mp3 --output json --language es
```

## Modelos disponibles

| Modelo | Tamaño descarga | Velocidad | Calidad | Uso recomendado |
|--------|----------------|-----------|---------|-----------------|
| tiny   | ~39 MB  | Muy rápido | Básica  | Pruebas rápidas |
| base   | ~74 MB  | Rápido     | Aceptable | Audio claro, pocas palabras |
| small  | ~244 MB | Medio      | Buena   | **Default. Audio normal** |
| medium | ~769 MB | Lento      | Muy buena | Reuniones, acentos |
| large-v3 | ~1.5 GB | Muy lento | Excelente | Audio difícil, máxima precisión |

Los modelos se descargan automáticamente en `~/.cache/huggingface/hub/` la primera vez.

## Formatos de entrada soportados
mp3, wav, ogg, m4a, flac, aac, mp4, mkv, avi, mov, webm (cualquier formato que FFmpeg soporte)

## Flujo de trabajo con Claude

1. El usuario proporciona ruta al archivo de audio
2. Claude ejecuta `whisper-transcribe <archivo> --language es`
3. Se genera automáticamente `<archivo>.txt` en la misma carpeta
4. Claude lee el .txt y puede resumir, analizar o procesar el contenido

## Ejemplo completo

```bash
# El usuario tiene una nota de voz de WhatsApp
whisper-transcribe ~/Downloads/nota.ogg --language es --output stdout

# Transcribir una reunión y guardar subtítulos
whisper-transcribe ~/reunion.mp4 \
  --model medium \
  --language es \
  --output srt
```

## Notas importantes
- Primera ejecución descarga el modelo (solo una vez, queda en caché)
- Funciona sin GPU (CPU, compute_type=int8) → lento pero funciona en cualquier máquina
- NO requiere activar ningún venv ni estar en ningún proyecto
- Si hay GPU disponible: añadir `--device cuda` para mayor velocidad
