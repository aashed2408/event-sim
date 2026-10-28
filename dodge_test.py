"""Step 2: how much earlier does the event camera notice the ball than a 30 fps camera?"""
import csv
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sim

SPEEDS = [1, 2, 5, 10, 15, 20]   # ball speeds in m/s
TRIALS = 30                      # trials per speed, each with a random camera phase


def run():
    rng = np.random.default_rng(sim.SEED)
    rows = []
    for speed in SPEEDS:
        # The event camera has no phase, so its detection time is the same every trial
        t_event = sim.event_detect_time(speed)
        for trial in range(TRIALS):
            phase = int(rng.integers(0, sim.FRAME_GAP))   # random start offset 0..32
            t_frame = sim.frame_detect_time(speed, phase)
            head_start = t_frame - t_event                # ms
            distance_cm = speed * head_start / 10         # m/s x ms = mm, /10 = cm
            rows.append({"speed_mps": speed, "trial": trial + 1, "phase_ms": phase,
                         "event_detect_ms": t_event, "frame_detect_ms": t_frame,
                         "head_start_ms": head_start, "distance_cm": distance_cm})
    return rows


def main():
    rows = run()
    os.makedirs("results", exist_ok=True)

    # One row per trial
    with open("results/dodge_test.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # Summary per speed: mean, min, max
    summary = {"head_start_ms": [], "distance_cm": []}
    print(f"{'speed (m/s)':>11} | {'head start ms: mean  min  max':>30} | {'distance cm: mean  min  max':>28}")
    for speed in SPEEDS:
        hs = np.array([r["head_start_ms"] for r in rows if r["speed_mps"] == speed])
        dist = np.array([r["distance_cm"] for r in rows if r["speed_mps"] == speed])
        summary["head_start_ms"].append((hs.mean(), hs.min(), hs.max()))
        summary["distance_cm"].append((dist.mean(), dist.min(), dist.max()))
        print(f"{speed:>11} | {hs.mean():>21.1f} {hs.min():>4} {hs.max():>4} | "
              f"{dist.mean():>18.1f} {dist.min():>4.1f} {dist.max():>4.1f}")

    # Chart: two panels, mean line with a shaded min-to-max band
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    panels = [("head_start_ms", "Head start (ms)"), ("distance_cm", "Distance ball moved (cm)")]
    for ax, (key, label) in zip(axes, panels):
        mean, low, high = np.array(summary[key]).T
        ax.fill_between(SPEEDS, low, high, alpha=0.3, label="min to max")
        ax.plot(SPEEDS, mean, "o-", label="mean")
        ax.set_xlabel("Ball speed (m/s)")
        ax.set_ylabel(label)
        ax.set_ylim(bottom=0)
        ax.grid(alpha=0.3)
        ax.legend()
    axes[0].set_title("How much earlier the event camera notices")
    axes[1].set_title("How far the ball moves in that time")
    fig.tight_layout()
    fig.savefig("results/dodge_test.png", dpi=120)
    print("Saved results/dodge_test.png and results/dodge_test.csv")


if __name__ == "__main__":
    main()
