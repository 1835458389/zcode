"""Atmosphere: volumetric cloud volumes, cool lighting, cameras, render setup."""

import math

import bpy
from mathutils import Vector

from sk_core import CFG


# ------------------------------------------------------------------- meshes --
def _cube_mesh(name, sx, sy, sz):
    hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5
    verts = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
             (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    return me


def _sphere_mesh(name, rx, ry, rz, seg=40, rings=28):
    verts, faces = [], []
    for j in range(rings + 1):
        phi = math.pi * j / rings
        for i in range(seg):
            th = math.pi * 2.0 * i / seg
            verts.append((rx * math.sin(phi) * math.cos(th),
                          ry * math.sin(phi) * math.sin(th),
                          rz * math.cos(phi)))
    for j in range(rings):
        for i in range(seg):
            a = j * seg + i
            b = j * seg + (i + 1) % seg
            c = (j + 1) * seg + (i + 1) % seg
            d = (j + 1) * seg + i
            faces.append((a, b, c, d))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    return me


# ---------------------------------------------------------------- material --
def mat_cloud(name, density=0.055, top_z=0.0, falloff=18.0, wobble=9.0,
              shape_thr=0.44, shape_wide=0.24, albedo=(0.93, 0.945, 0.965),
              aniso=0.32, seed_off=0.0, detail_scale=0.045):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.cycles.volume_sampling = "MULTIPLE_IMPORTANCE"
    nt = m.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (760, 0)
    vol = nt.nodes.new("ShaderNodeVolumePrincipled")
    vol.location = (480, 0)
    vol.inputs["Color"].default_value = (*albedo, 1.0)
    vol.inputs["Anisotropy"].default_value = aniso
    if "Absorption Color" in vol.inputs:
        vol.inputs["Absorption Color"].default_value = (0.55, 0.62, 0.70, 1.0)

    geo = nt.nodes.new("ShaderNodeNewGeometry")
    geo.location = (-1080, 0)

    # big billow masses
    n1 = nt.nodes.new("ShaderNodeTexNoise")
    n1.location = (-860, 180)
    n1.noise_dimensions = "3D"
    n1.inputs["Scale"].default_value = 0.0135
    n1.inputs["Detail"].default_value = 4.0
    n1.inputs["Roughness"].default_value = 0.62
    n1.inputs["Distortion"].default_value = 0.28
    if "W" in n1.inputs:
        n1.inputs["W"].default_value = seed_off

    # fine erosion
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.location = (-860, -180)
    n2.noise_dimensions = "3D"
    n2.inputs["Scale"].default_value = detail_scale
    n2.inputs["Detail"].default_value = 3.0
    n2.inputs["Roughness"].default_value = 0.52
    n2.inputs["Distortion"].default_value = 0.12

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-620, 180)
    ramp.color_ramp.interpolation = "EASE"
    ramp.color_ramp.elements[0].position = shape_thr
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = shape_thr + shape_wide
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)

    # vertical mask with noise-perturbed top
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-860, -440)
    nz = nt.nodes.new("ShaderNodeMath")
    nz.operation = "MULTIPLY"
    nz.location = (-620, -440)
    nz.inputs[1].default_value = wobble
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    add.location = (-440, -400)
    add.inputs[0].default_value = top_z

    sub = nt.nodes.new("ShaderNodeMath")
    sub.operation = "SUBTRACT"
    sub.location = (-350, -400)

    mask = nt.nodes.new("ShaderNodeMapRange")
    mask.location = (-250, -400)
    mask.interpolation_type = "SMOOTHSTEP"
    mask.inputs["From Min"].default_value = 0.0
    mask.inputs["From Max"].default_value = -falloff
    mask.inputs["To Min"].default_value = 0.0
    mask.inputs["To Max"].default_value = 1.0
    mask.clamp = True

    dens_shape = nt.nodes.new("ShaderNodeMath")
    dens_shape.operation = "POWER"
    dens_shape.location = (-380, 160)
    dens_shape.inputs[1].default_value = 1.35
    dens_shape.use_clamp = True

    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.location = (160, -120)
    mul.use_clamp = True

    mul2 = nt.nodes.new("ShaderNodeMath")
    mul2.operation = "MULTIPLY"
    mul2.location = (320, -60)
    mul2.inputs[1].default_value = density
    mul2.use_clamp = True

    nt.links.new(geo.outputs["Position"], n1.inputs["Vector"])
    nt.links.new(geo.outputs["Position"], n2.inputs["Vector"])
    nt.links.new(geo.outputs["Position"], sep.inputs["Vector"])
    nt.links.new(n1.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(n2.outputs["Fac"], nz.inputs[0])
    nt.links.new(sep.outputs["Z"], add.inputs[0])
    nt.links.new(nz.outputs[0], add.inputs[1])
    sub.inputs[1].default_value = top_z
    nt.links.new(add.outputs[0], sub.inputs[0])
    nt.links.new(sub.outputs[0], mask.inputs["Value"])
    nt.links.new(ramp.outputs["Color"], dens_shape.inputs[0])
    nt.links.new(dens_shape.outputs[0], mul.inputs[0])
    nt.links.new(mask.outputs["Result"], mul.inputs[1])
    nt.links.new(mul.outputs[0], mul2.inputs[0])
    nt.links.new(mul2.outputs[0], vol.inputs["Density"])
    nt.links.new(vol.outputs["Volume"], out.inputs["Volume"])
    return m


# ------------------------------------------------------------------- clouds --
def cloud_box(name, center, size, mat, coll):
    me = _cube_mesh(name, size[0], size[1], size[2])
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.location = center
    coll.objects.link(ob)
    return ob


def cloud_ellipsoid(name, center, radii, mat, coll, rot=(0, 0, 0)):
    me = _sphere_mesh(name, radii[0], radii[1], radii[2])
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    ob.location = center
    ob.rotation_euler = rot
    coll.objects.link(ob)
    return ob


def build_clouds(coll):
    # ---- continuous cloud sea under and west of the island ------------------
    m_sea = mat_cloud("M_CloudSea", density=0.115, top_z=-20.0, falloff=30.0,
                      wobble=15.0, shape_thr=0.44, shape_wide=0.16,
                      albedo=(0.95, 0.965, 1.0), aniso=0.45, seed_off=3.1)
    sea = cloud_box("CloudSea", (-420.0, 40.0, -120.0), (2600.0, 2600.0, 200.0),
                    m_sea, coll)
    sea.cycles.is_caustics_caster = False

    # ---- rim flow: banks climbing the north rim and burying the statue base --
    m_rim = mat_cloud("M_CloudRim", density=0.14, top_z=1.0, falloff=17.0,
                      wobble=9.0, shape_thr=0.42, shape_wide=0.18,
                      albedo=(0.94, 0.96, 1.0), aniso=0.40, seed_off=7.7)
    rim_specs = [
        ("RimBank_W", (-78.0, 44.0, -6.0), (62.0, 42.0, 22.0), 0.0),
        ("RimBank_NW", (-42.0, 74.0, -8.0), (44.0, 28.0, 24.0), 0.4),
        ("RimBank_N", (0.0, 86.0, -10.0), (50.0, 24.0, 26.0), 0.0),
        ("RimBank_NE", (44.0, 74.0, -8.0), (44.0, 28.0, 22.0), -0.4),
        ("RimBank_E", (76.0, 40.0, -6.0), (54.0, 40.0, 20.0), 0.7),
        ("RimBank_SW", (-84.0, -26.0, -8.0), (46.0, 38.0, 16.0), 0.2),
        ("RimBank_SE", (80.0, -30.0, -8.0), (44.0, 36.0, 15.0), -0.2),
    ]
    for nm, c, r, rz in rim_specs:
        ob = cloud_ellipsoid(nm, c, r, m_rim, coll, rot=(0, 0, rz))
        # per-object density so the bank height varies
        me = ob.data
        m = m_rim.copy()
        m.name = f"{nm}_M"
        me.materials[0] = m

    # ---- low cloud veils inside the city -----------------------------------
    m_low = mat_cloud("M_CloudLow", density=0.085, top_z=7.0, falloff=9.0,
                      wobble=4.5, shape_thr=0.50, shape_wide=0.14,
                      albedo=(0.93, 0.95, 0.99), aniso=0.36, seed_off=11.3)
    low_specs = [
        ("CityLow_A", (-26.0, -18.0, 2.0), (34.0, 26.0, 7.0)),
        ("CityLow_B", (18.0, -46.0, 1.0), (28.0, 22.0, 6.0)),
        ("CityLow_C", (-4.0, 26.0, 3.0), (24.0, 18.0, 6.0)),
        ("CityLow_D", (44.0, 4.0, 2.0), (26.0, 20.0, 5.5)),
    ]
    for nm, c, r in low_specs:
        cloud_ellipsoid(nm, c, r, m_low, coll)

    # ---- distant background sea (north, beyond the island) ------------------
    m_far = mat_cloud("M_CloudFar", density=0.052, top_z=-120.0, falloff=40.0,
                      wobble=20.0, shape_thr=0.46, shape_wide=0.18,
                      albedo=(0.86, 0.90, 0.95), aniso=0.30, seed_off=19.5)
    cloud_box("CloudSeaFar", (200.0, 1050.0, -250.0), (3400.0, 1500.0, 240.0),
              m_far, coll)

    # ---- bank that buries the colossus base, seen from the south -----------
    m_base = mat_cloud("M_CloudBase", density=0.135, top_z=6.0, falloff=14.0,
                       wobble=6.0, shape_thr=0.46, shape_wide=0.16,
                       albedo=(0.94, 0.96, 1.0), aniso=0.38, seed_off=23.9)
    cloud_ellipsoid("StatueBaseBank", (2.0, 32.0, -4.0), (50.0, 24.0, 18.0),
                    m_base, coll, rot=(0, 0, 0.12))
    return True


# ------------------------------------------------------------------ lights --
def add_lights(coll):
    # big soft key from the upper-left (north-west), cool neutral
    key_data = bpy.data.lights.new("KeySun", type="SUN")
    key_data.energy = 5.6
    key_data.angle = math.radians(7.0)
    key_data.color = (0.92, 0.95, 1.0)
    key = bpy.data.objects.new("KeySun", key_data)
    key.rotation_euler = (math.radians(52.0), 0.0, math.radians(-125.0))
    key.location = (-520.0, 380.0, 900.0)
    coll.objects.link(key)

    # broad low-intensity cool fill from the opposite side
    fill_data = bpy.data.lights.new("FillArea", type="AREA")
    fill_data.energy = 9.0e6
    fill_data.shape = "RECTANGLE"
    fill_data.size = 1200.0
    fill_data.size_y = 700.0
    fill_data.color = (0.55, 0.70, 0.90)
    fill = bpy.data.objects.new("FillArea", fill_data)
    fill.location = (420.0, -700.0, 420.0)
    d = Vector((0, 0, 0)) - fill.location
    fill.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    coll.objects.link(fill)

    # faint cool bounce from below the cloud deck
    up_data = bpy.data.lights.new("CloudBounce", type="AREA")
    up_data.energy = 2.4e6
    up_data.shape = "RECTANGLE"
    up_data.size = 1400.0
    up_data.size_y = 1400.0
    up_data.color = (0.58, 0.68, 0.84)
    up = bpy.data.objects.new("CloudBounce", up_data)
    up.location = (-80.0, 20.0, -150.0)
    up.rotation_euler = (math.pi, 0.0, 0.0)
    coll.objects.link(up)
    return key, fill, up


def make_world():
    w = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.020, 0.032, 0.048, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return w


# ----------------------------------------------------------------- cameras --
def _look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def add_camera(name, loc, target, lens=85.0, coll=None, shift_x=0.0,
               ortho=None, dof=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = 36.0
    cd.clip_start = 1.0
    cd.clip_end = 6000.0
    cd.shift_x = shift_x
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    if dof:
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = dof
    ob = bpy.data.objects.new(name, cd)
    ob.location = loc
    coll.objects.link(ob)
    _look_at(ob, target)
    return ob


def build_cameras(coll):
    cams = {}
    # Main: high near-vertical view, island to frame-right, long lens.
    cams["main"] = add_camera(
        "CAM_Main", (-84.0, -318.0, 800.0), (-52.0, 12.0, 16.0),
        lens=135.0, coll=coll)

    # Architecture check: oblique close view of the core terrace.
    cams["arch"] = add_camera(
        "CAM_Architecture", (-74.0, -74.0, 62.0), (0.0, 16.0, 10.0),
        lens=50.0, coll=coll)

    # Statue check: from the island looking north-west at the colossus.
    cams["statue"] = add_camera(
        "CAM_Statue", (34.0, -16.0, 33.0), (0.0, 40.0, 24.0),
        lens=62.0, coll=coll)

    # Top check: orthographic straight-down plan.
    cams["top"] = add_camera(
        "CAM_Top", (0.0, 0.0, 420.0), (0.0, 0.0, 0.0),
        lens=85.0, coll=coll, ortho=250.0)
    return cams


# ------------------------------------------------------------------ render --
def setup_render(preview=False, samples=None):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.seed = CFG["seed"]
    sc.cycles.use_animated_seed = False
    if preview:
        sc.render.resolution_x = 640
        sc.render.resolution_y = 360
        sc.render.resolution_percentage = 100
        sc.cycles.samples = samples or 24
        sc.cycles.preview_samples = 12
        sc.cycles.use_adaptive_sampling = True
        sc.cycles.adaptive_threshold = 0.05
        sc.cycles.volume_step_rate = 5.0
        sc.cycles.volume_max_steps = 256
        sc.cycles.max_bounces = 4
        sc.cycles.volume_bounces = 2
    else:
        sc.render.resolution_x = 1920
        sc.render.resolution_y = 1080
        sc.render.resolution_percentage = 100
        sc.cycles.samples = samples or 128
        sc.cycles.use_adaptive_sampling = True
        sc.cycles.adaptive_threshold = 0.015
        sc.cycles.adaptive_min_samples = 24
        sc.cycles.volume_step_rate = 4.0
        sc.cycles.volume_max_steps = 320
        sc.cycles.max_bounces = 6
        sc.cycles.volume_bounces = 2
        sc.cycles.transparent_max_bounces = 8
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
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.color_depth = "16" if not preview else "8"
    sc.render.use_persistent_data = True
    try:
        sc.view_settings.view_transform = "AgX"
        for look in ("AgX - Medium High Contrast", "AgX - Medium High Contrast",
                     "Medium High Contrast", "None"):
            try:
                sc.view_settings.look = look
                break
            except Exception:
                continue
    except Exception:
        pass
    sc.view_settings.exposure = 0.15
    return sc
