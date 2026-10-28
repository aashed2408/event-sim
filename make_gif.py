"""Step 1: a GIF that shows a normal camera and an event camera side by side.

Also saves the same fake ball as a 240 fps video (videos/test_ball_240fps.mp4)
so phone_demo.py can be tested before you have a real video.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")  # draw images without opening a window
import matplotlib.pyplot as plt
import imageio.v2 as imageio

import sim

SPEED = 10            # ball speed in m/s
RENDER_EVERY = 2      # draw every 2nd simulation step
GIF_FPS = 20          # GIF plays at 20 frames per second
EVENT_WINDOW = 5      # right panel shows events from the last 5 ms

# How much slower than real life the GIF plays:
# each GIF frame shows 2 ms of real time but stays on screen for 1000/20 = 50 ms.
SLOWDOWN = (1000 / GIF_FPS) / RENDER_EVERY


def event_image(events, height, width):
    """Turn a list of events into a picture: red = brighter (ON), blue = darker (OFF), on black."""
    img = np.zeros((height, width, 3))
    # Events are in time order, so a later event paints over an earlier one
    on = events["p"] > 0
    img[events["y"][on], events["x"][on]] = [1, 0, 0]
    img[events["y"][~on], events["x"][~on]] = [0, 0.4, 1]
    return img


def draw_two_panels(frame, events_img, caption):
    """Draw the two panels with matplotlib and return the picture as an array."""
    # Make the figure taller for tall (portrait) images, so any shape fits
    height, width = frame.shape
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 3.9 * height / width + 0.6), dpi=80)
    ax1.imshow(frame, cmap="gray", vmin=0, vmax=1)
    ax1.set_title("Normal camera (30 fps)")
    ax2.imshow(events_img)
    ax2.set_title("Event camera")
    for ax in (ax1, ax2):
        ax.set_xticks([])
        ax.set_yticks([])
    fig.text(0.5, 0.03, caption, ha="center")
    fig.canvas.draw()
    picture = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()
    plt.close(fig)
    return picture


def make_gif():
    rng = np.random.default_rng(sim.SEED)
    phase = int(rng.integers(0, sim.FRAME_GAP))  # random start offset 0..32

    # Long enough for the ball to cross the whole picture and leave
    total_steps = int((sim.WIDTH - 2 * sim.START_X) / (SPEED * sim.PIXELS_PER_METER / 1000)) + 10
    snapshot_steps = set(sim.frame_times(phase, total_steps))

    cam = sim.EventCamera(sim.render(sim.ball_x(SPEED, 0)))
    held_frame = np.full((sim.HEIGHT, sim.WIDTH), sim.BACKGROUND)  # nothing captured yet
    recent = []          # events from recent steps
    pictures = []
    caption = f"slowed down {SLOWDOWN:g}x"

    for t in range(1, total_steps):
        image = sim.render(sim.ball_x(SPEED, t))
        recent.append(cam.step(image, t))
        recent = recent[-EVENT_WINDOW:]          # keep only the last 5 ms
        if t in snapshot_steps:
            held_frame = image                   # normal camera takes a new picture
        if t % RENDER_EVERY == 0:
            events = np.concatenate(recent)
            pictures.append(draw_two_panels(held_frame, event_image(events, sim.HEIGHT, sim.WIDTH), caption))

    os.makedirs("results", exist_ok=True)
    imageio.mimsave("results/events_vs_frames.gif", pictures, duration=1000 / GIF_FPS, loop=0)
    print(f"Saved results/events_vs_frames.gif ({len(pictures)} frames, {caption})")


def make_test_video():
    """Save the fake ball as a 240 fps, 2 second video for testing phone_demo.py."""
    fps = 240
    os.makedirs("videos", exist_ok=True)
    writer = imageio.get_writer("videos/test_ball_240fps.mp4", fps=fps, codec="libx264",
                                quality=10, macro_block_size=16)
    for i in range(2 * fps):
        t_ms = i * 1000 / fps                    # sample the 1 ms simulation at 240 fps
        image = sim.render(sim.ball_x(SPEED, t_ms))
        writer.append_data((image * 255).round().astype(np.uint8))
    writer.close()
    print("Saved videos/test_ball_240fps.mp4 (240 fps, 2 seconds)")


if __name__ == "__main__":
    make_gif()
    make_test_video()
