---
name: youtube-transcript
description: Extract and analyze transcripts from YouTube videos. Use when users request YouTube video transcriptions, summaries, or analysis. Handles video URLs or IDs, supports multiple languages (Spanish, English, etc.), and provides various output formats (text, timestamps, JSON, SRT). Works with auto-generated and manual subtitles.
---

# YouTube Transcript Extraction and Analysis

Extract transcripts from YouTube videos and optionally analyze their content.

## Quick Start

### Extract Basic Transcript

```bash
# Extract transcript (text format)
python3 ~/.claude/skills/youtube-transcript/scripts/extract_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Or use just the video ID
python3 ~/.claude/skills/youtube-transcript/scripts/extract_transcript.py VIDEO_ID
```

### Common Use Cases

**Get transcript with timestamps:**
```bash
python3 ~/.claude/skills/youtube-transcript/scripts/extract_transcript.py VIDEO_ID --format timestamps
```

**Save to file:**
```bash
python3 ~/.claude/skills/youtube-transcript/scripts/extract_transcript.py VIDEO_ID --output transcript.txt
```

**Specify language preference:**
```bash
python3 ~/.claude/skills/youtube-transcript/scripts/extract_transcript.py VIDEO_ID --languages en es fr
```

**Export as SRT subtitles:**
```bash
python3 ~/.claude/skills/youtube-transcript/scripts/extract_transcript.py VIDEO_ID --format srt --output video.srt
```

**Get JSON for processing:**
```bash
python3 ~/.claude/skills/youtube-transcript/scripts/extract_transcript.py VIDEO_ID --format json
```

## Scripts

### extract_transcript.py

Main transcript extraction script with multiple output formats.

**Parameters:**
- `video`: YouTube URL or video ID (required)
- `--languages, -l`: Language codes to try in order (default: es, en)
- `--format, -f`: Output format: text, timestamps, json, srt (default: text)
- `--output, -o`: Output file path (default: stdout)

**Output Formats:**
- `text`: Clean plain text without timestamps
- `timestamps`: Text with [MM:SS] timestamps per line
- `json`: Structured JSON with all metadata
- `srt`: Standard SRT subtitle format

**Example outputs:**

Text format:
```
VIDEO: https://www.youtube.com/watch?v=ABC123
Language: English (auto-generated) (en)
Auto-generated: True
Snippets: 500
================================================================================
For 500,000 years we've had essentially the same cognitive architecture...
```

Timestamps format:
```
[00:00] For 500,000 years we've had essentially
[00:02] the same cognitive architecture. And
[00:04] today, I want to talk about...
```

### analyze_transcript.py

Create analysis prompts for AI processing of transcript content.

**Parameters:**
- `video`: YouTube URL or video ID (required)
- `--type, -t`: Analysis type: summary, keypoints, technical, educational (default: summary)
- `--languages, -l`: Language codes to try (default: es, en)
- `--output, -o`: Save analysis prompt to file
- `--json`: Output raw transcript JSON instead of analysis prompt
- `--custom-prompt`: Provide custom analysis prompt

**Analysis Types:**

1. **summary** (default): General summary with key points, concepts, and practical applications
2. **keypoints**: Focused extraction of main ideas only
3. **technical**: Technical/engineering content analysis (stack, architecture, best practices)
4. **educational**: Educational content analysis (learning objectives, prerequisites, examples)

**Usage:**
```bash
# Generate summary analysis prompt
python scripts/analyze_transcript.py VIDEO_ID

# Technical analysis
python scripts/analyze_transcript.py VIDEO_ID --type technical

# Save prompt to file for manual processing
python scripts/analyze_transcript.py VIDEO_ID --output analysis.txt

# Get raw JSON for custom processing
python scripts/analyze_transcript.py VIDEO_ID --json > transcript.json
```

**Note:** This script generates analysis prompts that can be used with AI models. It does not perform the analysis itself.

## Workflow Patterns

### Pattern 1: Quick Extract and Analyze

When user requests video analysis:

1. Extract transcript to temporary file:
   ```bash
   python scripts/extract_transcript.py VIDEO_ID --output /tmp/transcript.txt
   ```

2. Read the transcript file and analyze directly with your capabilities (no need for analyze_transcript.py)

### Pattern 2: Structured Analysis

For formal analysis requests:

1. Generate analysis prompt:
   ```bash
   python scripts/analyze_transcript.py VIDEO_ID --type technical --output /tmp/prompt.txt
   ```

2. Read the prompt file and provide analysis based on the structured format

### Pattern 3: Export for User

When user wants to keep transcript:

1. Extract in preferred format:
   ```bash
   python scripts/extract_transcript.py VIDEO_ID --format timestamps --output transcript.txt
   ```

2. Provide the file path to user

## Language Support

The scripts try languages in order of preference (default: Spanish first, then English):
- `es`, `es-ES`, `es-MX` - Spanish variants
- `en` - English
- Custom: Specify any language code supported by YouTube

Override with `--languages` parameter:
```bash
python scripts/extract_transcript.py VIDEO_ID --languages fr de en
```

## Requirements

**Dependencies** (installed en sistema):
- `youtube-transcript-api` - En `~/.local/lib/python3.12/`
- `requests` - En sistema

Si falta: `pip3 install --user youtube-transcript-api requests --break-system-packages`

## Error Handling

Common errors and solutions:

**"ImportError: youtube-transcript-api not found"**
- Solution: `pip3 install --user youtube-transcript-api --break-system-packages`

**"HTTP Error 429: Too Many Requests"**
- YouTube rate limiting
- Wait a few minutes and retry
- Consider using a proxy if persistent

**"No transcript available"**
- Video doesn't have subtitles/captions
- Try different language codes
- Some videos disable subtitle extraction

**"Could not retrieve transcript"**
- Video may be private, deleted, or restricted
- Check video URL is correct
- Verify video is accessible

## Tips for Claude

1. **Usar python3 del sistema** - NO activar venv, la dependencia esta instalada globalmente
2. **Extract once, analyze multiple times** - save transcript to temp file and reference it
3. **Use appropriate format**:
   - `text` for AI analysis
   - `timestamps` for user readability
   - `json` for programmatic processing
   - `srt` for video editing
4. **Language detection**: Scripts auto-detect best available language, but you can override
5. **Large transcripts**: For very long videos (>1hr), consider extracting as JSON and processing in chunks

## Integration Examples

### With document analysis:
```bash
# Extract to temp file
python scripts/extract_transcript.py VIDEO_ID --output /tmp/transcript.txt

# Then analyze the file content directly
# (more efficient than using analyze_transcript.py)
```

### With project documentation:
```bash
# Extract key educational content
python scripts/extract_transcript.py VIDEO_ID --format timestamps --output docs/video-notes.txt
```

### Batch processing:
```bash
# Process multiple videos
for video in VIDEO_ID1 VIDEO_ID2 VIDEO_ID3; do
  python scripts/extract_transcript.py $video --output transcripts/${video}.txt
done
```

## Performance Notes

- Extraction is fast (<5 seconds typically)
- No API keys required (uses YouTube's public transcript API)
- Rate limits: ~100 requests/hour typically safe
- Transcript size: Usually 50-200 words per minute of video
