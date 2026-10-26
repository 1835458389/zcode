"""Colossal weathered limestone guardian at the island's north rim.

The figure faces +Y (north); the main camera looks in from the south, so the
back / back-quarter is what reads on screen.  Built from stacked lofted rings
so crown, shoulders, arms and robe folds survive at long focal length.
"""

import math
import random

import bpy
from mathutils import Matrix, Vector

from sk_core import CFG, MB, TAU, build_object, terrain_z

SCALE = 1.45

# local frame: +Z up, figure faces +Y
# (z, half_x, half_y, y_centre) bottom -> top
PROFILE = [
    (4.0, 12.0, 9.0, 1.0),
    (5.5, 12.6, 9.6, 1.2),
    (8.0, 11.8, 9.2, 1.0),
    (10.5, 10.4, 8.6, 0.8),
    (13.0, 8.6, 7.8, 0.5),
    (15.0, 7.4, 7.0, 0.3),
    (17.0, 8.2, 7.6, 0.2),
    (19.0, 9.4, 8.4, 0.1),
    (20.6, 9.9, 8.8, 0.0),
    (21.6, 8.6, 7.6, 0.0),
    (22.4, 5.6, 5.4, 0.2),
    (23.0, 4.4, 4.4, 0.3),
]

PLINTH_H = 4.0
HEAD_Z = 27.6
CROWN_BASE = 30.0


def _ring(z, hx, hy, cy, n=32, wobble=0.0, phase=0.0):
    pts = []
    for i in range(n):
        a = TAU * i / n + phase
        x = math.cos(a) * hx
        y = math.sin(a) * hy + cy
        if wobble:
            k = 1.0 + wobble * (math.sin(a * 5.0 + 0.7) * 0.5 + math.sin(a * 9.0) * 0.3)
            x *= k
            y = (y - cy) * k + cy
        pts.append((x, y, z))
    return pts


def build_statue(mats, coll, seed):
    mb = MB()
    rng = random.Random(seed + 11)
    yaw = CFG["statue_yaw"]

    # ---- plinth -----------------------------------------------------------
    for (r0, r1, z0, z1) in ((14.8, 14.0, 0.0, 1.2),
                             (13.6, 13.0, 1.2, 2.6),
                             (12.4, 11.8, 2.6, PLINTH_H)):
        mb.cylinder(0, 0, z0, r0, z1 - z0, mats["limestone_dark"], seg=36, r_top=r1)
    for k in range(20):
        a = TAU * k / 20
        mb.box((math.cos(a) * 13.4, math.sin(a) * 13.4, 3.2),
               (1.8, 0.9, 0.8), mats["limestone"], rz=a + math.pi / 2)

    # ---- torso ------------------------------------------------------------
    rings = [_ring(z, hx, hy, cy, 34, wobble=0.012, phase=0.02)
             for (z, hx, hy, cy) in PROFILE]
    mb.loft(rings, mats["limestone"], closed=True, smooth=True,
            cap_bottom=True, cap_top=True)

    # ---- crossed legs: forward mass at the base ---------------------------
    mb.sphere((0.0, 5.6, 6.3), (11.6, 6.2, 3.4), mats["limestone"], seg=26, rings=16)
    mb.sphere((0.0, 8.2, 5.2), (8.4, 3.6, 2.2), mats["limestone"], seg=20, rings=12)
    for s in (-1, 1):
        # folded knee
        mb.sphere((s * 7.4, 6.4, 6.0), (4.2, 4.6, 3.2), mats["limestone"],
                  seg=18, rings=12)

    # ---- robe folds: vertical ridges on the robe --------------------------
    for i in range(26):
        a = TAU * i / 26 + 0.03
        for j in range(8):
            t = j / 7.0
            z = 13.6 - t * 8.4
            hx, hy = 10.4, 8.8
            k = 1.0 + 0.06 * (1.0 - t)
            x, y = math.cos(a) * hx * k, math.sin(a) * hy * k + 0.9
            mb.box((x, y, z), (0.70, 0.70, 1.75), mats["limestone"], rz=a,
                   taper=0.80)

    # ---- shoulders + arms -------------------------------------------------
    sh_z, sh_x = 20.4, 9.4
    for s in (-1, 1):
        mb.sphere((s * sh_x * 0.72, 0.2, sh_z), (5.4, 5.6, 4.4),
                  mats["limestone"], seg=20, rings=14)
        # upper arm
        for k in range(6):
            t = k / 5.0
            mb.sphere((s * (sh_x * 0.80 - 0.30 * t), 0.6 + 0.8 * t,
                       sh_z - 1.6 - t * 4.6),
                      (3.5 - 0.4 * t, 3.7 - 0.4 * t, 3.2),
                      mats["limestone"], seg=16, rings=10)
        # forearm reaching forward to the knee
        for k in range(5):
            t = k / 4.0
            mb.sphere((s * (sh_x * 0.66 - 0.5 * t), 2.4 + 2.8 * t,
                       sh_z - 6.2 - t * 1.8),
                      (2.7 - 0.35 * t, 2.9, 2.5),
                      mats["limestone"], seg=14, rings=9)
        # hand on knee
        mb.sphere((s * 5.6, 6.4, 11.4), (2.4, 3.0, 1.6),
                  mats["limestone"], seg=16, rings=10)

    # ---- neck + head ------------------------------------------------------
    mb.cylinder(0, 0.5, 22.6, 3.7, 3.2, mats["limestone"], seg=22, r_top=3.3)
    mb.sphere((0, 0.8, HEAD_Z), (4.9, 4.5, 5.1), mats["limestone"],
              seg=26, rings=18)
    # jaw / brow planes
    mb.sphere((0, 2.3, HEAD_Z - 2.6), (3.6, 3.0, 2.5), mats["limestone"],
              seg=18, rings=12)
    mb.sphere((0, 2.6, HEAD_Z + 1.9), (4.2, 2.2, 1.4), mats["limestone"],
              seg=18, rings=10)
    for s in (-1, 1):
        mb.sphere((s * 4.7, 0.5, HEAD_Z - 0.3), (0.9, 1.7, 2.3),
                  mats["limestone"], seg=12, rings=8)

    # ---- crown / high headdress ------------------------------------------
    mb.cylinder(0, 0.7, 29.2, 4.8, 2.6, mats["limestone"], seg=26, r_top=4.4)
    z = CROWN_BASE + 1.6
    for (rr, hh) in ((4.4, 2.4), (4.0, 2.2), (3.6, 2.0), (3.1, 1.8)):
        mb.cylinder(0, 0.7, z, rr, hh, mats["limestone"], seg=24, r_top=rr * 0.90)
        z += hh
    top_z = z
    for i in range(13):
        a = TAU * i / 13
        rr = 3.4
        hn = 3.4 + 2.0 * (0.5 + 0.5 * math.cos(a * 2.0))
        mb.box((math.cos(a) * rr, 0.7 + math.sin(a) * rr, top_z + hn * 0.5),
               (1.5, 0.9, hn), mats["limestone"], rz=a, taper=0.16)
    mb.sphere((0, 0.7, top_z + 1.9), (2.3, 2.1, 2.6), mats["limestone"],
              seg=18, rings=12)

    # ---- halo / mandorla behind the head (+Y is the figure's back) ---------
    hx_, hy_, hz_ = 0.0, 2.4, HEAD_Z + 4.4
    for (rr, th) in ((10.8, 0.9), (9.6, 0.8), (8.4, 0.7)):
        pts = [(hx_ + math.cos(TAU * i / 44) * rr,
                hy_,
                hz_ + math.sin(TAU * i / 44) * rr * 1.12) for i in range(44)]
        verts = pts + [(x, y + th, zz) for (x, y, zz) in pts]
        faces = [(i, (i + 1) % 44, 44 + (i + 1) % 44, 44 + i) for i in range(44)]
        mb.add(verts, faces, mats["limestone"], smooth=True)

    # ---- erosion: pitting and chips --------------------------------------
    for _ in range(110):
        a = rng.uniform(0, TAU)
        t = rng.uniform(0.0, 1.0)
        z = 5.0 + t * 14.0
        hx = 11.6 - t * 2.0
        hy = 9.4 - t * 1.6
        x = math.cos(a) * hx
        y = math.sin(a) * hy + 1.0
        s = rng.uniform(0.30, 1.0)
        mb.sphere((x, y, z), (s, s, s * 0.65), mats["limestone_dark"],
                  seg=8, rings=6)

    mb.transform(Matrix.Scale(SCALE, 4))

    sx, sy = CFG["statue_pos"]
    ob = build_object("Statue", mb, mats["list"], coll,
                      loc=(sx, sy, terrain_z(sx, sy) - 1.2),
                      rot=(0.0, 0.0, yaw))
    return ob


def statue_anchor():
    sx, sy = CFG["statue_pos"]
    return Vector((sx, sy, 26.0 * SCALE))
