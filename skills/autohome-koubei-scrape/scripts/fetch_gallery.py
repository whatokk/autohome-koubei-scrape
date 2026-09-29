#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
汽车之家「车型图库」批量下载 —— 按分类成套抓取指定配置的高清图

背景/坑位（2026-09 实测）：
  1. 图库分类页 https://car.autohome.com.cn/pic/series-s<specid>/<seriesid>-<catid>.html
     · 带 -s<specid> 前缀 = 只抓该配置的图（不带则混全系配置）
     · 页面 GBK/GB2312 编码，必须 decode("gb18030")
     · 图片不在 src 里，而在 <img ... data-webp="//carX.autoimg.cn/...480x360_0_q95_c42_autohomecar__xxx.jpg">
     · 每页 60 张；翻页 -p2.html / -p3.html ...
  2. 尺寸靠改文件名前缀：
     480x360_0_q95_c42_ = 缩略图(480x360)
     1024x0_1_q95_      = 1024x768
     1600x0_1_q95_      = 1600x1200
     1920x0_1_q95_      = 1920x1440  ← 最大，优先
  3. 官图分类(catid=53) 可能 302 回落地页，落地页里仍有该配置的官图，可照抓。
  4. 必须 curl -4（autohome 域名 IPv6 优先，Python urllib 会 SSL 超时）。
"""
import os
import re
import sys
import json
import time
import subprocess

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
CATS = [("1", "车身外观"), ("10", "中控方向盘"), ("3", "车厢座椅"),
        ("12", "其它细节"), ("53", "官图"), ("55", "车展")]
# 抓取顺序：官图放最前 —— 官图与外观/内饰官方图重合度高，先抓官图才能凑满 10 张，
# 否则官图会被前面已入册的重复图挤掉（实测 官图后抓只剩 8 张）。
PROC_ORDER = ["53", "1", "10", "3", "12", "55"]
SIZE_PREF = ["1920x0_1_q95_", "1600x0_1_q95_", "1024x0_1_q95_", "480x360_0_q95_c42_"]
THUMB_PREFIX = "480x360_0_q95_c42_"


def curl(url, out=None, referer="https://car.autohome.com.cn/", timeout=30):
    cmd = ["curl", "-4", "-s", "-L", "-m", str(timeout), "-A", UA, "-e", referer]
    if out:
        cmd += ["-o", out, "-w", "%{http_code}"]
    cmd.append(url)
    r = subprocess.run(cmd, capture_output=True)
    if out:
        try:
            return r.stdout.decode().strip()
        except Exception:
            return "?"
    return r.stdout


def img_id(url):
    """图标唯一 ID：autohomecar__ 之后的部分"""
    m = re.search(r'autohomecar__(.+?)\.jpg', url)
    return m.group(1) if m else url


def parse(html):
    urls = re.findall(r'data-webp="([^"]+)"', html)
    alts = re.findall(r'data-webp="[^"]+"\s+alt="([^"]*)"', html)
    return [(u, alts[i] if i < len(alts) else "") for i, u in enumerate(urls)]


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        print("用法: python fetch_gallery.py <seriesid> <specid> <输出目录> [每套张数=10]")
        return 1
    seriesid, specid, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    per = int(sys.argv[4]) if len(sys.argv) > 4 else 10
    os.makedirs(outdir, exist_ok=True)

    seen, meta_all = set(), {}
    tmp = os.path.join(outdir, "_tmp.html")

    order = {c: i + 1 for i, (c, _) in enumerate(CATS)}
    name_of = dict(CATS)
    for catid in PROC_ORDER:
        catname = name_of[catid]
        setno = order[catid]
        picked = []
        page = 1
        while len(picked) < per and page <= 5:
            if page == 1:
                url = f"https://car.autohome.com.cn/pic/series-s{specid}/{seriesid}-{catid}.html"
            else:
                url = f"https://car.autohome.com.cn/pic/series-s{specid}/{seriesid}-{catid}-p{page}.html"
            code = curl(url, tmp, referer=f"https://car.autohome.com.cn/pic/series-s{specid}/{seriesid}.html")
            if not os.path.exists(tmp) or os.path.getsize(tmp) < 5000:
                print(f"  [{catname}] p{page} 抓取失败 HTTP={code}")
                break
            html = open(tmp, "rb").read().decode("gb18030", "ignore")
            items = parse(html)
            if not items:
                break
            for u, alt in items:
                iid = img_id(u)
                if iid in seen:
                    continue
                seen.add(iid)
                picked.append((u, alt))
                if len(picked) >= per:
                    break
            page += 1
            time.sleep(0.4)

        if not picked:
            print(f"套  [{catname}] 无可用图片，跳过")
            continue

        folder = os.path.join(outdir, f"套{setno:02d}_{catname}")
        os.makedirs(folder, exist_ok=True)
        done = []
        for i, (u, alt) in enumerate(picked, 1):
            tail = u.split("/")[-1]
            ok = False
            for pre in SIZE_PREF:
                big = tail.replace(THUMB_PREFIX, pre)
                base = u if u.startswith("http") else "https:" + u
                base = base.rsplit("/", 1)[0]
                target = f"{base}/{big}"
                fn = os.path.join(folder, f"{i:02d}.jpg")
                c = curl(target, fn, referer=url)
                if c == "200" and os.path.exists(fn) and os.path.getsize(fn) > 15000:
                    ok = True
                    done.append({"no": i, "alt": alt, "size_prefix": pre, "url": target})
                    break
            if not ok:
                print(f"     [{catname}] #{i} 下载失败 {tail[:40]}")
        meta_all[f"套{setno:02d}_{catname}"] = {
            "catid": catid, "count": len(done), "items": done}
        print(f"套  [{catname}] 下载 {len(done)}/{per} 张 -> {folder}")

    if os.path.exists(tmp):
        os.remove(tmp)
    with open(os.path.join(outdir, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"seriesid": seriesid, "specid": specid, "sets": meta_all},
                  f, ensure_ascii=False, indent=2)
    total = sum(v["count"] for v in meta_all.values())
    print(f"\n合计 {total} 张，共 {len(meta_all)} 套 -> {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
