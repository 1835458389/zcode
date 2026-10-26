"""Island blockout: irregular top surface, overhanging rim, tapered cliff."""

import math

import bpy

from sk_core import (CFG, MB, TAU, build_object, fbm2, fbm3, rim_radius,
                     smoothstep, terrain_z)

AX = CFG["island_ax"]   # east-west half axis
AY = CFG["island_ay"]   # north-south half axis
SEG = 256
TOP_RINGS = 30
CLIFF_RINGS = 24


def ellipse_r(theta):
    c, s = math.cos(theta), math.sin(theta)
    base = 1.0 / math.sqrt((c / AX) ** 2 + (s / AY) ** 2)
    wob = (1.0 + 0.075 * math.sin(3.0 * theta + 0.7)
           + 0.045 * math.sin(5.0 * theta + 2.1)
           + 0.030 * math.sin(8.0 * theta + 4.3)
           + 0.07 * (fbm2(math.cos(theta) * 2.4, math.sin(theta) * 2.4, 3, CFG["seed"]) - 0.5))
    return base * wob


# (radius factor, z, radial noise amplitude)
CLIFF_PROFILE = [
    (1.000, 0.6, 0.00),
    (1.030, -2.0, 0.00),
    (1.038, -5.0, 0.35),
    (1.020, -10.0, 0.9),
    (0.985, -17.0, 1.4),
    (0.940, -26.0, 1.6),
    (0.878, -36.0, 1.7),
    (0.800, -47.0, 1.6),
    (0.706, -58.0, 1.5),
    (0.596, -68.0, 1.3),
    (0.470, -77.0, 1.0),
    (0.336, -85.0, 0.7),
    (0.190, -91.0, 0.4),
    (0.000, -95.0, 0.0),
]


def build_island(mats, coll):
    mb = MB()
    seed = CFG["seed"]

    # ---- top surface -------------------------------------------------------
    rings = []
    for k in range(TOP_RINGS + 1):
        t = k / TOP_RINGS
        ring = []
        for i in range(SEG):
            th = TAU * i / SEG
            r = ellipse_r(th) * t
            x = math.cos(th) * r
            y = math.sin(th) * r
            # sink the outer band so the wall sits in a shallow basin edge
            z = terrain_z(x, y)
            if t > 0.80:
                z -= 2.4 * smoothstep(0.80, 1.0, t)
            z += (fbm3(x * 0.09, y * 0.09, 0.0, 2, seed) - 0.5) * 0.5 * (1.0 - t)
            ring.append((x, y, z))
        rings.append(ring)

    verts = []
    for ring in rings:
        verts.extend(ring)
    faces = []
    for j in range(TOP_RINGS):
        for i in range(SEG):
            a = j * SEG + i
            b = j * SEG + (i + 1) % SEG
            c = (j + 1) * SEG + (i + 1) % SEG
            d = (j + 1) * SEG + i
            faces.append((a, b, c, d))
    # centre cap: collapse the innermost ring
    zc = terrain_z(0, 0)
    verts.append((0.0, 0.0, zc))
    ci = len(verts) - 1
    for i in range(SEG):
        faces.append((ci, (i + 1) % SEG, i))
    mb.add(verts, faces, mats["ground"], smooth=True)

    # ---- cliff -------------------------------------------------------------
    cliff_rings = [rings[-1]]
    for pi in range(1, len(CLIFF_PROFILE) - 1):
        fac, z, namp = CLIFF_PROFILE[pi]
        ring = []
        for i in range(SEG):
            th = TAU * i / SEG
            r0 = ellipse_r(th)
            wob = 1.0 + namp * 0.055 * (fbm3(math.cos(th) * 3.4, math.sin(th) * 3.4,
                                             z * 0.035, 3, seed) - 0.5) * 2.0
            # vertical buttresses
            wob += 0.030 * math.sin(7.0 * th + z * 0.02) * smoothstep(-8.0, -30.0, min(z, -8.0))
            r = r0 * fac * wob
            dz = (fbm3(math.cos(th) * 5.0, math.sin(th) * 5.0, z * 0.06, 4, seed) - 0.5) * 2.6 * namp
            ring.append((math.cos(th) * r, math.sin(th) * r, z + dz))
        cliff_rings.append(ring)

    verts, faces = [], []
    for r in cliff_rings:
        verts.extend(r)
    ncl = len(cliff_rings)
    for j in range(ncl - 1):
        for i in range(SEG):
            a = j * SEG + i
            b = j * SEG + (i + 1) % SEG
            c = (j + 1) * SEG + (i + 1) % SEG
            d = (j + 1) * SEG + i
            faces.append((a, b, c, d))
    tip = len(verts)
    verts.append((0.0, 0.0, CLIFF_PROFILE[-1][1] - 4.0))
    last = (ncl - 1) * SEG
    for i in range(SEG):
        faces.append((tip, last + (i + 1) % SEG, last + i))
    mb.add(verts, faces, mats["rock"], smooth=True)

    # ---- secondary rock ledges / outcrops on the cliff ---------------------
    for k in range(34):
        th = TAU * (k / 34.0) + 0.11
        r0 = ellipse_r(th)
        z = -14.0 - 62.0 * ((k * 37) % 34) / 34.0
        # find radius factor at this height by interpolation
        fac = 1.0
        for j in range(len(CLIFF_PROFILE) - 1):
            z0 = CLIFF_PROFILE[j][1]
            z1 = CLIFF_PROFILE[j + 1][1]
            if z1 <= z <= z0:
                t = (z - z0) / (z1 - z0)
                fac = CLIFF_PROFILE[j][0] * (1 - t) + CLIFF_PROFILE[j + 1][0] * t
                break
        r = r0 * fac
        cx, cy = math.cos(th) * r, math.sin(th) * r
        s = 7.0 + 5.0 * ((k * 13) % 7) / 7.0
        mb.box((cx, cy, z), (s, s * 0.55, 5.0 + 3.0 * ((k * 5) % 3)),
               mats["rock"], rz=th, taper=0.45)

    ob = build_object("Island", mb, mats["list"], coll)
    return ob


def build_ground_detail(mats, coll, seed):
    """Scattered rock outcrops, boulders and worn paving on the top surface."""
    mb = MB()
    import random
    rng = random.Random(seed + 77)
    for _ in range(150):
        a = rng.uniform(0, TAU)
        rr = math.sqrt(rng.uniform(0.02, 0.96))
        r = ellipse_r(a) * rr
        x, y = math.cos(a) * r, math.sin(a) * r
        z = terrain_z(x, y)
        s = rng.uniform(0.7, 4.2)
        mb.sphere((x, y, z + s * 0.15), (s, s * rng.uniform(0.6, 1.0), s * rng.uniform(0.35, 0.7)),
                  mats["rock"], seg=10, rings=6)
    return build_object("GroundRocks", mb, mats["list"], coll)
