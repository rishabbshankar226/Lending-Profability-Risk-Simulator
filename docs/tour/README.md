# Captioned dashboard screenshot tour

[Watch or download the 90-second MP4](lending-simulator-tour.mp4) · [Read the transcript](transcript.md) · [WebVTT captions](captions.vtt)

The tour presents six real captures of the hosted desktop dashboard, with captions and no audio. Each scene stays on screen for 15 seconds. It is an assembled screenshot tour; continuous cursor motion, click sequences and real-time response timing were not recorded.

The underlying loan population and risk inputs are synthetic and uncalibrated. The tour explains conditional scenario results and calculation mechanics. It makes no claim of historical prediction accuracy or real business savings.

## Scenes

| Time | View / applied scenario | Source capture |
| --- | --- | --- |
| 0–15s | Base Overview: lending growth decision | [Overview](screenshots/01-overview.jpg) |
| 15–30s | Base Strategy comparison: profit and cash constraints | [Policies](screenshots/02-policies.jpg) |
| 30–45s | Balanced with $1.25m equity: changed recommendation | [Capital](screenshots/03-capital.jpg) |
| 45–60s | Conservative with 2× default assumptions: no profitable eligible policy | [Default stress](screenshots/04-defaults.jpg) |
| 60–75s | Base Methodology: financial timing and reconciliations | [Methodology](screenshots/05-methodology.jpg) |
| 75–90s | Balanced/$1.25m decision brief: tradeoffs and reproducible inputs | [Brief](screenshots/06-brief.jpg) |

The captures were taken in cloud Chrome, in the owner session, on October 7, 2026 (America/Chicago). Native screenshots are 1363 × 936. They are placed without cropping in a 1600 × 1200 video; the title and captions occupy added space outside the screenshots. The storyboard records source-image hashes, observed run IDs and repository/application commits. See [storyboard.json](storyboard.json).

## Media verification

The saved MP4 is H.264, yuv420p, 5 frames per second, 450 frames and exactly 90 seconds, with no audio stream. The complete file decoded without errors. Its MP4 index precedes the media payload for progressive playback. A frame from each scene was visually inspected at 7, 22, 37, 52, 67 and 82 seconds; titles, figures and captions were readable, with no caption clipping. The file's size and SHA-256 are in [media-validation.json](media-validation.json).

The video does not verify anonymous access, mobile layout, full accessibility or hosting performance. A continuous interactive walkthrough remains a separate pending item in the [release checklist](../release-checklist.md).

## Rebuild the optional media

The app does not depend on the media toolchain. On a system with Python, FFmpeg/ffprobe (including libx264 and drawtext) and DejaVu Sans fonts at the paths specified in the script, run from the repository root:

```bash
python scripts/render_tour.py
```

The renderer verifies the committed screenshot hashes and scene timing, then creates the MP4, transcript and WebVTT captions. Encoding may vary with FFmpeg/font versions. The saved media-validation report describes the committed file; after a rebuild, recheck the file's metadata, decode, hash and sample frames before updating that report.
