"""Assembly driver for the floating-island temple city.

Usage (headless):
    blender -b --factory-startup --python build_scene.py -- --stage all --cam main --preview

Stages: all | island | statue | city | clouds
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy
from mathutils import Vector

import sk_core
from sk_core import CFG, MI, make_mats, new_collection
from sk_island import build_ground_detail, build_island
from sk_statue import build_statue
from sk_city import (build_bailey, build_core, build_courtyards,
                     build_statue_plaza, build_wall)
from sk_atmo import (add_lights, build_cameras, build_clouds, make_world,
                     setup_render)

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")

# composition: aim point is west of the island so the island sits frame-right
MAIN_TARGET = (-88.0, -22.0, 6.0)
MAIN_PITCH = 60.0
MAIN_DIST = 1985.0
MAIN_ROLL = 7.0


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)


def place_main_camera(cam):
    """Position main camera from aim point + pitch + distance, with a roll."""
    import math
    p = math.radians(MAIN_PITCH)
    fwd = Vector((0.0, math.cos(p), -math.sin(p)))
    cam.location = Vector(MAIN_TARGET) - fwd * MAIN_DIST
    d = Vector(MAIN_TARGET) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cam.rotation_euler.rotate_axis("Z", math.radians(MAIN_ROLL))
    return cam


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all")
    ap.add_argument("--cam", default="")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--samples", type=int, default=0)
    ap.add_argument("--pct", type=int, default=100)
    ap.add_argument("--out", default="")
    ap.add_argument("--save", default="")
    ap.add_argument("--sky", action="store_true")
    ap.add_argument("--noclouds", action="store_true")
    ap.add_argument("--norim", action="store_true")
    ap.add_argument("--res", default="")
    ap.add_argument("--look", default="")
    args = ap.parse_args(argv)

    t0 = time.time()
    reset()
    mats = make_mats()

    c_island = new_collection("ISLAND")
    c_statue = new_collection("STATUE")
    c_city = new_collection("CITY")
    c_cloud = new_collection("CLOUDS")
    c_light = new_collection("LIGHT")
    c_cam = new_collection("CAMERAS")

    stage = args.stage
    if stage in ("all", "island"):
        build_island(mats, c_island)
        build_ground_detail(mats, c_island, CFG["seed"])
    if stage in ("all", "statue"):
        build_statue(mats, c_statue, CFG["seed"])
    if stage in ("all", "city"):
        build_wall(mats, c_city, CFG["seed"])
        build_courtyards(mats, c_city, CFG["seed"])
        build_core(mats, c_city, CFG["seed"])
        build_statue_plaza(mats, c_city, CFG["seed"])
        build_bailey(mats, c_city, CFG["seed"])
    if stage in ("all", "clouds") and not args.noclouds:
        build_clouds(c_cloud)
        if args.norim:
            for ob in list(c_cloud.objects):
                if ob.name.startswith(("RimBank", "StatueBaseBank")):
                    c_cloud.objects.unlink(ob)
                    bpy.data.objects.remove(ob, do_unlink=True)

    make_world()
    add_lights(c_light)
    cams = build_cameras(c_cam)
    place_main_camera(cams["main"])

    sc = setup_render(preview=args.preview, samples=args.samples or None)
    if args.res:
        rx, ry = [int(v) for v in args.res.lower().split("x")]
        sc.render.resolution_x = rx
        sc.render.resolution_y = ry
    if args.preview:
        sc.render.resolution_percentage = args.pct
    if args.look:
        try:
            sc.view_settings.look = args.look
        except Exception:
            pass

    # report scene budget
    tris = 0
    objs = 0
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            objs += 1
            tris += len(ob.data.loop_triangles) or len(ob.data.polygons)
    print("BUILD_SECONDS %.1f" % (time.time() - t0))
    print("MESH_OBJECTS %d  FACES %d" % (objs, tris))
    print("MATERIALS %d" % len(bpy.data.materials))

    # framing diagnostics
    from bpy_extras.object_utils import world_to_camera_view
    cam = cams["main"] if not args.cam else cams.get(args.cam, cams["main"])
    sc.camera = cam
    bpy.context.view_layer.update()
    ax, ay = CFG["island_ax"], CFG["island_ay"]
    sx, sy = CFG["statue_pos"]
    for label, pt in (("island_center", (0, 0, 0)),
                      ("statue_top", (sx, sy, CFG["statue_height"])),
                      ("island_west", (-ax, 0, 0)),
                      ("island_east", (ax, 0, 0)),
                      ("island_north", (0, ay, 0)),
                      ("island_south", (0, -ay, 0))):
        u, v, _ = world_to_camera_view(sc, cam, Vector(pt))
        print("FRAME %-14s u=%.3f v=%.3f" % (label, u, v))
    print("CAM %s loc=%s rot=%s lens=%.1f" %
          (cam.name, tuple(round(x, 1) for x in cam.location),
           tuple(round(x, 3) for x in cam.rotation_euler), cam.data.lens))

    if args.save:
        path = os.path.join(ROOT, args.save)
        bpy.ops.wm.save_as_mainfile(filepath=path)
        print("SAVED %s" % path)

    if args.cam or args.out:
        os.makedirs(OUT, exist_ok=True)
        name = args.out or ("preview_%s" % cam.name)
        sc.render.filepath = os.path.join(OUT, name)
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        print("RENDER_SECONDS %.1f" % (time.time() - t1))
        print("RENDERED %s" % sc.render.filepath)
    print("DONE")


if __name__ == "__main__":
    main()
