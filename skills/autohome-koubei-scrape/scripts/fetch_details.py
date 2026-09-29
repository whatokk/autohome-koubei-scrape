# -*- coding: utf-8 -*-
"""抓取汽车之家口碑详情页全文（结构化解析 kb-item 块）。

入口 URL: https://k.autohome.com.cn/spec/<specid>/view_<Koubeiid>_1.html  -> 301 -> detail/view_xxx.html
正文结构:
    <div class="space kb-item">
        <h1>空间 <div class="athm-star">…</div> <span class="star-num">5</span></h1>
        <p class="kb-item-msg">正文…</p>
    </div>
"""
import subprocess, json, re, time, os, sys, html as htmllib

SPECID = "76415"
REF = "https://k.autohome.com.cn/spec/%s/" % SPECID
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

STOP_MARKS = ["上述内容的版权归发帖人和汽车之家所有", "举报", "分享到：",
              "同车系车主口碑", "相关车系推荐", "意见反馈", "返回顶部"]


def decode_page(b):
    """详情页是 GB2312/GBK —— 直接按 utf-8 解会得到乱码（中文全丢）。
    优先读页面声明的 charset，失败则退到 gb18030（GBK 超集）。"""
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


def curl(url):
    cmd = ["curl", "-4", "-sL", "-m", "40",
           "-H", "Referer: " + REF,
           "-H", "User-Agent: " + UA,
           "-H", "Accept-Language: zh-CN,zh;q=0.9",
           url]
    return subprocess.run(cmd, capture_output=True).stdout


def strip_tags(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"</p>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = htmllib.unescape(s)
    lines = [" ".join(l.split()) for l in s.split("\n")]
    return "\n".join(l for l in lines if l).strip()


def parse_detail(html_bytes):
    """返回 {sections: {维度: 正文}, scores: {维度: 分}, append: 追加口碑}"""
    t = decode_page(html_bytes)
    t = re.sub(r"<script.*?</script>", "", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", "", t, flags=re.S)

    idx = [m.start() for m in re.finditer(r'<div class="space kb-item"', t)]
    sections, scores = {}, {}
    for a, b in zip(idx, idx[1:] + [len(t)]):
        seg = t[a:b]
        h = re.search(r"<h1[^>]*>(.*?)</h1>", seg, re.S)
        if not h:
            continue
        head_raw = h.group(1)
        star = re.search(r'star-num[^>]*>\s*([\d.]+)', head_raw)
        name = strip_tags(head_raw)
        name = re.sub(r"\s*\d+(\.\d+)?\s*$", "", name).strip()
        msgs = re.findall(r'<p class="kb-item-msg"[^>]*>(.*?)</p>', seg, re.S)
        if not msgs:
            # 兜底：去掉 h1 后的其余文本
            rest = seg.replace(h.group(0), "")
            text = strip_tags(rest)
        else:
            text = "\n".join(strip_tags(m) for m in msgs)
        text = text.strip()
        if name and text:
            if name in sections:          # 同名维度合并（如追加口碑里的再次出现）
                sections[name] += "\n" + text
            else:
                sections[name] = text
            if star:
                scores[name] = star.group(1)

    # 追加口碑 / 正文尾段（若有独立标记）
    full = strip_tags(t)
    append = ""
    m = re.search(r"购车\d+个?月后追加口碑[^\n]*", full)
    if m:
        tail = full[m.start():]
        ends = [tail.find(s) for s in STOP_MARKS if tail.find(s) > 0]
        append = tail[:min(ends) if ends else len(tail)].strip()
    return {"sections": sections, "scores": scores, "append": append}


def to_lines(html_bytes):
    t = decode_page(html_bytes)
    t = re.sub(r"<script.*?</script>", "", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"<[^>]+>", "\n", t)
    t = htmllib.unescape(t)
    return [l.strip() for l in t.split("\n") if l.strip()]


def fetch_one(koubeiid):
    url = "https://k.autohome.com.cn/spec/%s/view_%s_1.html" % (SPECID, koubeiid)
    b = curl(url)
    if len(b) < 20000:
        return None
    return parse_detail(b)


if __name__ == "__main__":
    raw = json.load(open("data/raw/spec_%s_raw.json" % SPECID, encoding="utf-8"))
    mjjh = [x for x in raw if any((m or {}).get("name") == "满级精华" for m in (x.get("medals") or []))]
    n = int(sys.argv[1]) if len(sys.argv) > 1 else len(mjjh)
    print("满级精华总数", len(mjjh), "本次抓取", n)
    for it in mjjh[:n]:
        d = fetch_one(it["Koubeiid"])
        print("---", it["Koubeiid"], it.get("username"), it.get("posttime"))
        if not d:
            print("   FAIL")
            continue
        print("   维度:", list(d["sections"].keys()), "评分:", d["scores"])
        for k, v in d["sections"].items():
            print("   [%s] %s" % (k, v[:80]))
        time.sleep(0.4)
