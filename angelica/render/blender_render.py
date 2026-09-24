#!/usr/bin/env python3
"""Render character jobs with Blender (run inside Blender, background mode).

    blender -b --python blender_render.py -- JOBS.json OUT_DIR [--size 1200] [--samples 64]
            [--only ID,ID...] [--force] [--views front,side,back]

Every job (see inventory.py) becomes OUT_DIR/<job id>/{front,side,back}.png:
orthographic full-body views of the model in its bind (T) pose with a
transparent background, plus `job.json` with the bounding box and parts used.

Coordinate conversion: the engine is left-handed, Y up, characters face +Z.
Blender vertex = (-x, -z, y) so the character faces -Y with its left arm at +X.
"""
import json
import math
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ski import parse_ski, SkiError  # noqa: E402

VIEWS = {
    # name: (camera direction from the model centre, camera rotation euler)
    "front": ((0, -1, 0), (math.pi / 2, 0, 0)),
    "side": ((1, 0, 0), (math.pi / 2, 0, math.pi / 2)),
    "back": ((0, 1, 0), (math.pi / 2, 0, math.pi)),
}


def args_after_dashes():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def parse_args(argv):
    opts = {"size": 1200, "samples": 64, "only": None, "force": False, "views": list(VIEWS)}
    pos = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--size":
            opts["size"] = int(argv[i + 1]); i += 2
        elif a == "--samples":
            opts["samples"] = int(argv[i + 1]); i += 2
        elif a == "--only":
            opts["only"] = set(argv[i + 1].split(",")); i += 2
        elif a == "--views":
            opts["views"] = argv[i + 1].split(","); i += 2
        elif a == "--force":
            opts["force"] = True; i += 1
        else:
            pos.append(a); i += 1
    if len(pos) != 2:
        raise SystemExit(__doc__)
    return pos[0], pos[1], opts


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    if os.environ.get("RENDER_DEVICE", "CPU").upper() == "GPU":
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for backend in (os.environ.get("RENDER_BACKEND", "CUDA"), "OPTIX", "HIP", "ONEAPI"):
            try:
                prefs.compute_device_type = backend
            except TypeError:
                continue
            prefs.get_devices()
            gpus = [d for d in prefs.devices if d.type != "CPU"]
            if gpus:
                for d in prefs.devices:
                    d.use = d.type != "CPU"
                scene.cycles.device = "GPU"
                break
    scene.cycles.use_denoising = os.environ.get("RENDER_DENOISE", "0") == "1"  # OIDN reloads its kernels every frame in background mode (12 s)
    scene.cycles.max_bounces = 2
    scene.cycles.transparent_max_bounces = 16
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (1, 1, 1, 1)
    bg.inputs[1].default_value = 0.8
    scene.world = world
    return scene


_image_cache = {}


def load_image(path):
    img = _image_cache.get(path)
    if img is None:
        img = bpy.data.images.load(path, check_existing=True)
        img.alpha_mode = "STRAIGHT"
        _image_cache[path] = img
    return img


def make_material(name, png):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.8
    bsdf.inputs["Specular IOR Level"].default_value = 0.15
    if png:
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = load_image(png)
        tex.interpolation = "Linear"
        links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        if tex.image.channels == 4 and tex.image.depth in (32, 64, 128):
            # cut-out alpha (hair cards, feathers, holes)
            math_node = nodes.new("ShaderNodeMath")
            math_node.operation = "GREATER_THAN"
            math_node.inputs[1].default_value = 0.5
            links.new(tex.outputs["Alpha"], math_node.inputs[0])
            links.new(math_node.outputs[0], bsdf.inputs["Alpha"])
            mat.surface_render_method = "DITHERED"
    else:
        bsdf.inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1)
    mat.use_backface_culling = False
    return mat


def convert(p):
    return (-p[0], -p[2], p[1])


def winding_disagrees(verts, normals, faces):
    """True when the face winding gives normals opposite to the stored ones."""
    agree = 0
    for a, b, c in faces[:400]:
        ax, ay, az = verts[a]
        ux, uy, uz = verts[b][0] - ax, verts[b][1] - ay, verts[b][2] - az
        vx, vy, vz = verts[c][0] - ax, verts[c][1] - ay, verts[c][2] - az
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        sx = normals[a][0] + normals[b][0] + normals[c][0]
        sy = normals[a][1] + normals[b][1] + normals[c][1]
        sz = normals[a][2] + normals[b][2] + normals[c][2]
        d = nx * sx + ny * sy + nz * sz
        if d > 0:
            agree += 1
        elif d < 0:
            agree -= 1
    return agree < 0


def add_mesh(part, mesh, key, materials):
    verts = [convert(p) for p in mesh["positions"]]
    idx = mesh["indices"]
    faces = [(idx[i], idx[i + 1], idx[i + 2]) for i in range(0, len(idx) - 2, 3)]
    faces = [f for f in faces if len(set(f)) == 3 and max(f) < len(verts)]
    normals = [convert(n) for n in mesh["normals"]]
    if winding_disagrees(verts, normals, faces):
        faces = [(a, c, b) for a, b, c in faces]
    me = bpy.data.meshes.new(key)
    me.from_pydata(verts, [], faces)
    for poly in me.polygons:
        poly.use_smooth = True
    uv = me.uv_layers.new(name="UVMap")
    uvs = mesh["uvs"]
    for loop in me.loops:
        u, v = uvs[loop.vertex_index]
        uv.data[loop.index].uv = (u, 1.0 - v)
    try:
        me.normals_split_custom_set_from_vertices(normals)
    except Exception as exc:
        print("  custom normals failed for %s: %s" % (key, exc))
    tex = mesh["texture_name"]
    png = part["textures"].get(tex)
    mkey = png or "__none__"
    if mkey not in materials:
        materials[mkey] = make_material(os.path.basename(png) if png else "none", png)
    me.materials.append(materials[mkey])
    me.validate()
    me.update()
    obj = bpy.data.objects.new(key, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def build_job(job):
    """Load all parts. Meshes with identical geometry are loaded once, and a
    suit/body mesh that a later cloth piece duplicates is dropped (the cloth
    piece is the one shown in game)."""
    geometry = {}  # positions hash -> (part order, mesh, part)
    order = 0
    for part in job["parts"]:
        try:
            model = parse_ski(part["ski"])
        except (SkiError, OSError) as exc:
            print("  skip %s: %s" % (part["ski"], exc))
            continue
        for mesh in model["meshes"]:
            if not mesh["positions"]:
                continue
            h = hash(tuple(mesh["positions"]))
            geometry[h] = (order, mesh, part)  # later parts override earlier ones
            order += 1
    materials = {}
    objs = []
    for n, (_o, mesh, part) in enumerate(sorted(geometry.values(), key=lambda t: t[0])):
        objs.append(add_mesh(part, mesh, "m%03d" % n, materials))
    return objs


def bbox(objs):
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for o in objs:
        for v in o.data.vertices:
            for k in range(3):
                lo[k] = min(lo[k], v.co[k])
                hi[k] = max(hi[k], v.co[k])
    return lo, hi


def render_views(scene, objs, out_dir, views, size, samples):
    lo, hi = bbox(objs)
    centre = [(a + b) / 2 for a, b in zip(lo, hi)]
    extent = [b - a for a, b in zip(lo, hi)]
    ortho = max(extent) * 1.08 + 0.05
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = ortho
    cam_data.clip_end = 1000
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    sun_data = bpy.data.lights.new("sun", "SUN")
    sun_data.energy = 2.5
    sun_data.angle = math.radians(20)
    sun = bpy.data.objects.new("sun", sun_data)
    scene.collection.objects.link(sun)
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.cycles.samples = samples
    dist = max(extent) * 4 + 5
    for view in views:
        direction, rot = VIEWS[view]
        cam.location = [c + d * dist for c, d in zip(centre, direction)]
        cam.rotation_euler = rot
        # key light: from the camera side, a little above and to the left
        sun.rotation_euler = (rot[0] - math.radians(35), rot[1], rot[2] + math.radians(25))
        scene.render.filepath = os.path.join(out_dir, view + ".png")
        bpy.ops.render.render(write_still=True)
    return {"bbox_min": lo, "bbox_max": hi, "ortho_scale": ortho}


def main():
    jobs_path, out_root, opts = parse_args(args_after_dashes())
    with open(jobs_path, encoding="utf-8") as f:
        jobs = json.load(f)
    if opts["only"]:
        jobs = [j for j in jobs if j["id"] in opts["only"]]
    done = 0
    for job in jobs:
        out_dir = os.path.join(out_root, job["id"])
        marker = os.path.join(out_dir, "job.json")
        if os.path.exists(marker) and not opts["force"]:
            continue
        t0 = time.time()
        print("render %s" % job["id"], flush=True)
        scene = reset_scene()
        _image_cache.clear()
        t1 = time.time()
        objs = build_job(job)
        if not objs:
            print("  no geometry", flush=True)
            continue
        os.makedirs(out_dir, exist_ok=True)
        t2 = time.time()
        info = render_views(scene, objs, out_dir, opts["views"], opts["size"], opts["samples"])
        print("  scene %.1fs build %.1fs render %.1fs" % (t1 - t0, t2 - t1, time.time() - t2), flush=True)
        info.update({"id": job["id"], "name": job["name"], "category": job["category"],
                     "group": job["group"], "parts": [p["ski"] for p in job["parts"]],
                     "meshes": len(objs), "seconds": round(time.time() - t0, 1)})
        with open(marker, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=1)
        done += 1
        print("  done in %.1fs" % (time.time() - t0), flush=True)
    print("rendered %d jobs" % done)


if __name__ == "__main__":
    main()
