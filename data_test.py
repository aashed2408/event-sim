"""Step 3: how much data does each camera make in 1 second?"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sim

SPEED = 10                      # ball speed in m/s
STEPS = 1000                    # 1 second of simulation
BYTES_PER_EVENT = 8             # simple packed event format
FRAME_BYTES = sim.WIDTH * sim.HEIGHT * 1   # 1 byte per pixel


def blur(image, sigma):
    """Smooth an image with a Gaussian blur (done one direction at a time)."""
    radius = int(3 * sigma)
    x = np.arange(-radius, radius + 1)
    kernel = np.exp(-x ** 2 / (2 * sigma ** 2))
    kernel /= kernel.sum()
    padded = np.pad(image, radius, mode="reflect")
    rows = np.apply_along_axis(lambda r: np.convolve(r, kernel, mode="valid"), 1, padded)
    return np.apply_along_axis(lambda c: np.convolve(c, kernel, mode="valid"), 0, rows)


def make_texture(width):
    """Smooth random gray texture: random 8x8-pixel blocks, blurred, brightness 0.2 to 0.6."""
    rng = np.random.default_rng(sim.SEED)
    blocks = rng.random((sim.HEIGHT // 8, width // 8))
    big = np.kron(blocks, np.ones((8, 8)))          # each random value fills an 8x8 block
    smooth = blur(big, sigma=2)
    smooth = (smooth - smooth.min()) / (smooth.max() - smooth.min())   # 0 to 1
    return 0.2 + 0.4 * smooth                        # 0.2 to 0.6


def count_events(moving_camera):
    """Run 1 second and count the events."""
    if moving_camera:
        # Wide texture so it can slide 1 px per step for the whole second
        texture = make_texture(sim.WIDTH + STEPS + 8)

    def scene(t):
        background = texture[:, t:t + sim.WIDTH] if moving_camera else None
        return sim.render(sim.ball_x(SPEED, t), background)

    cam = sim.EventCamera(scene(0))
    total = 0
    for t in range(1, STEPS):
        total += len(cam.step(scene(t), t))
    return total


def main():
    sizes = {}  # KB per second for each option and scene
    for name, moving in [("Still camera", False), ("Moving camera", True)]:
        n_events = count_events(moving)
        sizes[name] = {
            "Events": n_events * BYTES_PER_EVENT / 1000,
            "Frames 30 fps": FRAME_BYTES * 30 / 1000,
            "Frames 1000 fps": FRAME_BYTES * 1000 / 1000,
        }
        print(f"{name}: {n_events:,} events in 1 second")

    os.makedirs("results", exist_ok=True)

    # Small markdown table
    options = list(sizes["Still camera"].keys())
    lines = ["| Option | Still camera (KB/s) | Moving camera (KB/s) |",
             "|---|---:|---:|"]
    for opt in options:
        lines.append(f"| {opt} | {sizes['Still camera'][opt]:,.1f} | {sizes['Moving camera'][opt]:,.1f} |")
    table = "\n".join(lines)
    with open("results/data_size.md", "w") as f:
        f.write("# Data per second (ball at 10 m/s)\n\n" + table + "\n\n"
                "Events: 8 bytes each. Frames: 320 x 240 pixels, 1 byte each.\n")
    print(table)

    # Bar chart, log scale
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = np.arange(len(options))
    width = 0.38
    for i, scene_name in enumerate(sizes):
        values = [sizes[scene_name][opt] for opt in options]
        bars = ax.bar(x + (i - 0.5) * width, values, width, label=scene_name)
        ax.bar_label(bars, labels=[f"{v:,.0f}" for v in values], fontsize=8)
    ax.set_xticks(x, options)
    ax.set_yscale("log")
    ax.set_ylabel("KB per second (log scale)")
    ax.set_title("How much data each camera makes per second")
    ax.legend(loc="center")
    fig.tight_layout()
    fig.savefig("results/data_size.png", dpi=120)
    print("Saved results/data_size.png and results/data_size.md")


if __name__ == "__main__":
    main()
