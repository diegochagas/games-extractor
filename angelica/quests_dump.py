"""Structured quest dump from data_quest.tsv -> quests.json (list ordered by id) and quests_names.txt"""
import csv, re, json, sys, collections
OUT=sys.argv[1]; lang=sys.argv[2] if len(sys.argv)>2 else "pt-BR"
rows=[{"key":k,"zh_source":z,"translation":t} for k,z,t in json.load(open(f"{OUT}/text/lang/{lang}.json",encoding="utf-8"))["data_quest"]]
Q=collections.defaultdict(lambda: {"delv":{}, "award":{}, "unq":{}})
for r in rows:
    m=re.match(r"task_(\d+)\.(.*)$", r["key"]); 
    if not m: continue
    tid=int(m.group(1)); k=m.group(2); q=Q[tid]; v=r["translation"]; zh=r["zh_source"]
    if k=="m_szName": q["name"]=v; q["name_zh"]=zh
    elif k=="m_wstrDescript": q["descript"]=v
    elif k=="m_wstrMethodTrace": q["trace"]=v
    elif k=="m_wstrMethodString": q["method"]=v
    else:
        m2=re.match(r"m_(DelvTaskTalk|AwardTalk|UnqualifiedTalk)(?:\.text|\.windows\.(\d+)\.(talk_text|options\.(\d+)\.text))$", k)
        if not m2: q.setdefault("other",{})[k]=v; continue
        kind={"DelvTaskTalk":"delv","AwardTalk":"award","UnqualifiedTalk":"unq"}[m2.group(1)]
        if m2.group(2) is None: q[kind]["text"]=v
        else:
            w=q[kind].setdefault("windows",{}).setdefault(int(m2.group(2)),{"options":{}})
            if m2.group(3)=="talk_text": w["talk"]=v
            else: w["options"][int(m2.group(4))]=v
out=[]
for tid in sorted(Q):
    q=Q[tid]; q["id"]=tid
    for kind in ("delv","award","unq"):
        if "windows" in q[kind]:
            q[kind]["windows"]=[{"n":n, "talk":w.get("talk",""), "options":[w["options"][o] for o in sorted(w["options"])]} for n,w in sorted(q[kind]["windows"].items())]
    out.append(q)
json.dump(out, open(f"{OUT}/text/quests_{lang}.json","w"), ensure_ascii=False, indent=0)
with open(f"{OUT}/text/quests_{lang}_names.txt","w") as f:
    for q in out: f.write(f'{q["id"]}\t{q.get("name","")}\t{"D" if q.get("descript") else "-"}{"T" if q["delv"] else "-"}{"A" if q["award"] else "-"}\t{q.get("name_zh","")}\n')
story=[q for q in out if q.get("descript") and (q["delv"].get("windows") or q["award"].get("windows"))]
print(len(out),"quests;", sum(1 for q in out if q.get("descript")),"with description;", len(story), "with description + dialogue windows")
