#!/usr/bin/env python3
"""
Extract transcripts from YouTube videos.
Supports multiple languages and outputs in various formats.
"""

import sys
import argparse
from pathlib import Path

# Check if running in venv, if not, provide instructions
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    print("ERROR: youtube-transcript-api not found.")
    print("\nInstall it system-wide:")
    print("  pip3 install --user youtube-transcript-api --break-system-packages")
    sys.exit(1)


def extract_video_id(url_or_id):
    """Extract video ID from YouTube URL or return ID if already an ID."""
    if 'youtube.com/watch?v=' in url_or_id:
        return url_or_id.split('watch?v=')[1].split('&')[0]
    elif 'youtu.be/' in url_or_id:
        return url_or_id.split('youtu.be/')[1].split('?')[0]
    else:
        # Assume it's already a video ID
        return url_or_id


def extract_transcript(video_id, languages=['es', 'es-ES', 'es-MX', 'en'], output_format='text'):
    """
    Extract transcript from a YouTube video.

    Args:
        video_id: YouTube video ID
        languages: List of language codes to try (in order of preference)
        output_format: 'text', 'json', 'srt', or 'timestamps'

    Returns:
        dict with transcript data
    """
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=languages)

        result = {
            'video_id': video_id,
            'video_url': f'https://www.youtube.com/watch?v={video_id}',
            'language': transcript.language,
            'language_code': transcript.language_code,
            'is_generated': transcript.is_generated,
            'snippet_count': len(transcript.snippets),
            'transcript': transcript.snippets
        }

        return result

    except Exception as e:
        return {'error': str(e), 'video_id': video_id}


def format_output(result, output_format='text'):
    """Format transcript data for output."""
    if 'error' in result:
        return f"ERROR: {result['error']}\nVideo ID: {result['video_id']}"

    output = []
    output.append(f"VIDEO: {result['video_url']}")
    output.append(f"Language: {result['language']} ({result['language_code']})")
    output.append(f"Auto-generated: {result['is_generated']}")
    output.append(f"Snippets: {result['snippet_count']}")
    output.append("=" * 80)

    if output_format == 'text':
        # Plain text without timestamps
        full_text = ' '.join([s.text for s in result['transcript']])
        output.append(full_text)

    elif output_format == 'timestamps':
        # Text with timestamps
        for snippet in result['transcript']:
            timestamp = f"[{int(snippet.start//60):02d}:{int(snippet.start%60):02d}]"
            output.append(f"{timestamp} {snippet.text}")

    elif output_format == 'json':
        # JSON format
        import json
        return json.dumps(result, indent=2, default=str)

    elif output_format == 'srt':
        # SRT subtitle format
        output = []
        for i, snippet in enumerate(result['transcript'], 1):
            start_time = format_srt_time(snippet.start)
            end_time = format_srt_time(snippet.start + snippet.duration)
            output.append(f"{i}")
            output.append(f"{start_time} --> {end_time}")
            output.append(snippet.text)
            output.append("")

    return '\n'.join(output)


def format_srt_time(seconds):
    """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def main():
    parser = argparse.ArgumentParser(
        description='Extract transcripts from YouTube videos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract transcript in text format
  python extract_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"

  # Extract with timestamps
  python extract_transcript.py VIDEO_ID --format timestamps

  # Extract as JSON
  python extract_transcript.py VIDEO_ID --format json

  # Save to file
  python extract_transcript.py VIDEO_ID --output transcript.txt

  # Specify languages (in order of preference)
  python extract_transcript.py VIDEO_ID --languages en es fr
        """
    )

    parser.add_argument('video', help='YouTube video URL or ID')
    parser.add_argument('--languages', '-l', nargs='+',
                       default=['es', 'es-ES', 'es-MX', 'en'],
                       help='Language codes to try (default: es en)')
    parser.add_argument('--format', '-f',
                       choices=['text', 'timestamps', 'json', 'srt'],
                       default='text',
                       help='Output format (default: text)')
    parser.add_argument('--output', '-o', type=str,
                       help='Output file path (default: stdout)')

    args = parser.parse_args()

    # Extract video ID
    video_id = extract_video_id(args.video)

    # Get transcript
    print(f"Extracting transcript for video: {video_id}", file=sys.stderr)
    result = extract_transcript(video_id, args.languages, args.format)

    # Format output
    output = format_output(result, args.format)

    # Write output
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(output, encoding='utf-8')
        print(f"Transcript saved to: {output_path}", file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
