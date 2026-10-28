# Event Camera Simulator — Project Spec

## What this project is
A Python simulator that shows how an event camera "sees" a fast ball, compared with a normal 30 fps camera.
The owner is a beginner. Deadline: finished in one day.

## Rules for Claude Code
- Keep code simple and readable. Add short comments a grade 10 student can follow.
- Dependencies: numpy, matplotlib, imageio, imageio-ffmpeg ONLY (opencv-python only for the optional webcam demo).
- Use a virtual environment (`.venv`) and a `requirements.txt`.
- After every change, RUN the script and check the output matches the "Expected" notes below. Fix it if not.
- Use a fixed random seed (42) so results are repeatable.
- Do not add features that are not in this spec.
- All outputs go in `results/`.

## Files
```
sim.py           # scene, event model, frame camera (shared code)
make_gif.py      # Step 1 visual
dodge_test.py    # Step 2 experiment + chart
data_test.py     # Step 3 experiment + chart
README.md        # Step 4 write-up
phone_demo.py    # Step 5 turns any video in videos/ into events
videos/          # the user drops their own videos here
results/         # all images, gifs, tables
```

## Scene (synthetic — no real video)
- Image: 320 x 240 pixels, grayscale, brightness values 0 to 1.
- Background: plain dark, brightness 0.1.
- Ball: radius 8 px, brightness 0.9, anti-aliased edge (soft 1-pixel edge so sub-pixel motion still changes brightness).
- Scale: 160 pixels = 1 meter (view is 2 m wide).
- Simulation clock: 1000 steps per second (1 step = 1 ms).
- Ball moves left to right along the middle row. It starts fully outside the left edge.

## Event camera model (sim.py)
- Work on log brightness: `L = log(I + 1e-3)`.
- Each pixel keeps a reference log brightness, starting at the first image.
- Each step: `diff = L - ref`. Number of events per pixel: `n = floor(|diff| / C)`, threshold `C = 0.2`.
- Emit n events at that pixel. Polarity = +1 if brighter, -1 if darker.
- Update: `ref += sign(diff) * n * C` (move the reference by whole thresholds; do NOT reset it to L).
- Event = (t_ms, x, y, polarity). Store as a numpy structured array.

## Normal camera model (sim.py)
- Takes a snapshot of the scene every 33 steps (about 30 fps).
- Start offset ("phase") is random from 0 to 32 steps, so the ball can appear at any point between frames.

## Detection rules
- Event camera "notices" the ball at the first step with at least 5 events.
- Normal camera "notices" the ball at the first frame where the sum of |frame - empty background| > 5.

## Step 1 — Visual (make_gif.py)
- Ball at 10 m/s.
- `results/events_vs_frames.gif`: two panels side by side.
  - Left, titled "Normal camera (30 fps)": shows the most recent 30 fps frame (it freezes between frames).
  - Right, titled "Event camera": events from the last 5 ms, red = brighter (ON), blue = darker (OFF), on black.
- Render every 2nd simulation step, play at 20 fps, add the caption "slowed down 25x" (each GIF frame shows 2 ms of real time but stays on screen for 50 ms).
- Expected: red dots on the ball's front edge, blue on the back edge, nothing in the background. Left panel jumps in steps.

## Step 2 — Dodge test (dodge_test.py)
- Speeds: 1, 2, 5, 10, 15, 20 m/s. 30 trials per speed, each with a random camera phase.
- For each trial, record:
  - head start in ms = (normal camera detection time) - (event camera detection time)
  - distance in cm = speed x head start (how far the ball moved before the normal camera noticed)
- `results/dodge_test.png`: two panels.
  - Left: head start (ms) vs speed — mean with a shaded min-to-max band.
  - Right: distance (cm) vs speed — mean with a shaded min-to-max band.
- `results/dodge_test.csv`: one row per trial.
- Print a summary table.
- Expected: head start averages about 15–20 ms and stays roughly FLAT across speeds (max about 33 ms). Distance grows with speed: about 15–20 cm at 10 m/s, 30–40 cm at 20 m/s. If not, something is wrong.

## Step 3 — Data size (data_test.py)
- 1 second of simulation, ball at 10 m/s, two scenes:
  1. Still camera: plain background (as above).
  2. Moving camera: background is a smooth random gray texture (seed 42; random 8x8-pixel blocks, blurred, brightness 0.2–0.6) that shifts 1 px per step, to mimic a drone's camera turning.
- Size estimates:
  - Events: 8 bytes per event (simple packed format; real sensors compress better, so this is rough).
  - Frames at 30 fps: 320 x 240 x 1 byte x 30.
  - Frames at 1000 fps (needed to match event timing): 320 x 240 x 1 byte x 1000.
- `results/data_size.png`: bar chart, log scale, KB per second for each option and scene.
- `results/data_size.md`: small table of the numbers.
- Expected: still camera → event data is far smaller than 1000 fps frames (the fair comparison, since that is what a normal camera needs to match event timing), but a bright, fast object can still make events about a third the size of 30 fps frames. Moving camera → event data explodes, far above 30 fps frames and possibly above 1000 fps frames. (Real sensors cap their event rate and drop events when overloaded; mention this in the README limitations.)

## Step 4 — README.md
Sections: title, one-line summary, the GIF, how it works (4 short bullets), results (both charts + a "Findings" section left as `TODO: write in your own words`), limitations, how to run, credits.

Limitations to list honestly:
- Synthetic scene, not real footage.
- Simple sensor model: no noise, no per-pixel threshold differences, no refractory period, no readout or bandwidth limits.
- Head start counts only when each camera first "notices" the ball; it ignores processing time on a real drone.
- 1 ms simulation steps, so event timing is 1 ms here, not microseconds like a real sensor.

Credits: Lichtsteiner, Posch & Delbruck (2008) dynamic vision sensor; Falanga, Kleber & Scaramuzza (2020) event-camera drone obstacle avoidance; v2e (Delbruck group) and ESIM (Scaramuzza group) as real simulators.

## Step 5 — Any video, added later (phone_demo.py)
The user does NOT have a video yet. Build this so it works with ANY video they add later, with no code changes.

How the user will use it:
- They drop one or more videos into a `videos/` folder (create it now, with a short `videos/README.txt` saying "Put your videos here").
- They run `python phone_demo.py`. It processes every video in `videos/` that hasn't been processed yet. `python phone_demo.py videos/myclip.mov` processes just that one.

Requirements:
- Accept common video types: .mp4, .mov, .m4v, .avi, .mkv (any capitalization). Skip other files.
- Read frames one at a time with imageio (ffmpeg plugin), so big videos don't run out of memory. Use at most the first 5 seconds.
- If a video can't be read (for example an iPhone HEVC .MOV), automatically convert it to .mp4 with the ffmpeg binary that comes with imageio-ffmpeg, then read that.
- Frame rate: phones often save slow motion as a 30 fps file even when filmed at 240 fps. So for each video, ask in the terminal: "What frame rate did you film this at? Press Enter for 240". Also accept `--fps 120` on the command line to skip the question.
- Works for any size or shape (portrait or landscape): convert to grayscale, brightness 0 to 1, shrink to 320 px wide keeping the shape.
- Run the SAME event model from sim.py (C = 0.2). Timestamp of frame i = i x 1000 / fps milliseconds.
- Name outputs after the video so nothing gets overwritten:
  - `results/<video name>_events.gif`: same two-panel layout as Step 1. Left "Normal camera (30 fps)": keep only every (fps / 30)th frame and hold it. Right "Event camera": events since the previous frame, red = ON, blue = OFF, on black. Play at 24 fps with a caption saying how much it is slowed down.
  - `results/<video name>_stats.md`: frames used, total events, events per second, and KB per second for events (8 bytes each) vs 30 fps frames at the same size.
- README: add a "Real-world test" section between the lines `<!-- REAL WORLD START -->` and `<!-- REAL WORLD END -->`. Until a real video exists it says "Add a video to the videos folder and run phone_demo.py." Each run replaces what's between the markers with the newest video's GIF and stats.
- If the video is shorter than half a second or has no frames, print a friendly message and skip it. Never crash on one bad file.
- Print a plain-English summary when done, including which files to open.
- After each video, check the event rate. If more than half of all pixels fire events in most frames, print: "Lots of events everywhere. The phone probably moved, or indoor lights were flickering. Try filming with the phone held still, in daylight."

Testing now (the user has no video yet):
- Save the Step 1 fake ball as `videos/test_ball_240fps.mp4` (240 fps, 2 seconds, with the 1000-step sim sampled at 240 fps).
- Run `python phone_demo.py --fps 240` and check that it works. Expected: events only on the ball, and the event-rate warning does NOT appear.
- Also test a 30 fps version and a portrait (tall) version to prove any video works, then delete those two test files.

README limitations to add: event timing is only as fine as the video's frame gap (about 4 ms at 240 fps, 33 ms at 30 fps), and video compression adds some fake events.

## Optional (only if time remains)
- `threshold_test.py`: add Gaussian noise (sigma 0.02) to every image; try C = 0.05, 0.1, 0.2, 0.3, 0.5; plot noise events vs ball events. Expected: small C = lots of noise events; large C = ball starts to get missed.
- `webcam_demo.py`: live webcam → events window, press q to quit. Warn the user that webcam auto-exposure causes floods of false events.
