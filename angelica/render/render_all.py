#!/usr/bin/env python3
"""Render every job of an inventory with several Blender processes.

    render_all.py JOBS.json OUT_DIR [--blender PATH] [--workers N] [--size 1000]
                  [--samples 64] [--category npc|player] [--force]

Jobs are ordered players first, then the NPC groups that are characters, then
monsters, scenery and props, and dealt round-robin to the workers. Already
rendered jobs (with job.json) are skipped unless --force is given.
Logs go to OUT_DIR/_logs/worker-N.log.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

# NPC folders that are people first, things last.
GROUP_ORDER = [
    "青铜圣斗士", "白银圣斗士", "黄金圣斗士", "黑暗圣斗士", "雅典娜", "圣域势力", "冥王势力",
    "海皇势力", "其他原著角色", "动画", "其他", "圣域地区", "庐山地区", "遗忘之路地区",
    "死亡皇后岛地区", "东西伯利亚", "亚特兰蒂斯", "仙女岛", "哈迪斯城", "极乐净土",
    "新手村地区", "银河竞技场地区", "选人背景npc", "结婚场景", "boss", "宠物", "野兽",
    "怪物", "技能用怪", "机关npc", "机关怪物", "洪荒模型", "滚雪球", "神器", "场景",
    "场景物品", "矿物",
]


def job_rank(job):
    if job["category"] == "player":
        return (0, job["group"], job["name"])
    if job["category"] == "object":
        return (0, "z-object", job["id"])
    try:
        g = GROUP_ORDER.index(job["group"])
    except ValueError:
        g = len(GROUP_ORDER)
    return (1, g, job["id"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("jobs")
    ap.add_argument("out_dir")
    ap.add_argument("--blender", default=os.environ.get("BLENDER", shutil.which("blender") or "blender"))
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--size", type=int, default=1000)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--category", choices=["npc", "player", "object"])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    with open(a.jobs, encoding="utf-8") as f:
        jobs = json.load(f)
    if a.category:
        jobs = [j for j in jobs if j["category"] == a.category]
    if not a.force:
        jobs = [j for j in jobs if not os.path.exists(os.path.join(a.out_dir, j["id"], "job.json"))]
    jobs.sort(key=job_rank)
    print("%d jobs to render with %d workers" % (len(jobs), a.workers), flush=True)
    if not jobs:
        return 0

    log_dir = os.path.join(a.out_dir, "_logs")
    os.makedirs(log_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="render_jobs_")
    procs = []
    for w in range(a.workers):
        chunk = jobs[w::a.workers]
        if not chunk:
            continue
        jobs_file = os.path.join(tmp, "worker-%d.json" % w)
        with open(jobs_file, "w", encoding="utf-8") as f:
            json.dump(chunk, f, ensure_ascii=False)
        cmd = [a.blender, "-b", "--python", os.path.join(HERE, "blender_render.py"), "--",
               jobs_file, a.out_dir, "--size", str(a.size), "--samples", str(a.samples)]
        if a.force:
            cmd.append("--force")
        log = open(os.path.join(log_dir, "worker-%d.log" % w), "a")
        procs.append(subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT))
    rc = 0
    for p in procs:
        rc |= p.wait()
    shutil.rmtree(tmp, ignore_errors=True)
    print("finished, exit code %d" % rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
