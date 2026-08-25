import math

def calculate_angle(point_a, point_b, point_c):
    """
    Calculates 2D angle (in degrees) at vertex point_b formed by segments (BA) and (BC).
    Each point can be a tuple/list (x, y) or dict {"x": x, "y": y}.

    Returns:
        float: Angle in degrees in range [0.0, 180.0].
    """
    if isinstance(point_a, dict):
        a = (point_a["x"], point_a["y"])
    else:
        a = (point_a[0], point_a[1])

    if isinstance(point_b, dict):
        b = (point_b["x"], point_b["y"])
    else:
        b = (point_b[0], point_b[1])

    if isinstance(point_c, dict):
        c = (point_c["x"], point_c["y"])
    else:
        c = (point_c[0], point_c[1])

    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])

    dot_product = ba[0] * bc[0] + ba[1] * bc[1]
    magnitude_ba = math.hypot(ba[0], ba[1])
    magnitude_bc = math.hypot(bc[0], bc[1])

    if magnitude_ba == 0 or magnitude_bc == 0:
        return 0.0

    cosine_angle = dot_product / (magnitude_ba * magnitude_bc)
    cosine_angle = max(-1.0, min(1.0, cosine_angle))

    angle_rad = math.acos(cosine_angle)
    angle_deg = math.degrees(angle_rad)

    return round(angle_deg, 2)


def get_body_inclination(point_a, point_b):
    """
    Calculates the inclination angle (in degrees) of line segment AB relative to horizontal plane.
    0 degrees = completely horizontal, 90 degrees = completely vertical.
    """
    if isinstance(point_a, dict):
        a = (point_a["x"], point_a["y"])
    else:
        a = (point_a[0], point_a[1])

    if isinstance(point_b, dict):
        b = (point_b["x"], point_b["y"])
    else:
        b = (point_b[0], point_b[1])

    dx = abs(b[0] - a[0])
    dy = abs(b[1] - a[1])

    if dx == 0:
        return 90.0

    angle_rad = math.atan2(dy, dx)
    return round(math.degrees(angle_rad), 2)


class AngleSmoother:
    """
    Applies Exponential Moving Average (EMA) to smooth frame-to-frame joint angles.
    """
    def __init__(self, alpha=0.35):
        self.alpha = alpha
        self.smoothed_value = None

    def update(self, new_value):
        if self.smoothed_value is None:
            self.smoothed_value = new_value
        else:
            self.smoothed_value = (self.alpha * new_value) + ((1 - self.alpha) * self.smoothed_value)
        return self.smoothed_value

    def reset(self):
        self.smoothed_value = None
