"""Verify composition constraints numerically against the main camera.

Reports per-object screen bounding boxes, island ellipse orientation, city
density distribution and material sanity.  No rendering.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

import build_scene as BS
from sk_atmo import (add_lights, build_cameras, build_clouds, make_world,
                     setup_render)
from sk_city import (build_bailey, build_core, build_courtyards,
                     build_statue_plaza, build_wall)
from sk_core import CFG, make_mats, new_collection
from sk_island import build_ground_detail, build_island
from sk_statue import build_statue


def screen_bbox(sc, cam, ob):
    us, vs = [], []
    dg = bpy.context.evaluated_depsgraph_get()
    obe = ob.evaluated_get(dg)
    me = obe.to_mesh()
    mw = obe.matrix_world
    for v in me.vertices:
        u, vv, _ = world_to_camera_view(sc, cam, mw @ v.co)
        us.append(u)
        vs.append(vv)
    obe.to_mesh_clear()
    if not us:
        return None
    return (min(us), max(us), min(vs), max(vs))


bpy.ops.wm.read_factory_settings(use_empty=True)
mats = make_mats()

c_island = new_collection("ISLAND")
c_statue = new_collection("STATUE")
c_city = new_collection("CITY")
c_cloud = new_collection("CLOUDS")
c_light = new_collection("LIGHT")
c_cam = new_collection("CAMERAS")

build_island(mats, c_island)
build_ground_detail(mats, c_island, CFG["seed"])
build_statue(mats, c_statue, CFG["seed"])
build_wall(mats, c_city, CFG["seed"])
build_courtyards(mats, c_city, CFG["seed"])
build_core(mats, c_city, CFG["seed"])
build_statue_plaza(mats, c_city, CFG["seed"])
build_bailey(mats, c_city, CFG["seed"])
build_clouds(c_cloud)
make_world()
add_lights(c_light)
cams = build_cameras(c_cam)
BS.place_main_camera(cams["main"])

sc = bpy.context.scene
sc.render.resolution_x = 1920
sc.render.resolution_y = 1080
sc.camera = cams["main"]
bpy.context.view_layer.update()

print("=" * 68)
print("SCENE BUDGET")
tot_faces = tot_objects = 0
for ob in bpy.data.objects:
    if ob.type == "MESH":
        tot_objects += 1
        tot_faces += len(ob.data.polygons)
print("  mesh objects %d   faces %d   materials %d"
      % (tot_objects, tot_faces, len(bpy.data.materials)))

print("=" * 68)
print("MAIN CAMERA FRAMING  (u right, v up, 0..1)")
rows = []
for ob in bpy.data.objects:
    if ob.type != "MESH":
        continue
    bb = screen_bbox(sc, cams["main"], ob)
    if bb:
        rows.append((ob.name, bb, len(ob.data.polygons)))
rows.sort(key=lambda r: -r[2])
for name, (u0, u1, v0, v1), nf in rows:
    print("  %-18s u %6.3f..%6.3f  v %6.3f..%6.3f  faces %d"
          % (name, u0, u1, v0, v1, nf))

print("=" * 68)
print("CONSTRAINT CHECKS")
isl = next(r for r in rows if r[0] == "Island")[1]
w = isl[1] - isl[0]
h = isl[3] - isl[2]
px_w = w * sc.render.resolution_x
px_h = h * sc.render.resolution_y
print("  island screen w %.3f  h %.3f  (%.0f x %.0f px, ratio %.2f:1) -> %s"
      % (w, h, px_w, px_h, px_w / max(px_h, 1e-6),
         "HORIZONTAL (ok)" if px_w > px_h * 1.25 else "NOT horizontal"))
print("  island centre u %.3f -> %s"
      % ((isl[0] + isl[1]) / 2,
         "right side (ok)" if (isl[0] + isl[1]) / 2 > 0.6 else "not right"))

st = next(r for r in rows if r[0] == "Statue")[1]
print("  statue u %.3f..%.3f  v %.3f..%.3f  height %.3f of frame"
      % (st[0], st[1], st[2], st[3], st[3] - st[2]))
print("  statue inside frame: %s"
      % ("ok" if st[0] > 0.0 and st[1] < 1.0 and st[2] > 0.0 and st[3] < 1.0
         else "CLIPPED"))

print("  island left edge %.3f -> left %.0f%% of frame free for cloud"
      % (isl[0], isl[0] * 100))

# city mass concentrated in the lower half of the island footprint
city_objs = [ob for ob in bpy.data.objects if ob.type == "MESH"
             and ob.name not in ("Island", "Statue", "GroundRocks")]
low = 0.0
tot = 0.0
for ob in city_objs:
    for v in ob.data.vertices:
        p = ob.matrix_world @ v.co
        tot += 1.0
        if p.y < 10.0:
            low += 1.0
print("  city vertices south of y=10: %.1f%%" % (100.0 * low / max(tot, 1.0)))

# footprint containment of the statue
sx, sy = CFG["statue_pos"]
ax, ay = CFG["island_ax"], CFG["island_ay"]
rn = ((sx / ax) ** 2 + (sy / ay) ** 2) ** 0.5
print("  statue normalised radius %.3f (must be < 1.0)" % rn)

print("  material check: %d materials" % len(bpy.data.materials))
for m in bpy.data.materials:
    if m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                inp = n.inputs["Base Color"]
                if inp.is_linked:
                    continue
                c = inp.default_value
                if c[0] > 0.82 and c[1] > 0.82 and c[2] > 0.82:
                    print("    WARNING very white base colour: %s" % m.name)
print("=" * 68)
print("VERIFY_DONE")
