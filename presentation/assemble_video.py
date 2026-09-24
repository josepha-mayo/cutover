"""Assemble real demo captures and final narration into a reviewable MP4.

The clip manifest is deliberately separate from narration and Bob provenance.
This script only checks media integrity and timing; it cannot prove what a clip
shows. Review every recorded frame and claim before publishing the result.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def validate_submission_media(path: Path) -> None:
    # The general lablab.ai submission guide sets a 300 MB presentation limit.
    if path.stat().st_size >= 300_000_000:
        raise ValueError(f"Video exceeds the 300 MB submission limit: {path}")
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "stream=codec_type,codec_name,width,height,avg_frame_rate",
            "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    streams = json.loads(result.stdout)["streams"]
    video = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if len(video) != 1 or video[0].get("codec_name") != "h264":
        raise ValueError("Expected exactly one H.264 video stream")
    if (video[0].get("width"), video[0].get("height")) != (1920, 1080):
        raise ValueError("Expected a 1920×1080 video stream")
    if video[0].get("avg_frame_rate") != "30/1":
        raise ValueError("Expected a 30 fps video stream")
    if len(audio) != 1 or audio[0].get("codec_name") != "aac":
        raise ValueError("Expected exactly one AAC narration stream")


def assemble(manifest_path: Path, narration: Path, output: Path,
             allow_test_assembly: bool = False) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    clips = manifest["clips"]
    target = float(manifest["duration_sec"])
    if not 0 < target <= 180 or not clips:
        raise ValueError("Expected a nonempty demo of at most 180 seconds")
    test_assembly = (bool(manifest.get("assembly_test_only")) or any(
        "assembly-test" in str(clip.get("path", "")).lower() for clip in clips
    ) or any(marker in narration.name.lower() for marker in
             ("test-only", "timing-test", "negative-control")))
    if test_assembly and not allow_test_assembly:
        raise ValueError("Test footage or narration requires --test-assembly")
    if test_assembly and "assembly-test" not in output.name.lower():
        raise ValueError("Test output filename must contain assembly-test")
    if not narration.is_file():
        raise FileNotFoundError(narration)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")

    clip_paths: list[Path] = []
    clip_intervals: list[tuple[float, float]] = []
    total = 0.0
    for clip in clips:
        if "PENDING" in json.dumps(clip).upper():
            raise ValueError("Replace pending clip descriptions before assembly")
        path = project_path(clip["path"])
        start = float(clip.get("start_sec", 0))
        length = float(clip["duration_sec"])
        if not path.is_file() or start < 0 or length <= 0:
            raise ValueError(f"Invalid clip {path}")
        if start + length > duration(path) + 0.08:
            raise ValueError(f"Clip {path} ends after its recorded media")
        clip_paths.append(path)
        clip_intervals.append((start, length))
        total += length

    if abs(total - target) > 0.05:
        raise ValueError(f"Clips total {total:.2f}s, expected {target:.2f}s")
    narration_length = duration(narration)
    if abs(narration_length - target) > 0.25:
        raise ValueError(
            f"Narration lasts {narration_length:.2f}s, expected {target:.2f}s"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for path in clip_paths:
        command += ["-i", str(path)]
    command += ["-i", str(narration)]
    filters = []
    for index, (start, length) in enumerate(clip_intervals):
        filters.append(
            f"[{index}:v]trim=start={start:.3f}:duration={length:.3f},"
            "setpts=PTS-STARTPTS,"
            "scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x17221d,"
            f"fps=30,setsar=1,format=yuv420p[v{index}]"
        )
    inputs = "".join(f"[v{index}]" for index in range(len(clips)))
    filters.append(f"{inputs}concat=n={len(clips)}:v=1:a=0[vout]")
    command += [
        "-filter_complex",
        ";".join(filters),
        "-map",
        "[vout]",
        "-map",
        f"{len(clips)}:a:0",
        "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-movflags",
        "+faststart",
        str(output),
    ]
    subprocess.run(command, check=True)
    actual = duration(output)
    if abs(actual - target) > 0.3:
        raise RuntimeError(f"Assembled video lasts {actual:.2f}s, expected {target:.2f}s")
    validate_submission_media(output)
    print(f"Created {output} ({actual:.2f}s, {len(clips)} clips)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--narration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--test-assembly", action="store_true",
                        help="Allow clearly named assembly-test placeholder footage")
    args = parser.parse_args()
    assemble(args.manifest, args.narration, args.output, args.test_assembly)


if __name__ == "__main__":
    main()
