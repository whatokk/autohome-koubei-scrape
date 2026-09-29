# -*- coding: utf-8 -*-
"""抓取一条汽车之家口碑详情页里的全部配图（原图分辨率）。

用法:
    python fetch_images.py <详情页URL> [输出目录]

示例:
    python fetch_images.py https://k.autohome.com.cn/detail/view_01kwdtrfdg6mw3ed1n6rwg0000.html

关键经验（2026-09 实测，踩过的坑）:
  1. 详情页 HTML 是 **GB2312/GBK**，不是 UTF-8。按 utf-8 解会得到 `ƦƥƤ 2026 210KMӥ500` 这种乱码。
  2. 详情页有**两种服务端形态**，同一 URL 前后两次请求可能返回不同版本：
       - 全文版（~160KB）：正文 `<div class="text-con">` 内嵌 `data-src` 图片  ← 但只是**子集**
       - 壳版（~92KB）：正文全靠 JS 渲染，HTML 里只剩侧栏 `120x90` 缩略图
     ⇒ **不要只信 HTML 里的图片**。本脚本以「列表接口 piclist」为准，HTML 图片作并集兜底。
  3. 真·全量图集在列表接口 `result.list[].piclist[]`，条数与 `photoCount` 一致。
     实测某条口碑：正文内嵌 8 张，photoCount/piclist 为 12 张 —— 漏 4 张。
  4. 图片懒加载用 `data-src`（`src` 是空的）。
  5. 文件名前缀 `800x800_1_q87_` / `480x360_0_q87_` / `120x90_c42_` 都是服务端缩略图，
     **去掉该前缀即得原图**（实测 480×360 → 1920×2560）。
"""
import os
import re
import sys
import json
import shutil
import subprocess

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
REF = "https://k.autohome.com.cn/"
LIST_API = ("https://koubeiipv6.app.autohome.com.cn/pc/spec/list"
            "?specid={specid}&pageIndex={page}&pageSize=10&order=0&ge=0"
            "&summaryKey=0&pm=1")
THUMB_PREFIX = re.compile(r"/(\d+x\d+_[a-z0-9]+_q\d+_)")


def curl(url, referer=REF, timeout=40):
    cmd = ["curl", "-4", "-sL", "-m", str(timeout), "-A", UA]
    if referer:
        cmd += ["-e", referer]
    cmd.append(url)
    return subprocess.run(cmd, capture_output=True).stdout


def decode_page(b):
    """详情页是 GBK：读页面声明的 charset，失败退 gb18030 再退 utf-8。"""
    m = re.search(rb'charset=["\']?\s*([A-Za-z0-9_-]+)', b[:2048])
    enc = m.group(1).decode("ascii", "ignore").lower() if m else ""
    for cand in ([enc] if enc else []) + ["gb18030", "utf-8"]:
        try:
            t = b.decode(cand)
            if t.count("\ufffd") < 5:
                return t
        except (UnicodeDecodeError, LookupError):
            continue
    return b.decode("gb18030", "ignore")


def orig(u):
    """把缩略图 URL 还原成原图 URL。"""
    return THUMB_PREFIX.sub("/", u if u.startswith("http") else "https:" + u)


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()


def extract_from_html(h):
    """HTML 里内嵌的配图（可能是子集）。"""
    raw = [s for s in re.findall(r'data-src="(//[^"]+)"', h) if "autoimg" in s]
    # 排除侧栏小缩略图（120x90 / 160x120 之类）
    keep = [s for s in raw if not re.search(r"/\d{2,3}x\d{2,3}_c\d+_", s)]
    seen, out = set(), []
    for u in keep:
        o = orig(u)
        if o not in seen:
            seen.add(o)
            out.append(o)
    return out


def extract_ids(h):
    """从详情页抠 specid / koubeiid（两套模板位置不同，都试）。"""
    def first(pats):
        for p in pats:
            m = re.search(p, h, re.I)
            if m:
                return m.group(1)
        return None
    specid = first([r"autohome\.com\.cn/spec/(\d+)", r"specId\D{0,8}(\d{3,8})"])
    koubeiid = first([r'hidEvalId[^>]*value=["\'](\d+)',
                      r"objectid=(\d+)",
                      r"KoubeiId[\"']?\s*[:=]\s*[\"']?(\d+)"])
    return specid, koubeiid


def fetch_piclist(specid, koubeiid, max_page=30):
    """走列表接口找这条口碑，返回它的全量图集。"""
    if not (specid and koubeiid):
        return None, None
    for page in range(1, max_page + 1):
        b = curl(LIST_API.format(specid=specid, page=page),
                 referer="https://k.autohome.com.cn/spec/%s/" % specid)
        try:
            d = json.loads(b.decode("utf-8", "ignore"))
        except Exception:
            return None, None
        r = d.get("result") or {}
        items = r.get("list") or []
        for it in items:
            if str(it.get("Koubeiid")) == str(koubeiid):
                return it, [orig(u) for u in (it.get("piclist") or [])]
        if page >= (r.get("pagecount") or 1) or not items:
            break
    return None, None


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    url = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    if not out:
        m = re.search(r"view_([0-9a-z]+)\.html", url)
        out = "koubei_images_%s" % (m.group(1) if m else "out")

    b = curl(url)
    if len(b) < 2000:
        raise SystemExit("页面抓取失败（%d 字节）" % len(b))
    h = decode_page(b)

    specid, koubeiid = extract_ids(h)
    html_imgs = extract_from_html(h)
    item, api_imgs = fetch_piclist(specid, koubeiid)

    # 并集（保序：接口优先，HTML 补充）
    seen, urls = set(), []
    for u in (api_imgs or []) + html_imgs:
        if u not in seen:
            seen.add(u)
            urls.append(u)

    def pick(p):
        m = re.search(p, h, re.S)
        return strip_tags(m.group(1)) if m else ""

    meta = {
        "source_url": url,
        "specid": specid,
        "koubeiid": koubeiid,
        "h1": pick(r"<h1[^>]*>(.*?)</h1>"),
        "page_title": pick(r"<title>(.*?)</title>"),
        "title": (item or {}).get("feeling_summary") or pick(r"《(.*?)》"),
        "username": (item or {}).get("username"),
        "posttime": (item or {}).get("posttime"),
        "photoCount": (item or {}).get("photoCount"),
        "img_from_api": len(api_imgs or []),
        "img_from_html": len(html_imgs),
        "img_count": len(urls),
    }

    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out, exist_ok=True)

    print("标题:", meta["title"])
    print("作者:", meta["username"], "| 时间:", meta["posttime"])
    print("图片: 接口 %s 张 / HTML %s 张 / 去重合计 %d 张  (photoCount=%s)"
          % (meta["img_from_api"] or "-", meta["img_from_html"],
             meta["img_count"], meta["photoCount"]))
    print("-" * 68)

    ok = 0
    for i, u in enumerate(urls, 1):
        fn = os.path.join(out, "%02d.jpg" % i)
        subprocess.run(["curl", "-4", "-s", "-m", "40", "-A", UA, "-e", REF,
                        u, "-o", fn], check=False)
        sz = os.path.getsize(fn) if os.path.exists(fn) else 0
        if sz > 5000:
            ok += 1
        print("%02d  %8d B  %s" % (i, sz, u.split("/")[-1]))

    meta["images"] = urls
    meta["downloaded"] = ok
    json.dump(meta, open(os.path.join(out, "_meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("-" * 68)
    print("完成 %d/%d 张 -> %s" % (ok, len(urls), out))
    if meta["photoCount"] and ok != meta["photoCount"]:
        print("⚠️ 下载数与 photoCount 不一致，检查是否有漏图")


if __name__ == "__main__":
    main()
