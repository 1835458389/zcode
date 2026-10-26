"""Calibrate the main camera to the reference framing.

Targets (screen fractions, u right / v up):
  island width  ~0.44      island centre v ~0.50
  island west edge ~0.50   east edge < 0.94
  north edge < 0.80        south edge > 0.14
"""

import itertools
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

import build_scene as BS
from sk_atmo import build_cameras
from sk_core import CFG, make_mats, new_collection
from sk_island import build_island

bpy.ops.wm.read_factory_settings(use_empty=True)
mats = make_mats()
c_island = new_collection("ISLAND")
c_cam = new_collection("CAMERAS")
build_island(mats, c_island)
cams = build_cameras(c_cam)
cam = cams["main"]
sc = bpy.context.scene
sc.camera = cam
sc.render.resolution_x = 1920
sc.render.resolution_y = 1080

ax, ay = CFG["island_ax"], CFG["island_ay"]
ZN = 4.0
pts = {
    "w": (0.0, -0.0, 0.0),  # placeholder replaced below
}
PROBE = {
    "west": (-ax, 0.0, 0.0),
    "east": (ax, 0.0, 0.0),
    "north": (0.0, ay, 0.0),
    "south": (0.0, -ay, 0.0),
    "centre": (0.0, 0.0, 0.0),
    "sculpt": (0.0, CFG["statue_pos"][1], CFG["statue_height"]),
}


def measure(target, pitch, dist, roll):
    p = math.radians(pitch)
    fwd = Vector((0.0, math.cos(p), -math.sin(p)))
    cam.location = Vector(target) - fwd * dist
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.rotation_euler.rotate_axis("Z", math.radians(roll))
    bpy.context.view_layer.update()
    out = {}
    for k, pt in PROBE.items():
        u, v, _ = world_to_camera_view(sc, cam, Vector(pt))
        out[k] = (u, v)
    return out


def score(m):
    w = m["east"][0] - m["west"][0]
    h = m["north"][1] - m["south"][1]
    cu = (m["east"][0] + m["west"][0]) * 0.5
    cv = (m["north"][1] + m["south"][1]) * 0.5
    s = 0.0
    s += 6.0 * (w - 0.44) ** 2
    s += 4.0 * (m["west"][0] - 0.50) ** 2
    s += 3.0 * (cv - 0.50) ** 2
    s += 2.0 * (cu - 0.70) ** 2
    if m["east"][0] > 0.95:
        s += 40.0 * (m["east"][0] - 0.95) ** 2
    if m["north"][1] > 0.82:
        s += 40.0 * (m["north"][1] - 0.82) ** 2
    if m["south"][1] < 0.12:
        s += 40.0 * (0.12 - m["south"][1]) ** 2
    return s, w, h, cu, cv


best = None
for ty in (-24.0, -16.0, -8.0, 0.0, 8.0):
    for tx in (-80.0, -64.0, -48.0, -32.0):
        for dist in (1150.0, 1250.0, 1350.0, 1450.0):
            for pitch in (58.0, 62.0, 66.0, 70.0):
                m = measure((tx, ty, 6.0), pitch, dist, 4.0)
                s, w, h, cu, cv = score(m)
                if best is None or s < best[0]:
                    best = (s, tx, ty, dist, pitch, m, w, h, cu, cv)

s, tx, ty, dist, pitch, m, w, h, cu, cv = best
print("BEST score=%.4f target=(%.1f,%.1f) dist=%.0f pitch=%.0f" % (s, tx, ty, dist, pitch))
print("  width=%.3f height=%.3f centre=(%.3f,%.3f)" % (w, h, cu, cv))
for k, (u, v) in m.items():
    print("  %-7s u=%.3f v=%.3f" % (k, u, v))

# refine around the best
best2 = None
for ty in [ty + d for d in (-6, -3, 0, 3, 6)]:
    for tx in [tx + d for d in (-8, -4, 0, 4, 8)]:
        for dist in [dist + d for d in (-70, -35, 0, 35, 70)]:
            for pitch in [pitch + d for d in (-2, -1, 0, 1, 2)]:
                for roll in (3.0, 5.0, 7.0):
                    m2 = measure((tx, ty, 6.0), pitch, dist, roll)
                    s2, w2, h2, cu2, cv2 = score(m2)
                    if best2 is None or s2 < best2[0]:
                        best2 = (s2, tx, ty, dist, pitch, roll, m2, w2, h2, cu2, cv2)
s, tx, ty, dist, pitch, roll, m, w, h, cu, cv = best2
print("REFINED score=%.4f target=(%.2f,%.2f,6.0) dist=%.1f pitch=%.1f roll=%.1f"
      % (s, tx, ty, dist, pitch, roll))
print("  width=%.3f height=%.3f centre=(%.3f,%.3f)" % (w, h, cu, cv))
for k, (u, v) in m.items():
    print("  %-7s u=%.3f v=%.3f" % (k, u, v))
print("PY %r" % ({"target": (round(tx, 2), round(ty, 2), 6.0),
                   "dist": round(dist, 1), "pitch": round(pitch, 1),
                   "roll": round(roll, 1)},))
