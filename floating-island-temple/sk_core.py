"""Deterministic scene kernel: hash noise, mesh accumulator, materials."""

import math

import bpy
from mathutils import Euler, Matrix, Vector

TAU = math.pi * 2.0

CFG = {
    "seed": 20261026,
    "island_radius": 100.0,
    "island_ax": 120.0,
    "island_ay": 58.0,
    "cliff_depth": 96.0,
    "cloud_top": -18.0,
    "statue_height": 44.0,
    "statue_pos": (0.0, 40.0),
    "statue_yaw": math.radians(-25.0),
    "wall_radius": 84.0,
    "core_radius": 34.0,
    "statue_clear_radius": 28.0,
    "courtyard_count": 14,
}


# ---------------------------------------------------------------- noise ----
def _hash3(ix, iy, iz, seed):
    n = (int(ix) * 374761393 + int(iy) * 668265263 + int(iz) * 1442695041
         + int(seed) * 1013904223) & 0xFFFFFFFF
    n = (n ^ (n >> 13)) & 0xFFFFFFFF
    n = (n * 1274126177) & 0xFFFFFFFF
    n = (n ^ (n >> 16)) & 0xFFFFFFFF
    return n / 4294967295.0


def _fade(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def noise2(x, y, seed=0):
    ix, iy = math.floor(x), math.floor(y)
    u, v = _fade(x - ix), _fade(y - iy)
    a = _hash3(ix, iy, 0, seed)
    b = _hash3(ix + 1, iy, 0, seed)
    c = _hash3(ix, iy + 1, 0, seed)
    d = _hash3(ix + 1, iy + 1, 0, seed)
    return (a + (b - a) * u) * (1 - v) + (c + (d - c) * u) * v


def noise3(x, y, z, seed=0):
    ix, iy, iz = math.floor(x), math.floor(y), math.floor(z)
    u, v, w = _fade(x - ix), _fade(y - iy), _fade(z - iz)

    def h(i, j, k):
        return _hash3(ix + i, iy + j, iz + k, seed)

    x00 = h(0, 0, 0) + (h(1, 0, 0) - h(0, 0, 0)) * u
    x10 = h(0, 1, 0) + (h(1, 1, 0) - h(0, 1, 0)) * u
    x01 = h(0, 0, 1) + (h(1, 0, 1) - h(0, 0, 1)) * u
    x11 = h(0, 1, 1) + (h(1, 1, 1) - h(0, 1, 1)) * u
    y0 = x00 + (x10 - x00) * v
    y1 = x01 + (x11 - x01) * v
    return y0 + (y1 - y0) * w


def fbm2(x, y, octaves=4, seed=0, lac=2.03, gain=0.5):
    amp, freq, total, norm = 0.5, 1.0, 0.0, 0.0
    for i in range(octaves):
        total += amp * noise2(x * freq, y * freq, seed + i * 17)
        norm += amp
        amp *= gain
        freq *= lac
    return total / norm


def fbm3(x, y, z, octaves=4, seed=0, lac=2.03, gain=0.5):
    amp, freq, total, norm = 0.5, 1.0, 0.0, 0.0
    for i in range(octaves):
        total += amp * noise3(x * freq, y * freq, z * freq, seed + i * 17)
        norm += amp
        amp *= gain
        freq *= lac
    return total / norm


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def smoothstep(e0, e1, x):
    t = clamp((x - e0) / (e1 - e0)) if e1 != e0 else 0.0
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def rim_radius(theta, base=None, seed=None):
    r0 = CFG["island_radius"] if base is None else base
    sd = CFG["seed"] if seed is None else seed
    k = (1.0 + 0.085 * math.sin(3.0 * theta + 0.7)
         + 0.055 * math.sin(5.0 * theta + 2.1)
         + 0.035 * math.sin(8.0 * theta + 4.3)
         + 0.045 * (fbm2(math.cos(theta) * 2.2, math.sin(theta) * 2.2, 3, sd) - 0.5))
    return r0 * k


def terrain_z(x, y):
    """Height of the island top, normalised to the elliptical footprint."""
    rn = math.hypot(x / CFG["island_ax"], y / CFG["island_ay"])
    edge = smoothstep(0.74, 1.0, rn)
    h = (fbm2(x * 0.021, y * 0.021, 4, CFG["seed"] + 3) - 0.5) * 6.4
    h += (fbm2(x * 0.075, y * 0.075, 3, CFG["seed"] + 9) - 0.5) * 1.5
    return h * (1.0 - 0.5 * smoothstep(0.0, 1.0, rn)) - edge * 3.2


# ------------------------------------------------------------------ MB ----
class MB:
    """Vertex / face / material accumulator."""

    def __init__(self):
        self.verts = []
        self.faces = []
        self.mats = []
        self.smooth = []

    def add(self, verts, faces, mat, smooth=False):
        off = len(self.verts)
        self.verts.extend(verts)
        for f in faces:
            self.faces.append(tuple(i + off for i in f))
            self.mats.append(mat)
            self.smooth.append(smooth)

    def box(self, c, s, mat, rz=0.0, taper=1.0):
        hx, hy, hz = s[0] * 0.5, s[1] * 0.5, s[2] * 0.5
        t = taper
        pts = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
               (-hx * t, -hy * t, hz), (hx * t, -hy * t, hz),
               (hx * t, hy * t, hz), (-hx * t, hy * t, hz)]
        if rz:
            ca, sa = math.cos(rz), math.sin(rz)
            pts = [(x * ca - y * sa, x * sa + y * ca, z) for (x, y, z) in pts]
        self.add([(c[0] + x, c[1] + y, c[2] + z) for (x, y, z) in pts],
                 [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                  (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], mat)

    def quad(self, a, b, c, d, mat, smooth=False):
        self.add([a, b, c, d], [(0, 1, 2, 3)], mat, smooth)

    def cylinder(self, cx, cy, z0, r, h, mat, seg=16, r_top=None, caps=True):
        rt = r if r_top is None else r_top
        side, faces = [], []
        for i in range(seg):
            a = TAU * i / seg
            side.append((cx + math.cos(a) * r, cy + math.sin(a) * r, z0))
        for i in range(seg):
            a = TAU * i / seg
            side.append((cx + math.cos(a) * rt, cy + math.sin(a) * rt, z0 + h))
        for i in range(seg):
            j = (i + 1) % seg
            faces.append((i, j, seg + j, seg + i))
        self.add(side, faces, mat, smooth=True)
        if caps:
            for zz, rr, flip in ((z0, r, True), (z0 + h, rt, False)):
                pts = [(cx + math.cos(TAU * i / seg) * rr,
                        cy + math.sin(TAU * i / seg) * rr, zz) for i in range(seg)]
                f = list(range(seg))
                self.add(pts, [tuple(reversed(f)) if flip else tuple(f)], mat)

    def sphere(self, c, radii, mat, seg=18, rings=12, smooth=True):
        verts, faces = [], []
        rx, ry, rz = radii
        for j in range(rings + 1):
            phi = math.pi * j / rings
            for i in range(seg):
                th = TAU * i / seg
                verts.append((c[0] + rx * math.sin(phi) * math.cos(th),
                              c[1] + ry * math.sin(phi) * math.sin(th),
                              c[2] + rz * math.cos(phi)))
        for j in range(rings):
            for i in range(seg):
                a = j * seg + i
                b = j * seg + (i + 1) % seg
                cc = (j + 1) * seg + (i + 1) % seg
                d = (j + 1) * seg + i
                faces.append((a, b, cc, d))
        self.add(verts, faces, mat, smooth)

    def loft(self, rings, mat, closed=True, smooth=True, cap_bottom=False, cap_top=False):
        verts, faces = [], []
        n = len(rings[0])
        for ring in rings:
            verts.extend(ring)
        for j in range(len(rings) - 1):
            for i in range(n if closed else n - 1):
                a = j * n + i
                b = j * n + (i + 1) % n
                c = (j + 1) * n + (i + 1) % n
                d = (j + 1) * n + i
                faces.append((a, b, c, d))
        if cap_bottom:
            faces.append(tuple(reversed(range(n))))
        if cap_top:
            off = (len(rings) - 1) * n
            faces.append(tuple(off + i for i in range(n)))
        self.add(verts, faces, mat, smooth)

    def prism(self, poly, z0, z1, mat, smooth=False):
        n = len(poly)
        verts = [(x, y, z0) for (x, y) in poly] + [(x, y, z1) for (x, y) in poly]
        faces = [tuple(reversed(range(n)))]
        for i in range(n):
            j = (i + 1) % n
            faces.append((i, j, n + j, n + i))
        faces.append(tuple(n + i for i in range(n)))
        self.add(verts, faces, mat, smooth)

    def transform(self, matrix):
        self.verts = [tuple(matrix @ Vector(v)) for v in self.verts]


def build_mesh(name, mb, mats):
    me = bpy.data.meshes.new(name)
    me.from_pydata(mb.verts, [], mb.faces)
    me.validate(verbose=False)
    for m in mats:
        me.materials.append(m)
    for i, p in enumerate(me.polygons):
        if i < len(mb.mats):
            p.material_index = mb.mats[i]
            p.use_smooth = mb.smooth[i]
    me.update()
    return me


def build_object(name, mb, mats, coll, loc=(0, 0, 0), rot=(0, 0, 0)):
    me = build_mesh(name, mb, mats)
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.rotation_euler = Euler(rot, "XYZ")
    coll.objects.link(ob)
    return ob


# ------------------------------------------------------------ materials ----
def _out(nt):
    for n in nt.nodes:
        if n.type == "OUTPUT_MATERIAL":
            return n
    return nt.nodes.new("ShaderNodeOutputMaterial")


def mat_principled(name, color, rough=0.6, metallic=0.0, spec=0.4):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    for key in ("Specular IOR Level", "Specular"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = spec
            break
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    out.location = (300, 0)
    return m


def mat_weathered(name, color, rough=0.7, scale=1.0, bump=0.22, detail=8.0,
                  tint=None, rough_var=0.18):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (620, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (340, 0)
    bsdf.inputs["Roughness"].default_value = rough
    tex = nt.nodes.new("ShaderNodeTexCoord")
    tex.location = (-820, 0)
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.location = (-620, 120)
    n1.inputs["Scale"].default_value = 3.4 * scale
    n1.inputs["Detail"].default_value = detail
    n1.inputs["Roughness"].default_value = 0.62
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.location = (-620, -180)
    n2.inputs["Scale"].default_value = 17.0 * scale
    n2.inputs["Detail"].default_value = 6.0
    n2.inputs["Roughness"].default_value = 0.55
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-380, 120)
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1)
    ramp.color_ramp.elements[1].position = 0.78
    ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1)
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.location = (-150, 120)
    mix.blend_type = "MIX"
    c2 = tint or tuple(min(1.0, c * 0.55) for c in color)
    mix.inputs["Color1"].default_value = (*color, 1.0)
    mix.inputs["Color2"].default_value = (*c2, 1.0)
    nt.links.new(tex.outputs["Object"], n1.inputs["Vector"])
    nt.links.new(tex.outputs["Object"], n2.inputs["Vector"])
    nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], mix.inputs["Fac"])
    nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.location = (-150, -180)
    mr.inputs["To Min"].default_value = max(0.2, rough - rough_var)
    mr.inputs["To Max"].default_value = min(1.0, rough + rough_var)
    nt.links.new(n2.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])
    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.location = (120, -230)
    bmp.inputs["Strength"].default_value = bump
    bmp.inputs["Distance"].default_value = 0.35
    nt.links.new(n2.outputs["Fac"], bmp.inputs["Height"])
    nt.links.new(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


def palette():
    """Low-saturation palette: blue-grey tile, near-black timber, dark red
    columns, grey stone, dark weathered island rock, pale limestone."""
    p = {}
    L = lambda h: ((h >> 16 & 255) / 255.0, (h >> 8 & 255) / 255.0,
                   (h & 255) / 255.0)

    def srgb_lin(c):
        return tuple((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
                     for v in c)

    p["tile"] = mat_weathered("M_Tile", srgb_lin(L(0x515C60)), 0.58, 2.2, 0.14, 7.0)
    p["tile_dark"] = mat_weathered("M_TileDark", srgb_lin(L(0x3C464A)), 0.62, 2.0, 0.12)
    p["timber"] = mat_weathered("M_Timber", srgb_lin(L(0x2E2B29)), 0.74, 1.6, 0.16)
    p["beam"] = mat_principled("M_Beam", srgb_lin(L(0x232120)), 0.7, 0.0, 0.3)
    p["column"] = mat_weathered("M_Column", srgb_lin(L(0x6A322A)), 0.55, 2.6, 0.09)
    p["stone"] = mat_weathered("M_Stone", srgb_lin(L(0x6E6C66)), 0.78, 1.3, 0.3, 9.0)
    p["stone_dark"] = mat_weathered("M_StoneDark", srgb_lin(L(0x54544F)), 0.8, 1.5, 0.3)
    p["rock"] = mat_weathered("M_Rock", srgb_lin(L(0x3E4A4E)), 0.84, 0.55, 0.42, 10.0,
                              tint=srgb_lin(L(0x2C3639)), rough_var=0.12)
    p["rock_wet"] = mat_weathered("M_RockWet", srgb_lin(L(0x2B3438)), 0.62, 0.9, 0.5)
    p["limestone"] = mat_weathered("M_Limestone", srgb_lin(L(0xD2CBB8)), 0.70, 1.1,
                                   0.30, 9.0, tint=srgb_lin(L(0xA9A392)), rough_var=0.13)
    p["limestone_dark"] = mat_weathered("M_LimestoneDark", srgb_lin(L(0xA8A190)), 0.74,
                                        1.4, 0.36)
    p["ground"] = mat_weathered("M_Ground", srgb_lin(L(0x4E5453)), 0.86, 0.7, 0.36)
    p["gold"] = mat_principled("M_Gold", srgb_lin(L(0x8A7648)), 0.42, 0.65)
    p["void"] = mat_principled("M_Void", (0.004, 0.005, 0.006), 0.9)
    return p


# ---------------------------------------------------------- collections ----
def new_collection(name, parent=None):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if c.name not in parent.children:
        parent.children.link(c)
    return c


MATS = [
    "tile", "tile_dark", "timber", "beam", "column", "stone",
    "stone_dark", "rock", "rock_wet", "limestone", "limestone_dark",
    "ground", "gold", "void",
]
MI = {k: i for i, k in enumerate(MATS)}


def make_mats():
    p = palette()
    d = {k: i for i, k in enumerate(MATS)}
    d["list"] = [p[k] for k in MATS]
    d["p"] = p
    return d
