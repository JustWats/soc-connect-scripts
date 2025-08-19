#!/usr/bin/env python3
import json, uuid, pathlib, sys, requests

BASE_URL="< YOUR SOC URL>"; CLIENT_ID="< YOUR CLIENT ID>"; CLIENT_SECRET="<YOUR CLIENT SECRET>"
VERIFY_SSL=False; OUT_DIR=pathlib.Path("./cases"); EVENT_LIMIT=5000; TIMEOUT=45

try:
    import urllib3; urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception: pass

S=requests.Session(); S.verify=VERIFY_SSL; S.headers.update({"Accept":"application/json"})

_T=sys.stdout.isatty()
def _c(s,k): return f"\033[{k}m{s}\033[0m" if _T else s
G=lambda s:_c(s,'32'); C=lambda s:_c(s,'36'); Y=lambda s:_c(s,'33'); R=lambda s:_c(s,'31')
B=lambda s:_c(s,'1');  D=lambda s:_c(s,'2')

def get_token():
    r=S.post(f"{BASE_URL}/oauth2/token",data={"grant_type":"client_credentials"},auth=(CLIENT_ID,CLIENT_SECRET),timeout=TIMEOUT)
    if r.status_code!=200: raise SystemExit(f"[!] token HTTP {r.status_code}\n{r.text}")
    try: return r.json()["access_token"]
    except Exception: raise SystemExit("[!] token parse failed:\n"+r.text[:1000])

def jget(url,params=None):
    r=S.get(url,params=params,timeout=TIMEOUT)
    if not r.ok: return None,r.status_code,r.text
    try: return r.json(),200,None
    except Exception:
        b=(r.text or "").strip(); return ([],200,None) if not b else (None,200,b)

def wjson(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,indent=2,ensure_ascii=False),encoding="utf-8")
def wtext(p,t): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(t or "",encoding="utf-8")

def discover_case_ids():
    obj,st,raw=jget(f"{BASE_URL}/connect/events",params={"query":"so_kind:case","range":"2000/01/01 00:00:00 - 2030/01/01 00:00:00","zone":"UTC","format":"2006/01/02 15:04:05","metricLimit":0,"eventLimit":EVENT_LIMIT})
    if obj is None: raise SystemExit(f"[!] case-list HTTP {st}\n{raw or ''}")
    ids=set()
    for ev in obj.get("events",[]):
        p=ev.get("payload") or {}
        for k in ("so_case_id","caseId","id"):
            v=p.get(k) or ev.get(k)
            if v:
                try: uuid.UUID(str(v)); ids.add(str(v)); break
                except Exception: pass
    return sorted(ids)

EP={"case":["/connect/case/{id}"],"artifacts":["/connect/case/{id}/artifacts","/connect/case/artifacts/{id}"],"comments":["/connect/case/{id}/comments","/connect/case/comments/{id}"],"events":["/connect/case/{id}/events","/connect/case/events/{id}"],"history":["/connect/case/{id}/history","/connect/case/history/{id}"]}

def pull_one(cid):
    base=OUT_DIR/cid; base.mkdir(parents=True,exist_ok=True); status={}
    for name,paths in EP.items():
        ok=False; last=(None,None)
        for p in paths:
            obj,st,raw=jget(f"{BASE_URL}{p.format(id=cid)}")
            if obj is not None: wjson(base/f"{name}.json",obj); ok=True; break
            last=(st,raw)
        if not ok:
            st,raw=last
            if name in ("artifacts","history") and st in (200,404,500): wjson(base/f"{name}.json",[]); ok=True
            else: wtext(base/f"{name}.err.{st}.txt",raw)
        status[name]=ok
    try: title=(json.loads((base/'case.json').read_text()) or {}).get('title') or ""
    except Exception: title=""
    print(f"{G('[•]')} {cid[:8]}  "+" ".join([f"{k[:3]} {G('✓') if v else R('×')}" for k,v in status.items()])+f"  {D(title[:60])}")
    return all(status.values())

def main():
    print("\n "+B("Security Onion Case Puller")+"\n"+"─"*60); print(f"Base URL : {BASE_URL}\nOutput   : {OUT_DIR.resolve()}\n"+"─"*60)
    S.headers["Authorization"]="Bearer "+get_token()
    print(C("[*]")+" Discovering cases…"); ids=discover_case_ids(); print(f"{G('[+]')} Found {len(ids)} cases\n")
    ok=sum(pull_one(cid) or 0 for cid in ids)
    print("\n"+"─"*60); print(f"{G('✓')}  Bundles OK : {ok}/{len(ids)}"); print(f"{C('i')}  Saved to   : {OUT_DIR.resolve()}"); print("─"*60)

if __name__=="__main__":
    try: main()
    except KeyboardInterrupt: print("\n"+Y("[!]")+" Aborted")
