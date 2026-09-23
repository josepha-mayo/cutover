"""Make reviewable SRT captions from the rendered narration's measured timings.

Sentence timing is estimated within each measured speech segment. Listen to the
final MP4 and adjust any cue boundaries before publishing the captions.
"""
import argparse
import json
import re
import textwrap
from pathlib import Path


def timestamp(seconds):
    milliseconds = round(seconds * 1000)
    hours, rest = divmod(milliseconds, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return f'{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}'


def caption_pieces(text):
    for sentence in re.split(r'(?<=[.!?])\s+', text.strip()):
        clauses = [sentence]
        if len(sentence) > 84:
            commas = [match.end() for match in re.finditer(',', sentence)
                      if 20 <= match.end() <= len(sentence) - 20]
            if commas:
                middle = min(commas, key=lambda position: abs(position - len(sentence) / 2))
                clauses = [sentence[:middle].strip(), sentence[middle:].strip()]
        for clause in clauses:
            lines = textwrap.wrap(clause, width=42, break_long_words=False,
                                  break_on_hyphens=False)
            for index in range(0, len(lines), 2):
                yield '\n'.join(lines[index:index + 2])


def captions(script_path, timings_path):
    script = json.loads(script_path.read_text(encoding='utf-8'))
    timings = json.loads(timings_path.read_text(encoding='utf-8'))
    segments = script['segments']
    if len(segments) != len(timings) or not segments:
        raise ValueError('Narration segments and rendered timings must match')
    cues = []
    previous_end = 0.0
    for segment, timing in zip(segments, timings):
        if segment['id'] != timing['id']:
            raise ValueError('Narration and timing IDs disagree')
        content = segment['text']
        if not content.strip() or 'PENDING' in content.upper() or 'TODO' in content.upper():
            raise ValueError('Replace unfinished narration before captioning')
        start, end = float(timing['start_sec']), float(timing['end_sec'])
        if start < previous_end or end <= start or end > float(script['duration_sec']):
            raise ValueError(f'Invalid speech timing for {segment["id"]}')
        pieces = list(caption_pieces(content))
        weights = [len(piece.replace('\n', '')) for piece in pieces]
        boundary = start
        for index, (piece, weight) in enumerate(zip(pieces, weights)):
            next_boundary = (end if index == len(pieces) - 1 else
                             boundary + (end - boundary) * weight / sum(weights[index:]))
            if next_boundary - boundary < 1.0:
                raise ValueError(f'Caption cue is too short in {segment["id"]}')
            cues.append((boundary, next_boundary, piece))
            boundary = next_boundary
        previous_end = end
    return cues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--script', required=True, type=Path)
    parser.add_argument('--timings', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    cues = captions(args.script, args.timings)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(''.join(
        f'{index}\n{timestamp(start)} --> {timestamp(end)}\n{text}\n\n'
        for index, (start, end, text) in enumerate(cues, 1)), encoding='utf-8')
    print(f'Created {args.output} ({len(cues)} cues; review against the final audio)')


if __name__ == '__main__':
    main()
