"""Open one model of the dump in Blender's window (T pose, textured), the same way the renders were built.

    cd DUMP_DIR && MODELO=<name> blender --python /path/to/view_in_blender.py

<name> = the gallery file name without "-frente.png" (e.g. pegaso-nivel-1-masc), the Chinese asset name, the
Portuguese caption or the job id of text/render_jobs.json. In Blender press Z > Material Preview to see the
textures, Home to frame the model, Numpad 1 / 3 for front / side.
"""
import json
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blender_render as r  # noqa: E402

name = os.environ["MODELO"]
idx = json.load(open("text/gallery_index.json", encoding="utf-8"))["items"]
jobs = {j["id"]: j for j in json.load(open("text/render_jobs.json", encoding="utf-8"))}
hit = next((x for x in idx if x["kind"] == "render" and name in (x.get("base"), x.get("job"), x.get("zh"), x.get("pt"))), None)
job = jobs[hit["job"] if hit else name]
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
objs = r.build_job(job)
print("loaded %s: %d meshes" % (job["id"], len(objs)))
