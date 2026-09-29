# -*- coding: utf-8 -*-
"""抓取汽车之家口碑列表接口（IPv6 域名需强制 IPv4，走 curl -4）"""
import subprocess, json, sys, time, os

API = "https://koubeiipv6.app.autohome.com.cn/pc/spec/list"
REF = "https://k.autohome.com.cn/spec/{specid}/"


def fetch(specid, page, size=20):
    url = ("%s?specid=%s&pageIndex=%d&pageSize=%d&order=0&ge=0&summaryKey=0&pm=1"
           % (API, specid, page, size))
    cmd = ["curl", "-4", "-s", "-m", "30",
           "-H", "Referer: " + REF.format(specid=specid),
           "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                 "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
           "-H", "Accept: application/json, text/plain, */*",
           url]
    out = subprocess.run(cmd, capture_output=True).stdout
    try:
        return json.loads(out.decode("utf-8", "ignore"))
    except Exception as e:
        print("PARSE FAIL page", page, e, out[:200])
        return None


if __name__ == "__main__":
    specid = sys.argv[1]
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    outdir = sys.argv[3] if len(sys.argv) > 3 else "data/raw"
    os.makedirs(outdir, exist_ok=True)

    j = fetch(specid, 1, size)
    r = j["result"]
    print("rowcount", r.get("rowcount"), "pagecount", r.get("pagecount"),
          "pagesize", r.get("pagesize"), "specname", r.get("specname"))
    allitems = list(r.get("list") or [])
    pages = int(r.get("pagecount") or 1)
    for p in range(2, pages + 1):
        jj = fetch(specid, p, size)
        if not jj or "result" not in jj:
            print("skip page", p)
            continue
        items = jj["result"].get("list") or []
        allitems.extend(items)
        print("page", p, "got", len(items), "total", len(allitems))
        time.sleep(0.6)

    with open(os.path.join(outdir, "spec_%s_raw.json" % specid), "w", encoding="utf-8") as f:
        json.dump(allitems, f, ensure_ascii=False, indent=1)

    # 统计勋章分布
    from collections import Counter
    c = Counter()
    for it in allitems:
        ms = it.get("medals") or []
        if not ms:
            c["（无勋章）"] += 1
        for m in ms:
            c[m.get("name")] += 1
    print("TOTAL", len(allitems))
    for k, v in c.most_common():
        print("  ", k, v)
