"""Bounded flat-map planner: two matched cars, known static obstacles, <=36 km/h.

Coordinates are metres relative to the encounter centre. Red faces -Y and
blue +Y. Positive X is red's left and blue's right. Obstacles are supplied
map truth, not perceived objects. Circles conservatively enclose each car.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Obstacle:
    x: float
    y: float
    radius: float


@dataclass(frozen=True)
class Plan:
    mode: str
    offsets: tuple[float, float]
    rejected: tuple[dict, ...] = ()


def position(car, offset, progress):
    """Smooth lane change, hold through passing, return only after clearance."""
    if progress <= 5:
        blend = 0.0
    elif progress < 40:
        u = (progress - 5) / 35
        blend = u * u * (3 - 2 * u)
    elif progress <= 65:
        blend = 1.0
    elif progress < 85:
        u = (progress - 65) / 20
        blend = 1 - u * u * (3 - 2 * u)
    else:
        blend = 0.0
    return offset * blend, (55 - progress) * (1 if car == 0 else -1)


def path(car, offset):
    return [position(car, offset, s) for s in range(0, 131, 2)]


def point_segment_distance(point, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    norm = dx * dx + dy * dy
    t = 0 if norm == 0 else max(0, min(1, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / norm))
    return math.dist(point, (a[0] + t * dx, a[1] + t * dy))


def path_distance(point, points):
    return min(point_segment_distance(point, a, b) for a, b in zip(points, points[1:]))


def choose_plan(obstacles, radii=(2.9, 2.9), speed=30 / 3.6):
    """Choose a fixed pair of complete paths, or require both cars to brake.

    Candidate timing allows +/-0.5 seconds of relative progress. This is a
    bounded geometric screen, not a general dynamics or safety guarantee.
    """
    obstacles = tuple(obstacles)
    if len(radii) != 2 or any(not math.isfinite(r) or r <= 0 for r in radii):
        raise ValueError('Two finite positive vehicle radii are required')
    if not math.isfinite(speed) or not 0 < speed <= 10:
        raise ValueError('This experiment supports speeds in (0, 10] m/s')
    if any(not all(math.isfinite(v) for v in (o.x, o.y, o.radius)) or o.radius <= 0 for o in obstacles):
        raise ValueError('Obstacle geometry must be finite with positive radius')
    # Stable preference: share the dodge; then let one car move if needed.
    candidates = ((3.5, -3.5), (7., 0.), (0., 7.), (-7., 0.), (0., -7.), (-3.5, 3.5))
    rejected = []
    for offsets in candidates:
        reason = None
        for car in (0, 1):
            points = path(car, offsets[car])
            if any(path_distance((o.x, o.y), points) <= radii[car] + o.radius + .6 for o in obstacles):
                reason = f'car {car} swept path intersects obstacle envelope'
                break
        if reason is None:
            # 0.5m samples plus 0.6m margin guard sampling and tracking error.
            for delta in (-.5 * speed, -.25 * speed, 0, .25 * speed, .5 * speed):
                if any(math.dist(position(0, offsets[0], s / 2),
                                 position(1, offsets[1], max(0, min(130, s / 2 + delta))))
                       <= sum(radii) + .6 for s in range(261)):
                    reason = 'vehicle envelopes overlap in the timing window'
                    break
        if reason is None:
            return Plan('pass', offsets, tuple(rejected))
        rejected.append({'offsets': offsets, 'reason': reason})
    return Plan('brake', (0., 0.), tuple(rejected))


def guard_reason(states, radii):
    """Request braking for invalid state or imminent constant-velocity overlap."""
    try:
        if len(states) != 2:
            return 'incomplete vehicle state'
        for s in states:
            values = [*s['pos'], *s['vel'], *s['up'], s['time']]
            if not all(math.isfinite(v) for v in values):
                return 'nonfinite vehicle state'
            if s['up'][2] < .9:
                return 'vehicle lost upright stability'
        if abs(states[0]['time'] - states[1]['time']) > .25:
            return 'vehicle sensor times differ by over 250ms'
        relative = [states[0]['pos'][i] - states[1]['pos'][i] for i in (0, 1)]
        velocity = [states[0]['vel'][i] - states[1]['vel'][i] for i in (0, 1)]
        vv = sum(v * v for v in velocity)
        t = max(0, min(1.0, -sum(p * v for p, v in zip(relative, velocity)) / vv)) if vv else 0
        closest = math.hypot(*(p + t * v for p, v in zip(relative, velocity)))
        if closest <= sum(radii) + .2:
            return 'vehicle envelopes overlap within one-second velocity projection'
    except (KeyError, TypeError, IndexError):
        return 'incomplete vehicle state'
    return None


def matching_configs(a, b):
    """Compare selected physical parts/tuning, excluding paint and UI provenance."""
    def selected(tree, prefix=''):
        result = {prefix: tree.get('chosenPartName', '')}
        for name, child in tree.get('children', {}).items():
            result.update(selected(child, prefix + '/' + name))
        return result
    return (a.get('model') == b.get('model')
            and a.get('vars', {}) == b.get('vars', {})
            and selected(a.get('partsTree', {})) == selected(b.get('partsTree', {})))


def front_aligned_path(points, state):
    """BeamNG AI line nodes track the front point, not the vehicle origin."""
    dx, dy = (state['front'][i] - state['pos'][i] for i in (0,1))
    return [(x + dx, y + dy, .25) for x,y in points]
