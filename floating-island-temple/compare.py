"""Build side-by-side / overlay / difference sheets against a reference.

Usage:
    python compare.py <render.png> [--ref reference.png] [--out out/]
    python compare.py out/final_1920.png            # auto-detect ref

If no reference image is available, the script writes a self-check sheet
(render + luminance band analysis + framing overlay) instead of failing.
"""

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def srgb_to_lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def load_rgb(path, size=None):
    im = Image.open(path).convert("RGB")
    if size:
        im = im.resize(size, Image.LANCZOS)
    return im


def lum(a):
    return a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)


def label(draw, xy, text, size=22):
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", size)
    except Exception:
        font = ImageFont.load_default()
    draw.text(xy, text, fill=(240, 244, 250), font=font)


def side_by_side(ref, ren, path):
    w, h = ren.size
    sheet = Image.new("RGB", (w * 2 + 24, h + 56), (18, 20, 24))
    sheet.paste(ref, (0, 56))
    sheet.paste(ren, (w + 24, 56))
    d = ImageDraw.Draw(sheet)
    label(d, (12, 16), "REFERENCE")
    label(d, (w + 36, 16), "RENDER")
    sheet.save(path)
    return path


def overlay(ref, ren, path, alpha=0.5):
    a = np.asarray(ref, dtype=np.float32)
    b = np.asarray(ren, dtype=np.float32)
    mix = (a * (1.0 - alpha) + b * alpha).clip(0, 255).astype(np.uint8)
    Image.fromarray(mix).save(path)
    return path


def difference(ref, ren, path, gain=3.0):
    a = lum(np.asarray(ref, dtype=np.float32) / 255.0)
    b = lum(np.asarray(ren, dtype=np.float32) / 255.0)
    d = np.abs(a - b) * gain
    d = (d.clip(0, 1) * 255).astype(np.uint8)
    # colour-map: blue = render brighter, red = reference brighter
    signed = (b - a) * gain
    rgb = np.zeros((*signed.shape, 3), dtype=np.uint8)
    rgb[..., 0] = (np.clip(-signed, 0, 1) * 255).astype(np.uint8)
    rgb[..., 2] = (np.clip(signed, 0, 1) * 255).astype(np.uint8)
    rgb[..., 1] = d // 3
    Image.fromarray(rgb).save(path)
    return path, float(np.mean(np.abs(a - b)))


def self_sheet(ren, path):
    """No reference: annotate the render with framing guides + band stats."""
    w, h = ren.size
    a = np.asarray(ren, dtype=np.float32) / 255.0
    L = lum(a)
    sheet = Image.new("RGB", (w, h + 150), (18, 20, 24))
    sheet.paste(ren, (0, 0))
    d = ImageDraw.Draw(sheet)
    for i in range(1, 3):
        d.line([(w * i / 3, 0), (w * i / 3, h)], fill=(255, 120, 90, 90), width=2)
        d.line([(0, h * i / 3), (w, h * i / 3)], fill=(255, 120, 90, 90), width=2)
    left = L[:, : w // 2].mean()
    right = L[:, w // 2:].mean()
    bright_l = (L[:, : w // 2] > 0.62).mean()
    bright_r = (L[:, w // 2:] > 0.62).mean()
    lines = [
        "mean %.3f   left %.3f   right %.3f" % (L.mean(), left, right),
        "bright cloud  left %.1f%%   right %.1f%%" % (bright_l * 100, bright_r * 100),
        "dark structure %.1f%%" % ((L < 0.25).mean() * 100),
        "row bands: " + " ".join(
            "%.2f" % L[int(i * h / 8):int((i + 1) * h / 8)].mean() for i in range(8)),
    ]
    for i, t in enumerate(lines):
        label(d, (14, h + 14 + i * 32), t, 22)
    sheet.save(path)
    return path, float(L.mean())


def find_reference(base):
    for name in ("reference.png", "reference.jpg", "ref.png", "ref.jpg",
                 "main_reference.png", "main_reference.jpg"):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("render")
    ap.add_argument("--ref", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--gain", type=float, default=3.0)
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = args.out or os.path.join(here, "out")
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(args.render))[0]

    ren = load_rgb(args.render)
    ref_path = args.ref or find_reference(here) or find_reference(
        os.path.dirname(os.path.abspath(args.render)))

    if ref_path:
        ref = load_rgb(ref_path, ren.size)
        p1 = side_by_side(ref, ren, os.path.join(out_dir, "%s_sbs.png" % stem))
        p2 = overlay(ref, ren, os.path.join(out_dir, "%s_overlay.png" % stem))
        p3, mad = difference(ref, ren, os.path.join(out_dir, "%s_diff.png" % stem),
                             args.gain)
        print("REF %s" % ref_path)
        print("SBS %s" % p1)
        print("OVERLAY %s" % p2)
        print("DIFF %s  mean_abs_diff %.4f" % (p3, mad))
    else:
        p, m = self_sheet(ren, os.path.join(out_dir, "%s_selfcheck.png" % stem))
        print("NO_REFERENCE_FOUND")
        print("SELFCHECK %s  mean_luma %.4f" % (p, m))


if __name__ == "__main__":
    main()
