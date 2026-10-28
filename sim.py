"""Shared code: the scene, the event camera model and the normal camera model.

Every other script imports from this file.
"""
import numpy as np

# ---------------- Scene settings ----------------
WIDTH, HEIGHT = 320, 240      # image size in pixels
BACKGROUND = 0.1              # brightness of the dark background
BALL_RADIUS = 8               # ball radius in pixels
BALL_BRIGHTNESS = 0.9         # brightness of the ball
PIXELS_PER_METER = 160        # 160 pixels = 1 meter
STEPS_PER_SECOND = 1000       # 1 simulation step = 1 millisecond
BALL_Y = HEIGHT // 2          # the ball moves along the middle row

# The ball's soft edge reaches out to radius + 0.5 pixels,
# so a centre at -(radius + 1) means the ball starts fully outside the image.
START_X = -(BALL_RADIUS + 1)

# ---------------- Camera settings ----------------
THRESHOLD = 0.2               # event threshold C (in log brightness)
EPS = 1e-3                    # small number so log(0) never happens
FRAME_GAP = 33                # normal camera takes a picture every 33 steps (~30 fps)
EVENT_DETECT_COUNT = 5        # event camera "notices" the ball at >= 5 events in one step
FRAME_DETECT_SUM = 5.0        # normal camera "notices" when sum |frame - background| > 5

SEED = 42                     # fixed random seed so results repeat

# One event = (time in ms, x, y, polarity). Polarity +1 = brighter, -1 = darker.
EVENT_DTYPE = np.dtype([("t", np.int32), ("x", np.int16), ("y", np.int16), ("p", np.int8)])

# x and y coordinate of every pixel (worked out once, reused for every image)
_YS, _XS = np.mgrid[0:HEIGHT, 0:WIDTH]


def ball_x(speed_mps, t_ms):
    """Where the ball's centre is (in pixels) at time t_ms."""
    pixels_per_ms = speed_mps * PIXELS_PER_METER / STEPS_PER_SECOND
    return START_X + pixels_per_ms * t_ms


def render(ball_cx, background=None):
    """Draw one image of the ball with its centre at x = ball_cx.

    background: an image to draw the ball on. If None, use the plain dark background.
    """
    if background is None:
        background = np.full((HEIGHT, WIDTH), BACKGROUND)
    # Distance from every pixel to the ball's centre
    dist = np.sqrt((_XS - ball_cx) ** 2 + (_YS - BALL_Y) ** 2)
    # How much of each pixel is covered by the ball: 1 inside, 0 outside,
    # and a soft 1-pixel edge in between (so tiny moves still change brightness).
    cover = np.clip(BALL_RADIUS + 0.5 - dist, 0.0, 1.0)
    return background * (1 - cover) + BALL_BRIGHTNESS * cover


class EventCamera:
    """A simple event camera: each pixel fires when its log brightness changes by C."""

    def __init__(self, first_image, threshold=THRESHOLD):
        self.C = threshold
        # Each pixel remembers a reference log brightness, starting at the first image
        self.ref = np.log(first_image + EPS)

    def step(self, image, t_ms):
        """Look at a new image and return the events it causes."""
        L = np.log(image + EPS)
        diff = L - self.ref
        # How many whole thresholds did each pixel change by?
        n = np.floor(np.abs(diff) / self.C).astype(np.int64)
        sign = np.sign(diff)
        # Move the reference by whole thresholds (not all the way to L)
        self.ref += sign * n * self.C

        # Build the list of events: pixel (x, y) gets n events
        ys, xs = np.nonzero(n)
        counts = n[ys, xs]
        events = np.zeros(counts.sum(), dtype=EVENT_DTYPE)
        events["t"] = t_ms
        events["x"] = np.repeat(xs, counts)
        events["y"] = np.repeat(ys, counts)
        events["p"] = np.repeat(sign[ys, xs], counts)
        return events


def frame_times(phase, total_steps):
    """Steps at which the normal camera takes a picture (every 33 steps, starting at phase)."""
    return range(phase, total_steps, FRAME_GAP)


def event_detect_time(speed_mps, max_steps=5000):
    """First step (ms) where the event camera sees at least 5 events."""
    cam = EventCamera(render(ball_x(speed_mps, 0)))
    for t in range(1, max_steps):
        events = cam.step(render(ball_x(speed_mps, t)), t)
        if len(events) >= EVENT_DETECT_COUNT:
            return t
    return None


def frame_detect_time(speed_mps, phase, max_steps=5000):
    """First frame time (ms) where the normal camera's picture differs enough from the empty background."""
    empty = np.full((HEIGHT, WIDTH), BACKGROUND)
    for t in frame_times(phase, max_steps):
        frame = render(ball_x(speed_mps, t))
        if np.abs(frame - empty).sum() > FRAME_DETECT_SUM:
            return t
    return None
