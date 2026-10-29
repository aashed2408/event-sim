"""Step 5: turn any video in videos/ into events, using the same event model as sim.py.

Usage:
    python phone_demo.py                       # every new video in videos/
    python phone_demo.py videos/myclip.mov     # just this one
    python phone_demo.py --fps 120             # skip the frame-rate question
"""
import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

import numpy as np
import matplotlib
matplotlib.use("Agg")  # draw charts without opening a window
import matplotlib.pyplot as plt
import imageio.v2 as imageio
import imageio_ffmpeg

import sim
from make_gif import event_image, draw_two_panels

VIDEO_TYPES = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
MAX_SECONDS = 5          # use at most the first 5 seconds of each video
MIN_SECONDS = 0.5        # skip videos shorter than half a second
TARGET_WIDTH = 320       # shrink every video to 320 px wide
GIF_FPS = 24             # GIF plays at 24 fps
BYTES_PER_EVENT = 8
TEST_VIDEO_NAME = "test_ball_240fps"   # the fake ball video made by make_gif.py
README_START = "<!-- REAL WORLD START -->"
README_END = "<!-- REAL WORLD END -->"
WARNING = ("Lots of events everywhere. The phone probably moved, or indoor lights were flickering. "
           "Try filming with the phone held still, in daylight.")


def ask_fps():
    """Ask what frame rate the video was filmed at (Enter = 240)."""
    while True:
        try:
            answer = input("What frame rate did you film this at? Press Enter for 240: ").strip()
        except EOFError:          # no keyboard (e.g. run from another program): use 240
            return 240.0
        if answer == "":
            return 240.0
        try:
            fps = float(answer)
            if fps > 0:
                return fps
        except ValueError:
            pass
        print("Please type a number, like 240 or 120.")


def to_gray_small(frame):
    """Colour frame -> grayscale, brightness 0 to 1, shrunk to 320 px wide (keeps the shape)."""
    frame = np.asarray(frame, dtype=float)
    if frame.ndim == 3:
        frame = frame[:, :, :3] @ np.array([0.299, 0.587, 0.114])   # standard gray mix
    gray = frame / 255.0
    h, w = gray.shape
    new_w = TARGET_WIDTH
    new_h = max(1, round(h * new_w / w))
    # Simple bilinear resize: blend the 4 nearest pixels
    ys = np.linspace(0, h - 1, new_h)
    xs = np.linspace(0, w - 1, new_w)
    y0, x0 = np.floor(ys).astype(int), np.floor(xs).astype(int)
    y1, x1 = np.minimum(y0 + 1, h - 1), np.minimum(x0 + 1, w - 1)
    wy, wx = (ys - y0)[:, None], (xs - x0)[None, :]
    top = gray[y0][:, x0] * (1 - wx) + gray[y0][:, x1] * wx
    bottom = gray[y1][:, x0] * (1 - wx) + gray[y1][:, x1] * wx
    return top * (1 - wy) + bottom * wy


def open_video(path, tmp_dir):
    """Open a video for reading one frame at a time.
    If it can't be read (e.g. iPhone HEVC .MOV), convert it to .mp4 first."""
    try:
        reader = imageio.get_reader(path, format="FFMPEG")
        reader.get_data(0)             # make sure at least one frame really decodes
        return reader
    except Exception:
        print("  Couldn't read this video directly, converting it to .mp4 first...")
    converted = os.path.join(tmp_dir, "converted.mp4")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()     # the ffmpeg that comes with imageio-ffmpeg
    result = subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(path), "-t", str(MAX_SECONDS),
                             "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", converted],
                            capture_output=True)
    if result.returncode != 0:
        raise RuntimeError("this file couldn't be read as a video, even after converting it")
    return imageio.get_reader(converted, format="FFMPEG")


def process_video(path, fps):
    """Turn one video into events. Returns a dict of stats, or None if skipped."""
    name = Path(path).stem
    with tempfile.TemporaryDirectory() as tmp_dir:
        reader = open_video(path, tmp_dir)
        file_fps = reader.get_meta_data().get("fps") or fps
        max_frames = int(MAX_SECONDS * file_fps)      # first 5 seconds of the video

        hold_every = max(1, round(fps / 30))           # normal camera keeps every (fps/30)th frame
        slowdown = fps / GIF_FPS                       # each video frame = 1/fps s, shown for 1/24 s
        caption = f"slowed down {slowdown:g}x" if slowdown >= 1 else f"sped up {1 / slowdown:g}x"

        gif_path = f"results/{name}_events.gif"
        writer = imageio.get_writer(gif_path, duration=1000 / GIF_FPS, loop=0)
        cam = None
        total_events = 0
        busy_frames = 0                # frames where more than half the pixels fired
        n_frames = 0
        size = None
        for i, frame in enumerate(reader):
            if i >= max_frames:
                break
            image = to_gray_small(frame)
            t_ms = round(i * 1000 / fps)               # real time of this frame
            if cam is None:
                cam = sim.EventCamera(image)           # same event model, C = 0.2
                events = np.zeros(0, dtype=sim.EVENT_DTYPE)
                held = image
            else:
                events = cam.step(image, t_ms)         # events since the previous frame
            if i % hold_every == 0:
                held = image                           # normal camera takes a new picture
            h, w = image.shape
            size = (w, h)
            fired = np.unique(events["y"].astype(int) * w + events["x"]).size
            if fired > 0.5 * w * h:
                busy_frames += 1
            total_events += len(events)
            n_frames += 1
            writer.append_data(draw_two_panels(held, event_image(events, h, w), caption))
        reader.close()

        # Too short or empty: skip it (and remove the half-made GIF)
        if n_frames == 0 or n_frames / file_fps < MIN_SECONDS:
            writer.close()
            os.remove(gif_path)
            print(f"  '{Path(path).name}' is shorter than half a second (or has no frames), so it was skipped.")
            return None
        writer.close()

    seconds = n_frames / fps                           # real (filmed) time covered
    w, h = size
    stats = {
        "name": name,
        "gif": gif_path,
        "frames": n_frames,
        "fps": fps,
        "size": f"{w} x {h}",
        "seconds": seconds,
        "events": total_events,
        "events_per_s": total_events / seconds,
        "event_kb_s": total_events / seconds * BYTES_PER_EVENT / 1000,
        "frame_kb_s": w * h * 30 / 1000,
        # Frames at the filmed frame rate: what a normal camera needs to match the events' timing
        "film_frame_kb_s": w * h * fps / 1000,
        "busy": busy_frames > n_frames / 2,
    }
    stats["table"] = (
        f"| | |\n|---|---:|\n"
        f"| Frames used | {n_frames} (filmed at {fps:g} fps, {seconds:.2f} s of real time) |\n"
        f"| Picture size | {w} x {h} pixels |\n"
        f"| Total events | {total_events:,} |\n"
        f"| Events per second | {stats['events_per_s']:,.0f} |\n"
        f"| Events, KB per second (8 bytes each) | {stats['event_kb_s']:,.1f} |\n"
        f"| 30 fps frames, KB per second (same size) | {stats['frame_kb_s']:,.1f} |\n"
        f"| {fps:g} fps frames, KB per second (same size, matches event timing) | {stats['film_frame_kb_s']:,.1f} |\n")
    with open(f"results/{name}_stats.md", "w") as f:
        f.write(f"# {Path(path).name}\n\n{stats['table']}")
    stats["chart"] = save_data_chart(stats)
    return stats


def save_data_chart(stats):
    """Bar chart (log scale): KB per second for events vs normal video, like Step 3."""
    labels = ["Events", "Frames 30 fps", f"Frames {stats['fps']:g} fps"]
    values = [stats["event_kb_s"], stats["frame_kb_s"], stats["film_frame_kb_s"]]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(labels, values, color=["tab:red", "tab:gray", "tab:gray"])
    ax.bar_label(bars, labels=[f"{v:,.0f}" for v in values], fontsize=9)
    ax.set_yscale("log")
    # Start the axis well below the smallest bar, so a short bar doesn't look like nothing
    # (and leave room above the tallest bar for its number)
    ax.set_ylim(10 ** (np.floor(np.log10(min(values))) - 1), max(values) * 3)
    ax.set_ylabel("KB per second (log scale)")
    ax.set_title(f"Data per second: {stats['name']}")
    fig.tight_layout()
    chart_path = f"results/{stats['name']}_data_size.png"
    fig.savefig(chart_path, dpi=120)
    plt.close(fig)
    return chart_path


def update_readme(stats):
    """Put the newest video's GIF, data chart and stats between the markers in README.md."""
    if not os.path.exists("README.md"):
        return
    text = open("README.md").read()
    if README_START not in text or README_END not in text:
        return
    before = text.split(README_START)[0]
    after = text.split(README_END)[1]
    # quote() turns spaces and brackets in the file name into %20, %28 ...
    # so the image link still works on GitHub
    middle = (f"\n![{stats['name']} as events]({quote(stats['gif'])})\n\n"
              f"![{stats['name']} data per second]({quote(stats['chart'])})\n\n{stats['table']}")
    with open("README.md", "w") as f:
        f.write(before + README_START + middle + README_END + after)


def main():
    parser = argparse.ArgumentParser(description="Turn videos into event camera output.")
    parser.add_argument("video", nargs="?", help="one video to process (default: all new videos in videos/)")
    parser.add_argument("--fps", type=float, help="frame rate the video was filmed at (skips the question)")
    args = parser.parse_args()

    os.makedirs("results", exist_ok=True)
    os.makedirs("videos", exist_ok=True)

    if args.video:
        videos = [Path(args.video)]
    else:
        # Every video in videos/ that doesn't have results yet
        videos = [p for p in sorted(Path("videos").iterdir())
                  if p.is_file() and p.suffix.lower() in VIDEO_TYPES
                  and not Path(f"results/{p.stem}_stats.md").exists()]
    if not videos:
        print("No new videos to process. Put a video in the videos folder, then run this again.")
        return

    done = []
    for path in videos:
        print(f"\nVideo: {path.name}")
        if path.suffix.lower() not in VIDEO_TYPES:
            print("  Not a video type I know (.mp4 .mov .m4v .avi .mkv), so it was skipped.")
            continue
        fps = args.fps if args.fps else ask_fps()
        try:
            stats = process_video(path, fps)
        except Exception as error:           # never crash on one bad file
            print(f"  Sorry, something went wrong with this video, so it was skipped. ({error})")
            continue
        if stats is None:
            continue
        if stats["busy"]:
            print("  " + WARNING)
        # The fake test ball isn't a real video, so it doesn't go in the README
        if stats["name"] != TEST_VIDEO_NAME:
            update_readme(stats)
        done.append(stats)

    # Plain-English summary
    print("\n===== Summary =====")
    if not done:
        print("No videos were processed.")
        return
    for s in done:
        print(f"{s['name']}: {s['frames']} frames ({s['seconds']:.2f} s of real time) made "
              f"{s['events']:,} events, about {s['events_per_s']:,.0f} events per second.")
        print(f"  That is {s['event_kb_s']:,.1f} KB/s of events vs {s['frame_kb_s']:,.1f} KB/s for 30 fps video.")
        print(f"  Open: {s['gif']}, {s['chart']} and results/{s['name']}_stats.md")
    if any(s["name"] != TEST_VIDEO_NAME for s in done):
        print("README.md's 'Real-world test' section now shows the newest video.")


if __name__ == "__main__":
    sys.exit(main())
