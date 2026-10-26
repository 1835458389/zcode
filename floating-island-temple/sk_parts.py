"""Standard components -> parametric templates.

All templates are built in local space with the base at z=0 and the front
facing -Y.  ``emit`` places them into a destination accumulator with a
transform matrix, which is how courtyards and city blocks get assembled.
"""

import math

from mathutils import Matrix, Vector

from sk_core import MB, TAU, clamp

# ------------------------------------------------------------------ helpers --


def _M(x=0.0, y=0.0, z=0.0, yaw=0.0, s=1.0, sz=None):
    return (Matrix.Translation((x, y, z))
            @ Matrix.Rotation(yaw, 4, "Z")
            @ Matrix.Diagonal(Vector((s, s, s if sz is None else sz, 1.0))))


def emit(dst, src, M=None, mat=None):
    if M is None:
        M = Matrix.Identity(4)
    off = len(dst.verts)
    dst.verts.extend([tuple(M @ Vector(v)) for v in src.verts])
    for f, m, sm in zip(src.faces, src.mats, src.smooth):
        dst.faces.append(tuple(i + off for i in f))
        dst.mats.append(m if mat is None else mat)
        dst.smooth.append(sm)


def _lin(a, b, n):
    return [a + (b - a) * i / n for i in range(n + 1)]


# --------------------------------------------------------------- components --


def platform(mb, mats, w, d, h, mat=None):
    mat = mats["stone"] if mat is None else mat
    mb.box((0, 0, h * 0.5), (w, d, h), mat)
    mb.box((0, 0, h + 0.12), (w * 0.97, d * 0.97, 0.24), mats["stone_dark"])
    # front steps
    steps = max(2, int(h / 0.35))
    for i in range(steps):
        z = h * (i + 1) / steps
        y = -d * 0.5 - (steps - i) * 0.45
        mb.box((0, y, z * 0.5), (min(6.0, w * 0.5), 0.9, z), mats["stone_dark"])


def column(mb, mats, x, y, z0, h, r=0.32, mat=None):
    mat = mats["column"] if mat is None else mat
    mb.box((x, y, z0 + 0.16), (r * 3.0, r * 3.0, 0.32), mats["stone"])
    mb.cylinder(x, y, z0, r * 1.12, h * 0.06, mat, seg=12)
    mb.cylinder(x, y, z0 + h * 0.06, r, h * 0.9, mat, seg=12, r_top=r * 0.94)
    mb.cylinder(x, y, z0 + h * 0.96, r * 1.25, h * 0.04, mat, seg=12)


def dougong(mb, mats, x, y, z, s=1.0):
    """Bracket cluster: three tapering tiers plus two outrigger arms."""
    mb.box((x, y, z + 0.16 * s), (1.05 * s, 1.05 * s, 0.32 * s), mats["beam"])
    mb.box((x, y, z + 0.48 * s), (0.86 * s, 1.7 * s, 0.30 * s), mats["beam"])
    mb.box((x, y, z + 0.78 * s), (1.7 * s, 0.86 * s, 0.28 * s), mats["beam"])
    mb.box((x, y, z + 1.02 * s), (2.3 * s, 2.3 * s, 0.24 * s), mats["timber"])


def beam_frame(mb, mats, w, d, z, h=0.55, t=0.28):
    mb.box((0, -d * 0.5, z), (w, t * 1.6, h), mats["beam"])
    mb.box((0, d * 0.5, z), (w, t * 1.6, h), mats["beam"])
    mb.box((-w * 0.5, 0, z), (t * 1.6, d, h), mats["beam"])
    mb.box((w * 0.5, 0, z), (t * 1.6, d, h), mats["beam"])


def wall_panel(mb, mats, x, y, z, w, h, yaw=0.0, mat=None):
    mat = mats["timber"] if mat is None else mat
    mb.box((x, y, z + h * 0.5), (w, 0.34, h), mat, rz=yaw)
    # lattice hint: two thin lighter bands
    mb.box((x, y, z + h * 0.28), (w * 0.96, 0.42, 0.12), mats["stone_dark"], rz=yaw)
    mb.box((x, y, z + h * 0.72), (w * 0.96, 0.42, 0.12), mats["stone_dark"], rz=yaw)


def railing(mb, mats, x0, y0, x1, y1, z, h=0.95):
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    if L < 0.2:
        return
    yaw = math.atan2(dy, dx)
    n = max(2, int(L / 1.1))
    for i in range(n + 1):
        t = i / n
        mb.box((x0 + dx * t, y0 + dy * t, z + h * 0.5),
               (0.16, 0.16, h), mats["stone"])
    mb.box(((x0 + x1) * 0.5, (y0 + y1) * 0.5, z + h),
           (L, 0.14, 0.13), mats["stone"], rz=yaw)
    mb.box(((x0 + x1) * 0.5, (y0 + y1) * 0.5, z + h * 0.45),
           (L, 0.10, 0.09), mats["stone_dark"], rz=yaw)


def roof(mb, mats, w, d, h, over=1.15, rib=1.05, upturn=1.5,
         ridge=True, mat=None, ribs=True, z0=0.0):
    """Hipped roof with concave slope, upturned corners and tile ribs."""
    _n0 = len(mb.verts)
    mat = mats["tile"] if mat is None else mat
    hw = w * 0.5 + over
    hd = d * 0.5 + over
    xs = _lin(-hw, hw, 8)
    prof = [(0.0, 1.0), (0.30, 0.80), (0.60, 0.46), (0.82, 0.22), (1.0, 0.10)]

    for sign in (-1.0, 1.0):
        grid = []
        for x in xs:
            col = []
            edge = clamp((abs(x) - hw * 0.55) / (hw * 0.45))
            for (t, zf) in prof:
                y = sign * hd * t
                z = h * zf
                z += upturn * (edge ** 2.2) * (t ** 2.0)
                # slight ridge sag for a supple eave line
                z -= 0.10 * h * (1.0 - abs(x) / hw) * (1.0 - t)
                col.append((x, y, z))
            grid.append(col)
        verts, faces = [], []
        nz = len(prof)
        for i, col in enumerate(grid):
            verts.extend(col)
            if i:
                for j in range(nz - 1):
                    a = (i - 1) * nz + j
                    b = i * nz + j
                    faces.append((a, b, b + 1, a + 1))
        mb.add(verts, faces, mat, smooth=False)

        if ribs:
            step = rib
            nx = max(2, int((2 * hw) / step))
            for k in range(nx + 1):
                x = -hw + 2 * hw * k / nx
                edge = clamp((abs(x) - hw * 0.55) / (hw * 0.45))
                for j in range(nz - 1):
                    t0, z0f = prof[j]
                    t1, z1f = prof[j + 1]
                    y0, y1 = sign * hd * t0, sign * hd * t1
                    za = h * z0f + upturn * edge ** 2.2 * t0 ** 2.0
                    zb = h * z1f + upturn * edge ** 2.2 * t1 ** 2.0
                    mb.box((x, (y0 + y1) * 0.5, (za + zb) * 0.5 + 0.075),
                           (0.20, abs(y1 - y0) * 1.04, 0.15), mats["tile_dark"])

    # gable / hip end caps
    for sign in (-1.0, 1.0):
        x = sign * hw
        verts = [(-sign * 0.0, -hd, 0.10 * h), (0.0, hd, 0.10 * h),
                 (0.0, 0.0, h)]
        verts = [(x, y, z) for (_, y, z) in verts]
        faces = [(0, 1, 2)] if sign > 0 else [(2, 1, 0)]
        mb.add(verts, faces, mats["timber"])

    if ridge:
        mb.box((0, 0, h + 0.20), (2 * hw * 0.99, 0.52, 0.42), mats["tile_dark"])
        mb.box((0, 0, h + 0.46), (2 * hw * 0.99, 0.34, 0.20), mats["tile"])
        for s in (-1, 1):
            # 脊兽 / ridge beasts at both ends
            mb.box((s * hw * 0.94, 0, h + 0.72), (0.55, 0.42, 0.9),
                   mats["tile_dark"], taper=0.55)
            mb.box((s * hw * 0.94, 0, h + 1.24), (0.34, 0.30, 0.5),
                   mats["tile_dark"], taper=0.3)
            # eave corner upturn spikes
            mb.box((s * hw * 0.995, 0, h * 0.12), (0.22, 0.9, 0.22),
                   mats["tile_dark"], rz=0.0, taper=0.6)

    if z0:
        for i in range(_n0, len(mb.verts)):
            v = mb.verts[i]
            mb.verts[i] = (v[0], v[1], v[2] + z0)


def pyramid_roof(mb, mats, w, h, over=1.0, mat=None, z0=0.0):
    _n0 = len(mb.verts)
    mat = mats["tile"] if mat is None else mat
    hw = w * 0.5 + over
    rings = []
    n = 24
    for (t, zf) in ((1.0, 0.09), (0.68, 0.38), (0.35, 0.70), (0.0, 1.0)):
        ring = []
        r = hw * t + 0.10
        for i in range(n):
            a = TAU * i / n
            z = h * zf + 0.55 * (abs(math.cos(a)) ** 4) * t ** 2
            ring.append((math.cos(a) * r, math.sin(a) * r, z))
        rings.append(ring)
    mb.loft(rings, mat, closed=True, smooth=False, cap_top=False)
    mb.cylinder(0, 0, h * 0.96, 0.20, 0.9, mats["gold"], seg=10, r_top=0.05)
    for i in range(n):
        a = TAU * i / n
        mb.box((math.cos(a) * hw * 0.92, math.sin(a) * hw * 0.92, h * 0.14),
               (0.16, 0.7, 0.16), mats["tile_dark"], rz=a)

    if z0:
        for i in range(_n0, len(mb.verts)):
            v = mb.verts[i]
            mb.verts[i] = (v[0], v[1], v[2] + z0)


def eave_band(mb, mats, w, d, z, s=1.0):
    """Continuous bracket/eave band under a roof."""
    nx = max(2, int(w / 2.2))
    for i in range(nx + 1):
        x = -w * 0.5 + w * i / nx
        for y in (-d * 0.5, d * 0.5):
            dougong(mb, mats, x, y, z, s)
    ny = max(1, int(d / 2.2))
    for i in range(1, ny):
        y = -d * 0.5 + d * i / ny
        for x in (-w * 0.5, w * 0.5):
            dougong(mb, mats, x, y, z, s)


def city_wall_segment(mb, mats, p0, p1, h=9.0, t=5.0, battlement=True):
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    if L < 0.5:
        return
    yaw = math.atan2(dy, dx)
    cx, cy = (x0 + x1) * 0.5, (y0 + y1) * 0.5
    mb.box((cx, cy, h * 0.5), (L, t, h), mats["stone_dark"], rz=yaw)
    mb.box((cx, cy, h * 0.5 + 0.2), (L, t * 1.06, h * 0.55),
           mats["stone"], rz=yaw, taper=0.97)
    mb.box((cx, cy, h + 0.18), (L, t * 1.12, 0.36), mats["stone_dark"], rz=yaw)
    if battlement:
        n = max(2, int(L / 2.4))
        for i in range(n + 1):
            u = -L * 0.5 + L * i / n
            for s in (-1, 1):
                px = cx + math.cos(yaw) * u - math.sin(yaw) * s * (t * 0.44)
                py = cy + math.sin(yaw) * u + math.cos(yaw) * s * (t * 0.44)
                mb.box((px, py, h + 0.85), (1.05, 0.55, 1.1),
                       mats["stone_dark"], rz=yaw)
    # buttress
    mb.box((cx - math.sin(yaw) * 0.0, cy + math.cos(yaw) * 0.0, h * 0.32),
           (3.0, t * 0.55, h * 0.66), mats["stone_dark"], rz=yaw, taper=0.8)


# ---------------------------------------------------------------- templates --


def t_gate_hall(mats, w=12.0, d=7.5, h=5.4):
    """门厅 - three-bay entrance hall, open front."""
    mb = MB()
    platform(mb, mats, w + 2.0, d + 2.0, 0.9)
    z0 = 1.05
    cols = 4
    for i in range(cols):
        x = -w * 0.5 + w * i / (cols - 1)
        for y in (-d * 0.5, d * 0.5):
            column(mb, mats, x, y, z0, h)
    wall_panel(mb, mats, 0, d * 0.5, z0, w * 0.98, h * 0.92)
    for i in range(cols - 1):
        x = -w * 0.5 + w * (i + 0.5) / (cols - 1)
        wall_panel(mb, mats, x, -d * 0.5 + 0.2, z0, w / (cols - 1) * 0.92,
                   h * 0.62, mat=mats["timber"])
    beam_frame(mb, mats, w, d, z0 + h)
    eave_band(mb, mats, w, d, z0 + h + 0.24, 0.85)
    roof(mb, mats, w, d, 3.6, over=1.35, z0=z0 + h + 1.28)
    return mb


def t_main_hall(mats, w=22.0, d=14.0, h=7.0):
    """主殿 - five-bay double-eave hall on a stone terrace."""
    mb = MB()
    platform(mb, mats, w + 4.0, d + 4.0, 1.9)
    z0 = 2.1
    cols = 6
    for i in range(cols):
        x = -w * 0.5 + w * i / (cols - 1)
        for y in (-d * 0.5, 0.0, d * 0.5):
            column(mb, mats, x, y, z0, h, r=0.38)
    wall_panel(mb, mats, 0, d * 0.5 - 0.1, z0, w * 0.99, h * 0.94)
    for s in (-1, 1):
        wall_panel(mb, mats, s * w * 0.5, 0, z0, d * 0.96, h * 0.9)
    # front lattice doors
    for i in range(cols - 1):
        x = -w * 0.5 + w * (i + 0.5) / (cols - 1)
        wall_panel(mb, mats, x, -d * 0.5 + 0.15, z0, w / (cols - 1) * 0.94,
                   h * 0.86)
    beam_frame(mb, mats, w, d, z0 + h)
    eave_band(mb, mats, w, d, z0 + h + 0.3, 1.0)
    # lower eave
    roof(mb, mats, w + 0.6, d + 0.6, 1.3, over=1.7, rib=1.4, ribs=False,
         z0=z0 + h + 1.45)
    # upper storey
    z1 = z0 + h + 1.5
    w2, d2 = w * 0.78, d * 0.72
    for i in range(cols - 1):
        x = -w2 * 0.5 + w2 * i / (cols - 2)
        for y in (-d2 * 0.5, d2 * 0.5):
            column(mb, mats, x, y, z1, h * 0.52, r=0.3)
    wall_panel(mb, mats, 0, d2 * 0.5, z1, w2, h * 0.5)
    wall_panel(mb, mats, 0, -d2 * 0.5, z1, w2, h * 0.5)
    beam_frame(mb, mats, w2, d2, z1 + h * 0.52)
    eave_band(mb, mats, w2, d2, z1 + h * 0.52 + 0.26, 0.8)
    roof(mb, mats, w2, d2, 4.6, over=1.5, rib=1.1,
         z0=z1 + h * 0.52 + 1.21)
    return mb


def t_wing(mats, w=14.0, d=7.0, h=4.8):
    """厢房 - long side hall with gable roof."""
    mb = MB()
    platform(mb, mats, w + 1.4, d + 1.4, 0.55)
    z0 = 0.7
    cols = 5
    for i in range(cols):
        x = -w * 0.5 + w * i / (cols - 1)
        for y in (-d * 0.5, d * 0.5):
            column(mb, mats, x, y, z0, h, r=0.27)
    wall_panel(mb, mats, 0, d * 0.5, z0, w, h * 0.9)
    for i in range(cols - 1):
        x = -w * 0.5 + w * (i + 0.5) / (cols - 1)
        wall_panel(mb, mats, x, -d * 0.5, z0, w / (cols - 1) * 0.9, h * 0.82)
    beam_frame(mb, mats, w, d, z0 + h)
    eave_band(mb, mats, w, d, z0 + h + 0.22, 0.7)
    roof(mb, mats, w, d, 3.0, over=1.1, z0=z0 + h + 1.07)
    return mb


def t_tower(mats, w=10.0, h=4.2, storeys=3):
    """楼阁 - multi-storey pavilion tower."""
    mb = MB()
    platform(mb, mats, w + 2.4, w + 2.4, 1.1)
    z = 1.25
    for s in range(storeys):
        shr = 1.0 - 0.11 * s
        ww = w * shr
        for (x, y) in ((-ww * 0.5, -ww * 0.5), (ww * 0.5, -ww * 0.5),
                       (-ww * 0.5, ww * 0.5), (ww * 0.5, ww * 0.5)):
            column(mb, mats, x, y, z, h, r=0.32)
        for (x, y) in ((-ww * 0.5, 0.0), (ww * 0.5, 0.0),
                       (0.0, -ww * 0.5), (0.0, ww * 0.5)):
            column(mb, mats, x, y, z, h, r=0.26)
        wall_panel(mb, mats, 0, 0, z, ww * 0.62, h * 0.78)
        # balcony
        mb.box((0, 0, z + h * 0.16), (ww + 1.5, ww + 1.5, 0.22), mats["timber"])
        for sx in (-1, 1):
            railing(mb, mats, sx * (ww * 0.5 + 0.7), -ww * 0.5 - 0.7,
                    sx * (ww * 0.5 + 0.7), ww * 0.5 + 0.7, z + h * 0.16)
            railing(mb, mats, -ww * 0.5 - 0.7, sx * (ww * 0.5 + 0.7),
                    ww * 0.5 + 0.7, sx * (ww * 0.5 + 0.7), z + h * 0.16)
        eave_band(mb, mats, ww, ww, z + h + 0.18, 0.65)
        if s < storeys - 1:
            roof(mb, mats, ww, ww, 1.0, over=1.5, rib=1.3, ribs=False,
                 z0=z + h + 0.98)
        z += h + 1.0
    roof(mb, mats, w * 0.62, w * 0.62, 4.4, over=1.4, rib=1.0, z0=z - 0.1)
    return mb


def t_pavilion(mats, w=6.0, h=4.4):
    """凉亭 - open four-column pavilion with pyramidal roof."""
    mb = MB()
    platform(mb, mats, w + 1.8, w + 1.8, 0.5)
    z0 = 0.62
    for (x, y) in ((-w * 0.5, -w * 0.5), (w * 0.5, -w * 0.5),
                   (-w * 0.5, w * 0.5), (w * 0.5, w * 0.5)):
        column(mb, mats, x, y, z0, h, r=0.26)
    beam_frame(mb, mats, w, w, z0 + h, 0.4)
    for s in (-1, 1):
        railing(mb, mats, -w * 0.5, s * w * 0.5, w * 0.5, s * w * 0.5, z0 + 0.05)
    pyramid_roof(mb, mats, w, 3.4, over=1.2, z0=z0 + h + 0.42)
    return mb


def t_gate_tower(mats, w=13.0, d=9.0, h=9.0):
    """门楼 - fortified gate with an upper hall."""
    mb = MB()
    mb.box((0, 0, h * 0.5), (w, d, h), mats["stone_dark"])
    mb.box((0, 0, h * 0.5), (w * 0.96, d * 0.9, h), mats["stone"])
    # gate opening
    mb.box((0, -d * 0.5 - 0.1, 3.0), (w * 0.22, 1.2, 6.0), mats["void"])
    for s in (-1, 1):
        mb.box((s * w * 0.5, 0, h * 0.5), (1.2, d * 1.02, h), mats["stone_dark"])
    mb.box((0, 0, h + 0.25), (w * 1.04, d * 1.04, 0.5), mats["stone_dark"])
    z0 = h + 0.5
    ww, dd, hh = w * 0.72, d * 0.5, 4.2
    for i in range(4):
        x = -ww * 0.5 + ww * i / 3
        for y in (-dd * 0.5, dd * 0.5):
            column(mb, mats, x, y, z0, hh, r=0.28)
    wall_panel(mb, mats, 0, 0, z0, ww * 0.5, hh * 0.7)
    beam_frame(mb, mats, ww, dd, z0 + hh)
    eave_band(mb, mats, ww, dd, z0 + hh + 0.2, 0.7)
    roof(mb, mats, ww, dd, 3.4, over=1.3, z0=z0 + hh + 1.05)
    return mb


def t_terrace_hall(mats, w=26.0, d=18.0, h=8.0):
    """高台殿 - hall on a tall three-tier terrace."""
    mb = MB()
    for i, (ww, dd, hh) in enumerate(((w + 7, d + 7, 1.6),
                                      (w + 5, d + 5, 1.5),
                                      (w + 3, d + 3, 1.4))):
        mb.box((0, 0, sum(x[2] for x in ((w + 7, d + 7, 1.6), (w + 5, d + 5, 1.5))[:i]) + hh * 0.5),
               (ww, dd, hh), mats["stone"])
        mb.box((0, 0, sum(x[2] for x in ((w + 7, d + 7, 1.6), (w + 5, d + 5, 1.5))[:i]) + hh),
               (ww * 0.99, dd * 0.99, 0.18), mats["stone_dark"])
    z0 = 4.6
    for i in range(8):
        x = -w * 0.5 + w * i / 7
        for y in (-d * 0.5, d * 0.5):
            column(mb, mats, x, y, z0, h, r=0.4)
        if i % 2 == 0:
            for y in (-d * 0.5, d * 0.5):
                dougong(mb, mats, x, y, z0 + h + 0.1, 0.9)
    wall_panel(mb, mats, 0, d * 0.5 - 0.2, z0, w, h * 0.92)
    for i in range(7):
        x = -w * 0.5 + w * (i + 0.5) / 7
        wall_panel(mb, mats, x, -d * 0.5 + 0.2, z0, w / 7 * 0.9, h * 0.85)
    beam_frame(mb, mats, w, d, z0 + h)
    eave_band(mb, mats, w, d, z0 + h + 0.28, 0.95)
    roof(mb, mats, w, d, 5.4, over=1.7, rib=1.1, z0=z0 + h + 1.38)
    # front ramp + flanking stairs
    mb.box((0, -d * 0.5 - 4.6, 2.2), (7.0, 8.0, 0.5), mats["stone_dark"],
           taper=1.0)
    return mb


def t_cross_hall(mats, w=20.0, d=13.0, h=6.4):
    """十字脊抱厦殿 - main hall with projecting cross-ridge porch."""
    mb = MB()
    platform(mb, mats, w + 3.0, d + 6.0, 1.4)
    z0 = 1.55
    for i in range(6):
        x = -w * 0.5 + w * i / 5
        for y in (-d * 0.5, d * 0.5):
            column(mb, mats, x, y, z0, h, r=0.36)
    wall_panel(mb, mats, 0, d * 0.5, z0, w, h * 0.92)
    for s in (-1, 1):
        wall_panel(mb, mats, s * w * 0.5, 0, z0, d, h * 0.88)
    beam_frame(mb, mats, w, d, z0 + h)
    eave_band(mb, mats, w, d, z0 + h + 0.26, 0.9)
    roof(mb, mats, w, d, 4.4, over=1.4, z0=z0 + h + 1.3)
    # porch projecting south
    pw, pd = w * 0.62, 5.4
    py = -d * 0.5 - pd * 0.5 + 0.4
    pz = z0
    for x in (-pw * 0.5, 0.0, pw * 0.5):
        column(mb, mats, x, py - pd * 0.5, pz, h * 0.72, r=0.3)
    beam_frame(mb, mats, pw, pd, pz + h * 0.72)
    eave_band(mb, mats, pw, pd, pz + h * 0.72 + 0.2, 0.7)
    roof(mb, mats, pw, pd, 2.9, over=1.2, ridge=True,
         z0=pz + h * 0.72 + 0.95)
    # cross ridge block
    mb.box((0, py, h * 0.9 + 2.9), (0.9, 1.0, 1.1), mats["tile_dark"], taper=0.4)
    return mb


def t_bell_tower(mats, w=9.0, h=4.0):
    """钟鼓楼 - square two-storey bell/drum tower."""
    mb = MB()
    mb.box((0, 0, 3.0), (w + 3.0, w + 3.0, 6.0), mats["stone_dark"])
    mb.box((0, 0, 6.02), (w + 3.4, w + 3.4, 0.4), mats["stone"])
    mb.box((0, -w * 0.5 - 1.4, 2.2), (3.2, 1.0, 4.4), mats["void"])
    z0 = 6.2
    for (x, y) in ((-w * 0.5, -w * 0.5), (w * 0.5, -w * 0.5),
                   (-w * 0.5, w * 0.5), (w * 0.5, w * 0.5)):
        column(mb, mats, x, y, z0, h, r=0.34)
    wall_panel(mb, mats, 0, 0, z0, w * 0.66, h * 0.8)
    beam_frame(mb, mats, w, w, z0 + h)
    eave_band(mb, mats, w, w, z0 + h + 0.2, 0.72)
    roof(mb, mats, w, w, 3.6, over=1.3, z0=z0 + h + 1.1)
    return mb


def t_corridor_court(mats, w=22.0, d=18.0):
    """连廊院 - courtyard enclosed by four wings and connecting corridors."""
    mb = MB()
    # main hall to the north
    emit(mb, t_main_hall(mats, w=w * 0.6, d=d * 0.42, h=6.0),
         _M(0, d * 0.30, 0, math.pi))
    # side wings
    for s in (-1, 1):
        emit(mb, t_wing(mats, w=d * 0.62, d=6.4, h=4.4),
             _M(s * w * 0.42, -d * 0.02, 0, s * math.pi * 0.5))
    # gate hall south
    emit(mb, t_gate_hall(mats, w=w * 0.34, d=6.4, h=4.8),
         _M(0, -d * 0.42, 0, 0.0))
    # connecting corridors
    z0 = 0.55
    for s in (-1, 1):
        x = s * w * 0.30
        for k in range(5):
            y = -d * 0.34 + k * d * 0.16
            column(mb, mats, x, y, z0, 3.0, r=0.2)
            column(mb, mats, x + s * 2.4, y, z0, 3.0, r=0.2)
    for s in (-1, 1):
        railing(mb, mats, s * w * 0.30, -d * 0.36, s * w * 0.30, d * 0.28, z0)
    # courtyard paving
    mb.box((0, -d * 0.03, 0.12), (w * 0.56, d * 0.5, 0.26), mats["stone_dark"])
    mb.box((0, -d * 0.03, 0.24), (w * 0.40, d * 0.36, 0.08), mats["stone"])
    return mb


TEMPLATES = {
    "gate_hall": t_gate_hall,
    "main_hall": t_main_hall,
    "wing": t_wing,
    "tower": t_tower,
    "pavilion": t_pavilion,
    "gate_tower": t_gate_tower,
    "terrace_hall": t_terrace_hall,
    "cross_hall": t_cross_hall,
    "bell_tower": t_bell_tower,
    "corridor_court": t_corridor_court,
}
