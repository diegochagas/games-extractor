"""Match player screenshots (a Saints/ folder) to the game's photobook cloth cards and to cloth renders (a Cloths/ folder) with CLIP.

    clip_match.py SOURCE_DIR DUMP_DIR OUT_DIR     (needs torch + open_clip; writes clip_matches.json and clip_dups.json)

SOURCE_DIR holds Saints/ (screenshots of the player's character in each cloth) and Cloths/ (reference renders);
the result was reviewed by hand into text/saints_screenshots.csv of the dump.
"""
import os, sys, json, torch, open_clip
from PIL import Image
D, OUT, S = sys.argv[1], sys.argv[2], sys.argv[3]
model, _, pre = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
model.eval(); tok = open_clip.get_tokenizer("ViT-B-32")
def emb(paths, crop=None):
    out=[]
    for i in range(0, len(paths), 32):
        ims=[]
        for p in paths[i:i+32]:
            im=Image.open(p).convert("RGB")
            if crop: im=crop(im)
            ims.append(pre(im))
        with torch.no_grad(): e=model.encode_image(torch.stack(ims)); e/=e.norm(dim=-1,keepdim=True)
        out.append(e)
    return torch.cat(out)
shots=sorted(os.path.join(D,"Saints",f) for f in os.listdir(D+"/Saints"))
def crop_shot(im): w,h=im.size; return im.crop((int(w*.30),int(h*.02),int(w*.70),int(h*.98)))
pb_dir=OUT+"/images/surfaces/res/photobook"; cards=sorted(os.path.join(pb_dir,f) for f in os.listdir(pb_dir) if f.endswith(".png"))
def crop_card(im): w,h=im.size; return im.crop((int(w*.08),int(h*.06),int(w*.92),int(h*.94)))
cloths=sorted(os.path.join(D,"Cloths",f) for f in os.listdir(D+"/Cloths"))
E_s=emb(shots,crop_shot); E_c=emb(cards,crop_card); E_r=emb(cloths)
sim_c=(E_s@E_c.T); sim_r=(E_s@E_r.T)
res=[]
for i,p in enumerate(shots):
    tc=sim_c[i].topk(5); tr=sim_r[i].topk(3)
    res.append({"shot":os.path.basename(p), "cards":[(os.path.basename(cards[j])[:-8], round(float(v),3)) for v,j in zip(tc.values,tc.indices)],
                "renders":[(os.path.basename(cloths[j])[:-4], round(float(v),3)) for v,j in zip(tr.values,tr.indices)]})
json.dump(res, open(S+"/clip_matches.json","w"), ensure_ascii=False, indent=0)
# also cluster near-duplicate shots (same cloth shot twice)
sim_ss=E_s@E_s.T
dups=[(os.path.basename(shots[i]),os.path.basename(shots[j]),round(float(sim_ss[i,j]),3)) for i in range(len(shots)) for j in range(i+1,len(shots)) if sim_ss[i,j]>0.97]
json.dump(dups, open(S+"/clip_dups.json","w")); print("shots",len(shots),"cards",len(cards),"renders",len(cloths),"near-dups",len(dups))
for r in res[:12]: print(r["shot"], r["cards"][:3], r["renders"][:2])
