"""City assembly: perimeter wall band, Poisson-disk courtyard ring, core plaza."""

import math
import random

from mathutils import Matrix, Vector

from sk_core import CFG, MB, TAU, build_object, terrain_z
from sk_parts import (TEMPLATES, _M, city_wall_segment, emit, railing,
                      t_bell_tower, t_cross_hall, t_gate_tower, t_pavilion,
                      t_terrace_hall, t_tower)
from sk_island import ellipse_r


def _statue_dist(x, y):
    sx, sy = CFG["statue_pos"]
    return math.hypot(x - sx, y - sy)


def _wall_ring(seed, n=132, factor=0.845):
    pts = []
    for i in range(n):
        th = TAU * i / n
        r = ellipse_r(th) * factor
        pts.append((math.cos(th) * r, math.sin(th) * r, th))
    return pts


def build_wall(mats, coll, seed):
    mb = MB()
    pts = _wall_ring(seed)
    n = len(pts)
    gates = []
    for i in range(n):
        x0, y0, th0 = pts[i]
        x1, y1, th1 = pts[(i + 1) % n]
        mx, my = (x0 + x1) * 0.5, (y0 + y1) * 0.5
        if _statue_dist(mx, my) < 37.0:
            continue
        city_wall_segment(mb, mats, (x0, y0), (x1, y1), h=9.0, t=5.2)
        if i % 11 == 0:
            gates.append((mx, my, math.atan2(y1 - y0, x1 - x0), th0))

    # gate towers on the accessible faces (skip the statue/north side)
    for (x, y, yaw, th) in gates:
        if abs(math.sin(th)) > 0.82 and math.cos(th) > 0.0:
            continue
        if _statue_dist(x, y) < 46.0:
            continue
        emit(mb, t_gate_tower(mats, w=12.0, d=8.5, h=8.4),
             _M(x, y, -0.4, yaw + math.pi * 0.5, 1.0))

    ob = build_object("CityWall", mb, mats["list"], coll)
    return ob


def _poisson(seed, count, rmin=26.0, tries=8000):
    rng = random.Random(seed)
    sx, sy = CFG["statue_pos"]
    pts = []
    for _ in range(tries):
        if len(pts) >= count:
            break
        th = rng.uniform(0, TAU)
        t = rng.uniform(0.50, 0.785)
        r = ellipse_r(th) * t
        x, y = math.cos(th) * r, math.sin(th) * r
        if math.hypot(x - sx, y - sy) < 43.0:
            continue
        ok = True
        for (px, py) in pts:
            if math.hypot(x - px, y - py) < rmin:
                ok = False
                break
        if ok:
            pts.append((x, y))
    return pts


KINDS = ["corridor_court", "main_hall", "wing", "tower", "pavilion",
         "corridor_court", "cross_hall", "bell_tower", "gate_hall",
         "corridor_court", "main_hall", "wing", "tower", "pavilion"]


def build_courtyards(mats, coll, seed):
    mb = MB()
    rng = random.Random(seed + 5)
    pts = _poisson(seed + 3, CFG["courtyard_count"])
    for i, (x, y) in enumerate(pts):
        kind = KINDS[i % len(KINDS)]
        fn = TEMPLATES[kind]
        s = rng.uniform(0.92, 1.08)
        yaw = math.atan2(y, x) + math.pi + rng.uniform(-0.28, 0.28)
        z = terrain_z(x, y) - 0.25
        if kind in ("main_hall", "cross_hall", "terrace_hall"):
            bw, bd, bh = 20.0, 13.0, 6.4
        elif kind in ("corridor_court",):
            bw, bd, bh = 22.0, 18.0, 4.2
        elif kind in ("tower", "bell_tower"):
            bw, bd, bh = 11.0, 11.0, 4.2
        elif kind in ("pavilion",):
            bw, bd, bh = 7.0, 7.0, 4.2
        else:
            bw, bd, bh = 14.0, 8.0, 4.8
        if kind == "corridor_court":
            geo = fn(mats, w=bw, d=bd)
        elif kind in ("tower", "bell_tower", "pavilion"):
            geo = fn(mats, w=bw, h=bh)
        else:
            geo = fn(mats, w=bw, d=bd, h=bh)
        emit(mb, geo, _M(x, y, z, yaw, s))
    return build_object("Courtyards", mb, mats["list"], coll)


def build_core(mats, coll, seed):
    """Symmetrical high-terrace axis just south of the statue."""
    mb = MB()
    cy = -12.0
    z = terrain_z(0, cy) - 0.4

    # main terrace hall on the axis, facing south (front is -Y)
    emit(mb, t_terrace_hall(mats, w=26.0, d=17.0, h=7.6), _M(0, cy + 10.0, z, 0.0, 1.0))
    # flanking cross halls facing inward
    for s in (-1, 1):
        emit(mb, t_cross_hall(mats, w=18.0, d=12.0, h=6.0),
             _M(s * 30.0, cy - 2.0, z - 0.2, s * math.pi * 0.5, 1.0))
    # bell / drum pair flanking the axis
    for s in (-1, 1):
        emit(mb, t_bell_tower(mats, w=9.0, h=4.0),
             _M(s * 17.0, cy - 17.0, z - 0.3, 0.0, 1.0))
    # courtyard towers behind
    for s in (-1, 1):
        emit(mb, t_tower(mats, w=9.0, h=3.8, storeys=3),
             _M(s * 37.0, cy + 20.0, z - 0.5, 0.0, 1.0))

    # ceremonial axis: paved spine, balustrades, stair flights
    mb.box((0, cy - 12.0, z + 0.30), (11.0, 44.0, 0.5), mats["stone_dark"])
    mb.box((0, cy - 12.0, z + 0.56), (8.0, 42.0, 0.14), mats["stone"])
    for s in (-1, 1):
        railing(mb, mats, s * 5.6, cy - 33.0, s * 5.6, cy + 8.0, z + 0.60, 1.05)

    # courtyard-facing gate pavilions
    for s in (-1, 1):
        emit(mb, t_pavilion(mats, w=6.4, h=4.2),
             _M(s * 24.0, cy - 30.0, z - 0.2, 0.0, 1.0))

    return build_object("CorePlaza", mb, mats["list"], coll)


def build_statue_plaza(mats, coll, seed):
    """Paved apron and low balustrade framing the colossus."""
    mb = MB()
    sx, sy = CFG["statue_pos"]
    z = terrain_z(sx, sy) - 0.2
    mb.cylinder(sx, sy, z, 21.0, 1.1, mats["stone_dark"], seg=40)
    mb.cylinder(sx, sy, z + 1.05, 20.4, 0.35, mats["stone"], seg=40)
    for i in range(28):
        a = TAU * i / 28
        if math.sin(a) > 0.55:
            continue
        x = sx + math.cos(a) * 21.0
        y = sy + math.sin(a) * 21.0
        mb.box((x, y, z + 1.7), (1.4, 1.4, 1.2), mats["stone_dark"], rz=a)
    return build_object("StatuePlaza", mb, mats["list"], coll)


def build_bailey(mats, coll, seed):
    """Low houses filling gaps between courtyards: keeps the city dense."""
    mb = MB()
    rng = random.Random(seed + 21)
    for _ in range(150):
        th = rng.uniform(0, TAU)
        t = rng.uniform(0.46, 0.79)
        r = ellipse_r(th) * t
        x, y = math.cos(th) * r, math.sin(th) * r
        if _statue_dist(x, y) < 34.0:
            continue
        w = rng.uniform(6.0, 14.0)
        d = rng.uniform(4.0, 7.5)
        h = rng.uniform(3.0, 4.6)
        yaw = rng.uniform(0, math.pi)
        z = terrain_z(x, y) - 0.2
        mb.box((x, y, z + 0.5), (w, d, 1.0), mats["stone_dark"], rz=yaw)
        mb.box((x, y, z + 1.0 + h * 0.5), (w * 0.9, d * 0.86, h),
               mats["timber"], rz=yaw)
        mb.box((x, y, z + 1.0 + h - 0.25), (w * 1.06, d * 1.02, 0.5),
               mats["tile_dark"], rz=yaw, taper=0.92)
        mb.box((x, y, z + 1.0 + h + 0.1), (w * 0.9, 0.5, 0.34),
               mats["tile"], rz=yaw)
    return build_object("Bailey", mb, mats["list"], coll)
