"""Render a captioned tour from committed browser captures; no browser automation."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
TOUR = ROOT / "docs" / "tour"
FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")


def run(args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)


def timecode(seconds):
    return f"{seconds // 3600:02}:{seconds // 60 % 60:02}:{seconds % 60:02}.000"


def main():
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise SystemExit(f"Install {tool} before rendering the optional tour.")
    if not FONT.is_file() or not BOLD.is_file():
        raise SystemExit("Install DejaVu Sans fonts or update FONT/BOLD paths in this script.")
    storyboard = json.loads((TOUR / "storyboard.json").read_text())
    scenes = storyboard["scenes"]
    expected_start = 0
    for scene in scenes:
        source = (TOUR / scene["image"]).resolve()
        if TOUR.resolve() not in source.parents:
            raise ValueError("Screenshot must be inside the committed tour directory.")
        if hashlib.sha256(source.read_bytes()).hexdigest() != scene["image_sha256"]:
            raise ValueError(f"Screenshot hash mismatch: {scene['image']}")
        if scene["start_seconds"] != expected_start or scene["duration_seconds"] <= 0:
            raise ValueError("Scenes must be contiguous with positive durations.")
        expected_start += scene["duration_seconds"]
        if len(scene["caption_lines"]) != 2:
            raise ValueError("Each scene must provide two readable caption lines.")
    if expected_start != storyboard["duration_seconds"]:
        raise ValueError("Storyboard duration does not match its scenes.")

    output = TOUR / "lending-simulator-tour.mp4"
    with tempfile.TemporaryDirectory(prefix="lending-tour-") as name:
        work = Path(name)
        clips = []
        for scene in scenes:
            n = scene["number"]
            title = work / f"title-{n}.txt"
            title.write_text(f"Screenshot tour | {n}/{len(scenes)} | {scene['title']}")
            filters = [
                "pad=1600:1200:(ow-iw)/2:80:color=0xf8fafc",
                "drawbox=x=0:y=0:w=iw:h=78:color=0x182c3e:t=fill",
                f"drawtext=fontfile={BOLD}:textfile={title}:expansion=none:fontsize=30:fontcolor=white:x=40:y=22",
            ]
            for line, y in zip(scene["caption_lines"], (1044, 1084)):
                text = work / f"caption-{n}-{y}.txt"
                text.write_text(line)
                filters.append(f"drawtext=fontfile={FONT}:textfile={text}:expansion=none:fontsize=26:fontcolor=0x182c3e:x=40:y={y}")
            footer = work / "footer.txt"
            footer.write_text("Synthetic expected-value projections | Uncalibrated | Six real dashboard screenshots | No audio")
            filters.append(f"drawtext=fontfile={FONT}:textfile={footer}:expansion=none:fontsize=20:fontcolor=0x334155:x=40:y=1160")
            clip = work / f"scene-{n}.mp4"
            run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-framerate", "5",
                 "-i", str(TOUR / scene["image"]), "-t", str(scene["duration_seconds"]),
                 "-vf", ",".join(filters), "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                 "-pix_fmt", "yuv420p", "-r", "5", "-g", "75", "-an", str(clip)])
            clips.append(clip)
        concat = work / "clips.txt"
        concat.write_text("".join(f"file '{clip}'\n" for clip in clips))
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
             "-i", str(concat), "-c", "copy", "-movflags", "+faststart",
             "-metadata", f"title={storyboard['title']} - captioned screenshot tour",
             "-metadata", "comment=Six real screenshots with captions; no continuous screen recording or audio.", str(output)])

    transcript = ["# Captioned screenshot tour transcript", "",
                  "A 90-second sequence of six actual hosted-dashboard screenshots, with captions and no audio.",
                  "This is an assembled screenshot tour. It contains no continuous interaction recording.", ""]
    vtt = ["WEBVTT", ""]
    for scene in scenes:
        start = scene["start_seconds"]
        end = start + scene["duration_seconds"]
        transcript.extend([f"## {start:02}–{end:02} seconds: {scene['title']}", "", *scene["caption_lines"], ""])
        vtt.extend([f"{timecode(start)} --> {timecode(end)}", *scene["caption_lines"], ""])
    (TOUR / "transcript.md").write_text("\n".join(transcript))
    (TOUR / "captions.vtt").write_text("\n".join(vtt))
    print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
