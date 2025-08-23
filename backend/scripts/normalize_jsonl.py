import sys, json, pathlib
# Usage: normalize_jsonl.py <in.jsonl> <out.jsonl> [default_pack] [default_safety]
if len(sys.argv) < 3:
    print("Usage: normalize_jsonl.py <in.jsonl> <out.jsonl> [default_pack] [default_safety]")
    sys.exit(1)
inp   = pathlib.Path(sys.argv[1]); outp = pathlib.Path(sys.argv[2])
dpack = (sys.argv[3] if len(sys.argv) > 3 else None)
dsafe = int(sys.argv[4]) if len(sys.argv) > 4 else None
def pack_from_cat(cat):
    if not cat: return dpack or "misc"
    c = str(cat).lower().strip().replace(" ", "_")
    if c.startswith("everyday"): return "everyday"
    if c.startswith("slang"): return "slang"
    if c.startswith("youth"): return "youth_culture"
    if c.startswith("cultural"): return "cultural"
    if c.startswith("profanity"): return "profanity"
    return dpack or c or "misc"
def safety_from_pack(p):
    return 2 if (p or "").lower() in ("slang","profanity") else 1
def num_phonetic(v):
    if v is None: return None
    if isinstance(v,(int,float)): return float(v)
    s = str(v).lower()
    if "high" in s: return 0.9
    if "medium" in s: return 0.6
    if "low" in s: return 0.3
    try: return float(v)
    except: return None
n=bad=0
with inp.open(encoding="utf-8") as fin, outp.open("w",encoding="utf-8") as fout:
    for line in fin:
        line=line.strip()
        if not line: continue
        try: j=json.loads(line)
        except: bad+=1; continue
        b = (j.get("banglish") or j.get("anflish") or j.get("src") or j.get("input") or j.get("text") or "").strip()
        e = (j.get("english")  or j.get("dst")  or j.get("translation") or j.get("expected") or "").strip()
        if not b or not e: bad+=1; continue
        pack = j.get("pack") or pack_from_cat(j.get("category"))
        safety = j.get("safety_level"); 
        if safety is None: safety = dsafe if dsafe is not None else safety_from_pack(pack)
        variants = j.get("variants") or []
        if not isinstance(variants, list): variants=[str(variants)]
        out={"banglish":b,"english":e,"pack":pack,"safety_level":int(safety),"variants":variants}
        pf=num_phonetic(j.get("phonetic_fidelity"))
        if pf is not None: out["phonetic_fidelity"]=pf
        if j.get("notes"): out["notes"]=j["notes"]
        if j.get("id"): out["id"]=j["id"]
        fout.write(json.dumps(out,ensure_ascii=False)+"\n"); n+=1
print(f"normalized={n}, skipped_bad_lines={bad}, out={outp}")
