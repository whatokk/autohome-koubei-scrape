# -*- coding: utf-8 -*-
"""批量抓取「满级精华」口碑全文并落盘"""
import json, time, os
from fetch_details import fetch_one, SPECID

RAW = "data/raw/spec_%s_raw.json" % SPECID
OUT = "data/mjjh_full.json"


def score_avg(item):
    sl = item.get("scoreList") or []
    vals = []
    for s in sl:
        try:
            vals.append(float(s.get("value")))
        except Exception:
            pass
    return round(sum(vals) / len(vals), 2) if vals else None


def main():
    raw = json.load(open(RAW, encoding="utf-8"))
    mjjh = [x for x in raw
            if any((m or {}).get("name") == "满级精华" for m in (x.get("medals") or []))]
    print("满级精华总数", len(mjjh), flush=True)
    out = []
    for i, it in enumerate(mjjh, 1):
        d = fetch_one(it["Koubeiid"])
        rec = {
            "seq": i,
            "koubeiid": it["Koubeiid"],
            "url": "https://k.autohome.com.cn/spec/%s/view_%s_1.html" % (SPECID, it["Koubeiid"]),
            "title": it.get("feeling_summary"),
            "username": it.get("username"),
            "userid": it.get("userid"),
            "posttime": it.get("posttime"),
            "score": score_avg(it),
            "scoreList": it.get("scoreList"),
            "medals": [m.get("name") for m in (it.get("medals") or [])],
            "distance": it.get("distance"),
            "buyprice": it.get("buyprice"),
            "buyplace": it.get("buyplace"),
            "boughtDate": it.get("boughtDate"),
            "carOwnershipPeriod": it.get("carOwnershipPeriod"),
            "oil": it.get("actual_oil_consumption"),
            "battery": it.get("actual_battery_consumption"),
            "range": it.get("summerRange") or it.get("springRange") or it.get("winterRange"),
            "photoCount": it.get("photoCount"),
            "viewcount": it.get("viewcount"),
            "helpfulcount": it.get("helpfulcount"),
            "commentcount": it.get("commentcount"),
            "exinfolist": it.get("exinfolist"),
            "piclist": it.get("piclist"),
            "sections": (d or {}).get("sections", {}),
            "scores": (d or {}).get("scores", {}),
            "append": (d or {}).get("append", ""),
            "ktype": ("探店" if any(k in ((d or {}).get("sections") or {})
                                    for k in ["新车好评", "新车槽点", "好评", "槽点"])
                      else "车主"),
            "ok": bool(d),
        }
        out.append(rec)
        if i % 10 == 0 or i == len(mjjh):
            json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("progress %d/%d ok=%d" % (i, len(mjjh), sum(1 for r in out if r["ok"])), flush=True)
        time.sleep(0.3)
    print("DONE", len(out), flush=True)


if __name__ == "__main__":
    main()
