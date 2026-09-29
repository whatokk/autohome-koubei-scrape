# -*- coding: utf-8 -*-
"""生成满级精华口碑的 HTML 可视化报告 + CSV 数据表"""
import json, os, csv, sys
from collections import Counter

SPEC = "iCAR V27 2026款 200KM四驱猎鹰500"
SRC = "data/mjjh_full.json"
HTML_OUT = "output/iCAR_V27_满级精华口碑.html"
CSV_OUT = "output/iCAR_V27_满级精华口碑.csv"

DIM_ORDER = ["最满意", "最不满意", "新车好评", "新车槽点", "购车经历", "提车价格",
             "空间", "驾驶感受", "续航", "外观", "内饰", "性价比", "智能化"]

HTML_TPL = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>__TITLE__</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{--bg:#f5f6f8;--card:#fff;--line:#e6e8ec;--txt:#1a1d21;--sub:#6b7280;--accent:#c8102e;--accent2:#1f6feb;--soft:#fafbfc}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);font:14px/1.7 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 60px}
h1{font-size:24px;margin:0 0 6px}
.sub{color:var(--sub);font-size:13px;margin-bottom:22px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:24px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.stat b{display:block;font-size:22px;line-height:1.3}
.stat span{color:var(--sub);font-size:12px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin-bottom:22px}
.panel h2{font-size:15px;margin:0 0 12px}
.bars{display:flex;flex-direction:column;gap:7px}
.bar{display:grid;grid-template-columns:78px 1fr 46px;align-items:center;gap:10px;font-size:13px}
.bar .track{height:9px;background:#eef0f3;border-radius:5px;overflow:hidden}
.bar .fill{height:100%;background:linear-gradient(90deg,#f0a5b0,var(--accent));border-radius:5px}
.bar .v{text-align:right;color:var(--sub)}
.tools{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px;position:sticky;top:0;background:var(--bg);padding:10px 0;z-index:9}
.tools input,.tools select{padding:9px 12px;border:1px solid var(--line);border-radius:9px;font-size:13px;background:#fff}
.tools input{flex:1;min-width:220px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:0;margin-bottom:14px;overflow:hidden}
.card>summary{cursor:pointer;padding:14px 18px;list-style:none;display:flex;gap:12px;align-items:flex-start}
.card>summary::-webkit-details-marker{display:none}
.idx{flex:0 0 34px;height:34px;border-radius:9px;background:var(--soft);border:1px solid var(--line);display:flex;align-items:center;justify-content:center;font-weight:600;color:var(--accent)}
.head{flex:1;min-width:0}
.title{font-weight:600;font-size:15px;margin-bottom:4px}
.meta{color:var(--sub);font-size:12.5px;display:flex;gap:14px;flex-wrap:wrap}
.badge{display:inline-block;background:#fdeef0;color:var(--accent);border:1px solid #f6d3d8;border-radius:999px;padding:1px 9px;font-size:11.5px;margin-left:6px}
.badge.t2{background:#eef4ff;color:var(--accent2);border-color:#cfe0ff}
.score{flex:0 0 auto;text-align:right}
.score b{font-size:19px;color:var(--accent)}
.score span{display:block;color:var(--sub);font-size:11px}
.body{padding:0 18px 18px;border-top:1px dashed var(--line);margin-top:4px}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:14px 0}
.kv div{background:var(--soft);border:1px solid var(--line);border-radius:8px;padding:7px 10px;font-size:12.5px}
.kv em{font-style:normal;color:var(--sub);display:block;font-size:11.5px}
.sec{margin:14px 0}
.sec h4{margin:0 0 5px;font-size:13px;color:var(--accent2)}
.sec p{margin:0;font-size:13.5px;color:#2b3038;white-space:pre-wrap}
.dims{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}
.dims span{background:var(--soft);border:1px solid var(--line);border-radius:6px;padding:2px 8px;font-size:12px;color:var(--sub)}
.dims b{color:var(--txt)}
a.src{color:var(--accent2);text-decoration:none;font-size:12.5px}
.pager{display:flex;gap:8px;align-items:center;justify-content:center;margin:22px 0 6px}
.pager button{padding:8px 14px;border:1px solid var(--line);background:#fff;border-radius:8px;cursor:pointer}
.pager button:disabled{opacity:.4;cursor:default}
#list{min-height:200px}
.empty{text-align:center;color:var(--sub);padding:40px}
</style>
</head>
<body>
<div class="wrap">
  <h1>__TITLE__</h1>
  <div class="sub">数据来源：汽车之家口碑（k.autohome.com.cn）· 采集时间 __NOW__ · 共 <b id="n"></b> 篇「满级精华」口碑</div>

  <div class="stats" id="stats"></div>

  <div class="panel">
    <h2>各维度平均分</h2>
    <div class="bars" id="dimBars"></div>
  </div>

  <div class="panel">
    <h2>样本画像</h2>
    <div class="bars" id="extra"></div>
  </div>

  <div class="tools">
    <input id="q" placeholder="搜索：标题 / 作者 / 正文关键词 / 地点（如 露营、风噪、合肥）">
    <select id="sort">
      <option value="seq">按序号</option>
      <option value="score">按评分从高到低</option>
      <option value="score_asc">按评分从低到高</option>
      <option value="time">按发布时间从新到旧</option>
      <option value="helpful">按有用数</option>
    </select>
    <select id="rating">
      <option value="">全部评分</option>
      <option value="5">5.00</option>
      <option value="4.8">≥4.80</option>
      <option value="4.5">≥4.50</option>
      <option value="4.2">≥4.20</option>
    </select>
    <select id="ktype">
      <option value="">全部类型</option>
      <option value="车主">车主口碑</option>
      <option value="探店">探店口碑</option>
    </select>
  </div>

  <div id="list"></div>
  <div class="pager">
    <button id="prev">上一页</button>
    <span id="pageInfo" class="sub"></span>
    <button id="next">下一页</button>
  </div>
</div>

<script>
const DATA = __DATA__;
const DIM_ORDER = __DIMORDER__;
let page = 1, PER = 20, view = [];
const $ = s => document.querySelector(s);

function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}

function renderStats(){
  const n = DATA.length;
  const avg = (DATA.reduce((a,b)=>a+(b.score||0),0)/n).toFixed(2);
  const words = DATA.map(d=>d.words||0).sort((a,b)=>b-a);
  const median = words[Math.floor(words.length/2)];
  const pictures = DATA.reduce((a,b)=>a+(b.photoCount||0),0);
  const owner = DATA.filter(d=>d.ktype!=='探店').length;
  const s = [
    ['满级精华口碑', n + ' 篇'],
    ['车主口碑 / 探店口碑', owner + ' / ' + (n-owner)],
    ['平均综合评分', avg + ' 分'],
    ['正文字数中位数', median + ' 字'],
    ['累计配图', pictures + ' 张'],
  ];
  $('#stats').innerHTML = s.map(([k,v])=>`<div class="stat"><b>${v}</b><span>${k}</span></div>`).join('');
  $('#n').textContent = n;
}

function renderDims(){
  const agg = {};
  DATA.forEach(d=>{
    Object.entries(d.scoreMap||{}).forEach(([k,v])=>{
      if(v==null) return;
      agg[k] = agg[k] || {sum:0,c:0};
      agg[k].sum += v; agg[k].c++;
    });
  });
  const rows = Object.entries(agg).map(([k,o])=>[k, o.sum/o.c]).sort((a,b)=>b[1]-a[1]);
  $('#dimBars').innerHTML = rows.map(([k,v])=>
    `<div class="bar"><span>${esc(k)}</span><div class="track"><div class="fill" style="width:${v/5*100}%"></div></div><span class="v">${v.toFixed(2)}</span></div>`
  ).join('');
}

function counter(key){
  const m = {};
  DATA.forEach(d=>{ const v = d[key]; if(v!=null && v!=='') m[v]=(m[v]||0)+1; });
  return Object.entries(m).sort((a,b)=>b[1]-a[1]).slice(0,6);
}

function renderExtra(){
  const blocks = [];
  const push = (label, arr, unit)=>{
    if(!arr.length) return;
    const max = Math.max(...arr.map(x=>x[1]));
    blocks.push(`<div class="bar" style="grid-template-columns:1fr 60px;font-weight:600">${label}</div>`);
    arr.forEach(([k,v])=>blocks.push(
      `<div class="bar"><span title="${esc(k)}" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(k)}</span>
       <div class="track"><div class="fill" style="width:${v/max*100}%"></div></div><span class="v">${v}${unit||''}</span></div>`));
  };
  const seg = (fn, order)=>{
    const m = {};
    DATA.forEach(d=>{ const s = fn(d); if(s) m[s]=(m[s]||0)+1; });
    return Object.entries(m).sort((a,b)=>order.indexOf(a[0])-order.indexOf(b[0]));
  };
  // 裸车价区间
  push('裸车价区间分布', seg(d=>{
    const m = /([\d.]+)万/.exec(d.buyprice||'');
    if(!m) return null;
    const p = parseFloat(m[1]);
    return p<17?'<17万':p<17.5?'17-17.5万':p<18?'17.5-18万':p<18.5?'18-18.5万':p<19?'18.5-19万':'≥19万';
  }, ['<17万','17-17.5万','17.5-18万','18-18.5万','18.5-19万','≥19万']), ' 篇');
  // 车主地区 TOP
  push('车主地区 TOP', counter('buyplace'), ' 篇');
  // 行驶里程段
  push('行驶里程分布', seg(d=>{
    const m = /([\d.]+)/.exec((d.distance||'').replace(/,/g,''));
    if(!m) return null;
    const km = parseFloat(m[1]);
    return km<1000?'<1000km':km<3000?'1000-3000km':km<10000?'3000-1万km':km<30000?'1-3万km':'≥3万km';
  }, ['<1000km','1000-3000km','3000-1万km','1-3万km','≥3万km']), ' 篇');
  $('#extra').innerHTML = blocks.join('');
}

function applyFilter(){
  const q = $('#q').value.trim().toLowerCase();
  const s = $('#sort').value, r = $('#rating').value, kt = $('#ktype').value;
  let arr = DATA.filter(d=>{
    if(r && (d.score||0) < parseFloat(r)) return false;
    if(kt && (d.ktype||'车主') !== kt) return false;
    if(!q) return true;
    const hay = [d.title,d.username,d.buyplace,d.boughtDate,
      ...Object.values(d.sections||{}), d.append].join(' ').toLowerCase();
    return hay.includes(q);
  });
  if(s==='score') arr.sort((a,b)=>(b.score||0)-(a.score||0));
  if(s==='score_asc') arr.sort((a,b)=>(a.score||0)-(b.score||0));
  if(s==='time') arr.sort((a,b)=>(b.posttime||'').localeCompare(a.posttime||''));
  if(s==='helpful') arr.sort((a,b)=>(b.helpfulcount||0)-(a.helpfulcount||0));
  if(s==='seq') arr.sort((a,b)=>a.seq-b.seq);
  view = arr; page = 1; renderList();
}

function renderList(){
  const pages = Math.max(1, Math.ceil(view.length/PER));
  if(page>pages) page = pages;
  const slice = view.slice((page-1)*PER, page*PER);
  if(!slice.length){ $('#list').innerHTML = '<div class="empty">没有匹配的口碑</div>'; }
  else $('#list').innerHTML = slice.map(d=>card(d)).join('');
  $('#pageInfo').textContent = `第 ${page} / ${pages} 页 · 共 ${view.length} 篇`;
  $('#prev').disabled = page<=1; $('#next').disabled = page>=pages;
}

function card(d){
  const kv = [
    ['行驶里程', d.distance], ['百公里油耗', d.oil && d.oil!=='0.0' ? d.oil+'L' : null],
    ['纯电续航', d.range], ['裸车购买价', d.buyprice],
    ['购车地点', d.buyplace], ['购买时间', d.boughtDate],
    ['拥车时长', d.carOwnershipPeriod], ['配图', d.photoCount ? d.photoCount+' 张' : null],
    ['浏览 / 有用', (d.viewcount||0)+' / '+(d.helpfulcount||0)]
  ].filter(x=>x[1]);
  const dims = Object.entries(d.scoreMap||{}).filter(([k,v])=>v!=null)
    .map(([k,v])=>`<span>${esc(k)} <b>${v}</b></span>`).join('');
  const secs = DIM_ORDER.filter(k=>(d.sections||{})[k]).map(k=>
    `<div class="sec"><h4>${esc(k)}</h4><p>${esc(d.sections[k])}</p></div>`).join('');
  const ap = d.append ? `<div class="sec"><h4>追加口碑</h4><p>${esc(d.append)}</p></div>` : '';
  return `<details class="card">
    <summary>
      <div class="idx">${d.seq}</div>
      <div class="head">
        <div class="title">${esc(d.title)||'（无标题）'}<span class="badge">满级精华</span><span class="badge t2">${d.ktype==='探店'?'探店':'车主'}</span></div>
        <div class="meta"><span>${esc(d.username)}</span><span>${esc(d.posttime)}</span>
        <span>${esc(d.specname||'')}</span></div>
      </div>
      <div class="score"><b>${d.score!=null?d.score.toFixed(2):'—'}</b><span>综合评分</span></div>
    </summary>
    <div class="body">
      <div class="kv">${kv.map(([k,v])=>`<div><em>${k}</em>${esc(String(v))}</div>`).join('')}</div>
      ${dims?`<div class="dims">${dims}</div>`:''}
      ${secs}${ap}
      <div style="margin-top:12px"><a class="src" href="${esc(d.url)}" target="_blank">查看汽车之家原口碑 ↗</a></div>
    </div>
  </details>`;
}

document.addEventListener('input', e=>{ if(e.target.id==='q') applyFilter(); });
$('#sort').onchange = applyFilter; $('#rating').onchange = applyFilter; $('#ktype').onchange = applyFilter;
$('#prev').onclick = ()=>{ page--; renderList(); scrollTo({top:0,behavior:'smooth'}); };
$('#next').onclick = ()=>{ page++; renderList(); scrollTo({top:0,behavior:'smooth'}); };

try{ renderStats(); renderDims(); renderExtra(); applyFilter(); }
catch(e){ $('#list').innerHTML = '<pre style="color:red;white-space:pre-wrap">JS ERROR: '+esc(String(e.stack||e.message))+'</pre>'; }
</script>
</body>
</html>
"""


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    for d in data:
        # 维度评分：优先详情页提取的 scores，回退列表接口 scoreList
        sm = {}
        for k, v in (d.get("scores") or {}).items():
            try:
                sm[k] = float(v)
            except Exception:
                pass
        if not sm:
            for s in (d.get("scoreList") or []):
                try:
                    sm[s["name"]] = float(s["value"])
                except Exception:
                    pass
        d["scoreMap"] = sm
        txt = "".join((d.get("sections") or {}).values()) + (d.get("append") or "")
        d["words"] = len(txt)
        d["specname"] = d.get("specname") or "2026款 200KM四驱猎鹰500"
    os.makedirs("output", exist_ok=True)

    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = (HTML_TPL.replace("__DATA__", payload)
            .replace("__DIMORDER__", json.dumps(DIM_ORDER, ensure_ascii=False))
            .replace("__TITLE__", SPEC + " · 汽车之家「满级精华」口碑采集")
            .replace("__NOW__", now))
    open(HTML_OUT, "w", encoding="utf-8").write(html)

    # CSV
    cols = ["序号", "标题", "口碑类型", "作者", "发布时间", "综合评分", "行驶里程", "百公里油耗",
            "纯电续航", "裸车价", "购车地点", "购买时间", "拥车时长", "图片数", "浏览数", "有用数", "口碑链接"] \
        + DIM_ORDER + ["追加口碑"]
    with open(CSV_OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for d in data:
            sec = d.get("sections") or {}
            row = [d["seq"], d.get("title"), d.get("ktype", "车主"), d.get("username"), d.get("posttime"), d.get("score"),
                   d.get("distance"), d.get("oil"), d.get("range"), d.get("buyprice"),
                   d.get("buyplace"), d.get("boughtDate"), d.get("carOwnershipPeriod"),
                   d.get("photoCount"), d.get("viewcount"), d.get("helpfulcount"), d.get("url")]
            row += [sec.get(k, "") for k in DIM_ORDER]
            row.append(d.get("append", ""))
            w.writerow(row)

    print("HTML:", HTML_OUT, os.path.getsize(HTML_OUT), "bytes")
    print("CSV :", CSV_OUT, os.path.getsize(CSV_OUT), "bytes")
    print("记录数:", len(data), "成功抓全文:", sum(1 for d in data if d.get("ok")))


if __name__ == "__main__":
    main()
