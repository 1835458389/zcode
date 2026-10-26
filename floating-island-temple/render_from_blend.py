"""Render a camera from an already-built .blend.

    blender -b scene.blend --python render_from_blend.py -- \
        --cam CAM_Main --res 1920x1080 --samples 40 --out out/final_1920.png
"""

import argparse
import os
import sys
import time

import bpy

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam", default="CAM_Main")
    ap.add_argument("--res", default="1920x1080")
    ap.add_argument("--samples", type=int, default=40)
    ap.add_argument("--out", default="out/final.png")
    ap.add_argument("--steps", type=float, default=4.0)
    ap.add_argument("--maxsteps", type=int, default=320)
    ap.add_argument("--noise", action="store_true")
    args = ap.parse_args(argv)

    sc = bpy.context.scene
    cam = bpy.data.objects.get(args.cam)
    if cam is None:
        raise SystemExit("camera not found: %s" % args.cam)
    sc.camera = cam

    rx, ry = [int(v) for v in args.res.lower().split("x")]
    sc.render.resolution_x = rx
    sc.render.resolution_y = ry
    sc.render.resolution_percentage = 100

    sc.cycles.samples = args.samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.adaptive_min_samples = max(4, args.samples // 6)
    sc.cycles.volume_step_rate = args.steps
    sc.cycles.volume_max_steps = args.maxsteps
    sc.cycles.use_denoising = True
    for attr, val in (("denoiser", "OPENIMAGEDENOISE"),
                      ("denoising_input_passes", "RGB_ALBEDO_NORMAL"),
                      ("denoising_prefilter", "ACCURATE"),
                      ("denoising_quality", "HIGH"),
                      ("denoising_use_gpu", False)):
        try:
            setattr(sc.cycles, attr, val)
        except Exception:
            pass

    sc.render.image_settings.file_format = "PNG"
    if args.noise:
        sc.render.image_settings.color_depth = "16"
        try:
            sc.view_settings.view_transform = "Standard"
        except Exception:
            pass
    else:
        sc.render.image_settings.color_depth = "8"

    out = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sc.render.filepath = out

    print("RENDERING %s  %dx%d  samples=%d  cam=%s"
          % (out, rx, ry, args.samples, args.cam))
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print("RENDER_SECONDS %.1f" % (time.time() - t0))
    print("RENDERED %s" % out)


if __name__ == "__main__":
    main()
