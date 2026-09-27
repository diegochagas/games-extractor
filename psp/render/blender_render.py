#!/usr/bin/env python3
"""Render .glb models with Blender (run inside Blender, background mode).

    blender -b --python blender_render.py -- JOBS.json OUT_DIR [--size 1200] [--samples 16]
            [--only ID,ID...] [--force] [--views front,side,back]

JOBS.json is a list of {"id": "characters/kog/kog_00_normal", "glb": "/path/model.glb",
"views": [...], "pose": {"animation": "idle_001", "frame": 0}, "hide": ["sky"], "cull": true};
`views`, `pose`, `hide` (prefixes of node names to leave out) and `cull` (faces seen from behind
are not drawn) are optional; without a pose the model is drawn in its bind pose. Every job becomes
OUT_DIR/<id>/<view>.png: orthographic views with a transparent background, plus job.json.

The glTF importer turns the model to Blender's Z-up: it faces -Y, its left arm at +X.
"""
import json
import math
import os
import sys
import time

import bpy
from mathutils import Vector

VIEWS = {
    # name: (camera direction from the model centre, camera rotation euler)
    "front": ((0, -1, 0), (math.pi / 2, 0, 0)),
    "side": ((1, 0, 0), (math.pi / 2, 0, math.pi / 2)),
    "back": ((0, 1, 0), (math.pi / 2, 0, math.pi)),
    "left": ((-1, 0, 0), (math.pi / 2, 0, -math.pi / 2)),
    "top": ((0, 0, 1), (0, 0, 0)),
    "three_quarter": ((0.6, -1, 0.35), None),
}


def parse_args(argv):
    opts = {"size": 1200, "samples": 16, "only": None, "force": False, "views": ["front", "side", "back"]}
    pos = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--size", "--samples"):
            opts[a[2:]] = int(argv[i + 1]); i += 2
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


def reset_scene(samples):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    if os.environ.get("RENDER_DEVICE", "CPU").upper() == "GPU":
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for backend in (os.environ.get("RENDER_BACKEND", "OPTIX"), "CUDA", "HIP", "ONEAPI"):
            try:
                prefs.compute_device_type = backend
            except TypeError:
                continue
            prefs.get_devices()
            if [d for d in prefs.devices if d.type != "CPU"]:
                for d in prefs.devices:
                    d.use = d.type != "CPU"
                scene.cycles.device = "GPU"
                break
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False          # OIDN reloads its kernels every frame in background mode
    scene.cycles.max_bounces = 1
    scene.cycles.transparent_max_bounces = 32
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    scene.world = world
    return scene


def bounds(scene):
    deps = bpy.context.evaluated_depsgraph_get()
    lo = Vector((1e18, 1e18, 1e18))
    hi = Vector((-1e18, -1e18, -1e18))
    found = False
    for obj in scene.objects:
        if obj.type != "MESH":
            continue
        ev = obj.evaluated_get(deps)
        me = ev.to_mesh()
        for v in me.vertices:
            p = ev.matrix_world @ v.co
            for k in range(3):
                lo[k] = min(lo[k], p[k])
                hi[k] = max(hi[k], p[k])
            found = True
        ev.to_mesh_clear()
    return (lo, hi) if found else (Vector((0, 0, 0)), Vector((1, 1, 1)))


def cull_backfaces(mat):
    """Faces seen from behind become transparent (sky domes and walls do not hide a stage)."""
    if not mat.node_tree:
        return
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    out = next((n for n in nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None)
    if out is None or not out.inputs["Surface"].is_linked:
        return
    surface = out.inputs["Surface"].links[0].from_socket
    geo = nodes.new("ShaderNodeNewGeometry")
    clear = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(geo.outputs["Backfacing"], mix.inputs[0])
    links.new(surface, mix.inputs[1])
    links.new(clear.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], out.inputs["Surface"])


def apply_pose(scene, pose):
    if not pose:
        return
    action = None
    wanted = pose.get("animation", "").lower()
    for a in bpy.data.actions:
        if a.name.lower() == wanted or a.name.lower().startswith(wanted + "_"):
            action = a
            break
    if action is None:
        print("  pose animation not found:", wanted)
        return
    for obj in scene.objects:
        if obj.type == "ARMATURE":
            obj.animation_data_create()
            obj.animation_data.action = action
    scene.frame_set(int(pose.get("frame", 0)))


def clear_animation(scene):
    for obj in scene.objects:
        if obj.animation_data:
            obj.animation_data.action = None
        if obj.type == "ARMATURE":
            for pb in obj.pose.bones:
                pb.location = (0, 0, 0)
                pb.rotation_quaternion = (1, 0, 0, 0)
                pb.rotation_euler = (0, 0, 0)
                pb.scale = (1, 1, 1)
    scene.frame_set(0)


def render_job(job, out_dir, opts):
    scene = reset_scene(opts["samples"])
    bpy.ops.import_scene.gltf(filepath=job["glb"])
    for img in bpy.data.images:
        img.alpha_mode = "STRAIGHT"
    for mat in bpy.data.materials:
        mat.use_backface_culling = False
        if mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == "TEX_IMAGE":
                    node.interpolation = "Linear"
    for obj in list(scene.objects):                       # "hide": node name prefixes left out
        if any(obj.name.lower().startswith(h.lower()) for h in job.get("hide", [])):
            bpy.data.objects.remove(obj, do_unlink=True)
    if job.get("cull"):
        for mat in bpy.data.materials:
            cull_backfaces(mat)
    if job.get("pose"):
        apply_pose(scene, job["pose"])
    else:
        clear_animation(scene)
    bpy.context.view_layer.update()
    lo, hi = bounds(scene)
    centre = (lo + hi) / 2
    size = hi - lo
    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    reach = max(size) * 4 + 10
    cam_data.clip_start = 0.01
    cam_data.clip_end = reach * 2
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for view in job.get("views") or opts["views"]:
        direction, rot = VIEWS[view]
        d = Vector(direction).normalized()
        cam.location = centre + d * reach
        if rot is None:
            cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        else:
            cam.rotation_euler = rot
        bpy.context.view_layer.update()
        # extent of the box seen from this camera
        inv = cam.matrix_world.inverted()
        xs, ys = [], []
        for x in (lo.x, hi.x):
            for y in (lo.y, hi.y):
                for z in (lo.z, hi.z):
                    p = inv @ Vector((x, y, z))
                    xs.append(p.x)
                    ys.append(p.y)
        w, h = (max(xs) - min(xs)) * 1.06, (max(ys) - min(ys)) * 1.06
        w, h = max(w, 1e-3), max(h, 1e-3)
        big = opts["size"]
        if w >= h:
            scene.render.resolution_x, scene.render.resolution_y = big, max(16, int(round(big * h / w)))
            cam_data.ortho_scale = w
        else:
            scene.render.resolution_x, scene.render.resolution_y = max(16, int(round(big * w / h))), big
            cam_data.ortho_scale = h
        scene.render.filepath = os.path.join(out_dir, view + ".png")
        bpy.ops.render.render(write_still=True)
        written.append(view)
    with open(os.path.join(out_dir, "job.json"), "w", encoding="utf-8") as f:
        json.dump({"id": job["id"], "glb": job["glb"], "views": written, "pose": job.get("pose"),
                   "bbox_min": list(lo), "bbox_max": list(hi)}, f, ensure_ascii=False, indent=1)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    jobs_path, out, opts = parse_args(argv)
    with open(jobs_path, encoding="utf-8") as f:
        jobs = json.load(f)
    done = failed = 0
    for job in jobs:
        if opts["only"] and job["id"] not in opts["only"]:
            continue
        dest = os.path.join(out, job["id"])
        if not opts["force"] and os.path.exists(os.path.join(dest, "job.json")):
            continue
        t = time.time()
        try:
            render_job(job, dest, opts)
            done += 1
            print("RENDERED %s in %.1fs" % (job["id"], time.time() - t))
        except Exception as exc:                                  # keep the batch going
            failed += 1
            print("FAILED %s: %s" % (job["id"], exc))
    print("done: %d rendered, %d failed" % (done, failed))


main()
