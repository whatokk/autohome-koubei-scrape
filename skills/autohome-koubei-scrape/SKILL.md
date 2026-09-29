---
name: autohome-koubei-scrape
description: 汽车之家口碑采集。按车型/配置抓取汽车之家口碑列表与全文，支持按口碑勋章等级筛选（满级精华 / 精华 / 推荐），导出为 HTML 可视化报告 + CSV；也支持只抓某条口碑的配图（原图批量下载 + 预览画廊）。当用户说「爬取汽车之家某车型的口碑」「抓某车的满级精华」「采集汽车之家口碑素材」「导出汽车之家口碑」「爬取这条口碑里的图片」「口碑图片下载」时使用。
agent_created: true
---

# 汽车之家口碑采集（autohome-koubei-scrape）

## 适用场景

从 **汽车之家口碑站**（`k.autohome.com.cn`）按车型/配置采集口碑。
区别于 `koubei-links-pipeline`（懂车帝链接核实回填）、`koubei-batch-create`（按参数原创口碑）、`koubei-pipeline`（口碑改写）。

用户说「爬取 iCAR V27 2026款 200KM四驱猎鹰500 的满级精华」= 抓该配置下 `medals` 含「满级精华」的全部口碑。

## 关键事实（2026-09 实测）

### 1. 口碑等级 = 勋章（medals）

汽车之家口碑按内容质量审核分级，列表接口每条都有：

| 勋章 name | 说明（**2026-09-24 实测修正**） |
|---|---|
| 满级精华 | 最高级（`medals[].type == 1`） |
| 精华 | 次级 |
| 推荐 | 再次 |
| 无勋章 | 未达标 |

⚠️ **「满级精华 = 1500 字以上」这个说法是错的，已按实测修正。**
实测方程豹钛7 EV 675KM 后驱闪充版（specid 77686，240 条口碑 / 满级精华 60 条 / 精华 145 条）：
抽 20 条满级精华全文逐条计字数，**正文纯汉字 658–1797 字，中位 884，平均 992**——
658 字的照样是满级精华。**评级看的是真实度、维度完整度与图文质量，不是字数门槛**，不要再用字数反推等级，一切以接口返回的 `medals` 为准。

PC 页面上的图标与静态文件名对应：`mjjh.png`=满级精华、`jh.png`=精华、`level2/level3.png`=等级。
**口碑列表页没有按等级筛选的 UI**，必须走接口自行过滤 `medals`。

**另一个实测坑（2026-09-24）**：**列表接口会返回重复条目**——同一 specid 的 60 条满级精华按 Koubeiid 去重后只剩 51 条唯一（约 15% 重复）。翻页抓完后必须 `Koubeiid` 去重，否则样本数虚高、统计口径失真。

### 2. 定位 seriesid / specid

```bash
curl -4 -s "https://k.autohome.com.cn/<seriesid>/" -o page.html
```
页面内嵌 `__NEXT_DATA__`，取 `props.pageProps.baseData`：
- `specgroup[].speclist[]` → `{specid, specname, koubeicount}`（各配置的口碑数）
- `seriesname`、`pricerange` 等

不知道 seriesid 时先 WebSearch「<车型> 汽车之家 口碑」，命中 `k.autohome.com.cn/<数字>/` 即 seriesid。

### 3. 口碑列表接口（核心）

```
https://koubeiipv6.app.autohome.com.cn/pc/spec/list
  ?specid=<specid>&pageIndex=<n>&pageSize=10&order=0&ge=0&summaryKey=0&pm=1
```

- 必须带 `Referer: https://k.autohome.com.cn/spec/<specid>/`，否则可能被拦
- **`pageSize` 被服务端忽略，恒定返回 10 条**；翻页按 `result.pagecount`（= `rowcount` / 10）
- 返回 `result.list[]`，每条关键字段：
  - `Koubeiid` — 口碑 ID（拼详情页 URL 用）
  - `feeling_summary` — 标题（这就是列表页显示的口碑标题）
  - `username` / `userid` / `posttime`
  - `medals[]` — 勋章，`[{type, name}]`
  - `scoreList[]` — 各维度评分 `[{name, value}]`（综合分 = 平均，列表页显示两位小数）
  - `distance` 行驶里程 / `buyprice` 裸车价 / `buyplace` 购买地点 / `boughtDate` 购买时间
  - `actual_oil_consumption` / `actual_battery_consumption` / `summerRange|springRange|winterRange`
  - `photoCount` / `viewcount` / `helpfulcount` / `commentcount` / `piclist[]`
  - `contents[]` — 各维度正文，**但是被截断的**（结尾带 `...`），要全文必须抓详情页

### 4. 详情页全文

```
https://k.autohome.com.cn/spec/<specid>/view_<Koubeiid>_1.html
```
返回 **301**，跟随跳转到 `https://k.autohome.com.cn/detail/view_<base36id>.html`（服务端渲染，curl 直接可读）。
**不要**直接用 `detail/view_<纯数字>.html`（404）。

正文用**结构化解析**（比纯文本行切分稳得多），每个维度是：

```html
<div class="space kb-item">
    <h1>空间 <div class="athm-star">…</div> <span class="star-num">5</span></h1>
    <p class="kb-item-msg">正文…</p>
</div>
```

算法：`re.finditer(r'<div class="space kb-item"', html)` 切开每块 → 块内取 `<h1>` 文本（去标签、去掉尾部数字）当维度名，`<span class="star-num">` 当维度评分，`<p class="kb-item-msg">` 当正文。
⚠️ **不要**用「逐行文本 + 维度词匹配」的土办法：页面顶部摘要卡片里也有「空间 5 / 驾驶感受 5」这类评分行，会把噪声混进正文。

### 5. 口碑配图采集

**只抓图、不抓文**时（「爬取这条口碑里的图片」），**不要只解析 HTML** —— 已验证会漏图。

⚠️ **两个必踩的坑（2026-09 实测）**：

1. **详情页有两种服务端形态，同一 URL 前后两次请求可能返回不同版本**：

   | 形态 | 体积 | 特征 | HTML 里有图吗 |
   |---|---|---|---|
   | 全文版 | ~160KB | 正文在 `<div class="text-con">` | 有，但**只是子集** |
   | 壳版 | ~92KB | 正文全靠 JS 渲染 | 只剩侧栏 `120x90` 缩略图 |

   实测同一条口碑：全文版 HTML 内嵌 **8 张**，壳版 **0 张**，
   而 `photoCount` / `piclist` 是 **12 张** —— 只解析 HTML 会漏 4 张。

2. **真·全量图集在列表接口的 `piclist[]`**，条数与 `photoCount` 一致。**这是唯一可信来源。**

正确流程：
```
抓详情页(GBK) → 正则抠 specid / koubeiid → 列表接口翻页定位该条 → 取 piclist → 去缩略图前缀下原图
```
- `specid`：页面里 `//www.autohome.com.cn/spec/(\d+)/`（壳版/全文版都有）。
- `koubeiid`：`<input id="hidEvalId" value="5874569">`，或反馈链接里的 `objectid=(\d+)`。
- 没有找到「按 koubeiid 直查」的接口（`/pc/koubei/detail` 等均 404），只能靠列表接口定位。
- 拿不到 ID 时再退回解析 HTML 的 `data-src`，但要提示用户可能不全。

图片 URL 规律：
- 懒加载用 **`data-src`**（`src` 是空的），在 `<div class="image status1"><img data-src="…">` 里。
- 形如 `//k2.autoimg.cn/koubeidfs/g34/M04/FB/D9/800x800_1_q87_autohomecar__xxx.jpg`；
  `800x800_1_q87_` / `480x360_0_q87_` / `120x90_c42_` 都是服务端缩略图前缀，
  **去掉该前缀即得原图**（实测 480×360 → 1920×2560，体积 ×5）。
- 侧栏「相关口碑」缩略图会混进来，特征是小尺寸 + `_c\d+_`（如 `120x90_c42_`），要过滤掉。
- 下载：`curl -4 -s -A "Mozilla/5.0" -e "https://k.autohome.com.cn/" <url> -o NN.jpg`。

产物：`NN_视角描述.jpg` + `_meta.json`（含 source_url / koubeiid / 作者 / 图集原链）+ 单文件 base64 预览画廊 HTML + zip。
口碑配图基本都是手机随手拍（1440×1080 / 1920×1440 / 1920×2560 混排），
内饰角度、车漆颜色、细节特写往往比官网图更真实，适合补进车型素材库。

**已封装脚本**：`scripts/fetch_images.py`
```bash
python fetch_images.py <详情页URL> [输出目录]
```

### 6. 车型图库采集（按分类成套抓，2026-09-24 新增）

用户说「去汽车之家找这个车型的 6 套图，一共 60 张」= 抓**车型图库**（`car.autohome.com.cn/pic/`），不是口碑配图。图库天然分 6 类，每类取 10 张即 60 张。

**URL 结构**（关键：`-s<specid>` 前缀 = 只抓该配置的图）
```
https://car.autohome.com.cn/pic/series-s<specid>/<seriesid>-<catid>.html      # 第1页
https://car.autohome.com.cn/pic/series-s<specid>/<seriesid>-<catid>-p2.html   # 第2页
```

6 个 catid（顺序即「套」的编号）：

| catid | 分类 | catid | 分类 |
|---|---|---|---|
| 1 | 车身外观 | 12 | 其它细节 |
| 10 | 中控方向盘 | 53 | 官图 |
| 3 | 车厢座椅 | 55 | 车展 |

**三个必踩的坑**：
1. **图片不在 `src` 里**，而在 `<img ... data-webp="//carX.autoimg.cn/cardfs/product/.../480x360_0_q95_c42_autohomecar__xxx.jpg">`。用 `data-src`/`src` 正则会得到 0 张。
2. **页面是 GBK**，必须 `decode("gb18030")`，否则分类名和 alt 全是乱码。
3. **尺寸靠改文件名前缀**（同一张图换前缀即得不同尺寸，实测同一 ID）：

   | 前缀 | 实得尺寸 |
   |---|---|
   | `480x360_0_q95_c42_` | 480×360（列表缩略图） |
   | `1024x0_1_q95_` | 1024×768 |
   | `1600x0_1_q95_` | 1600×1200 |
   | **`1920x0_1_q95_`** | **1920×1440（最大，优先）** |

4. **官图(catid=53) 会 302 回落地页**，但落地页仍含该配置的官图，可照抓。
5. **抓取顺序要把「官图」放最前** —— 官图与车身外观/内饰的官方图重合度高，若先抓外观，官图会被去重挤到只剩 8 张（实测）。先抓官图，外观有 36 张的余量，两边都能凑满 10。

**已封装脚本**：`scripts/fetch_gallery.py`
```bash
python fetch_gallery.py <seriesid> <specid> <输出目录> [每套张数=10]
# 例：方程豹钛7 EV 675KM 后驱闪充版 → seriesid=8171, specid=77686
python fetch_gallery.py 8171 77686 "D:/项目/汽车之家/方程豹钛7EV675_图库60张" 10
```
产出：`套01_车身外观/` … `套06_车展/`（每套 10 张，1920×1440）、`_meta.json`（含每张的原图 URL 与所用尺寸前缀）。

**怎么拿 specid**：分类页 HTML 里有配置切换列表 `href="/pic/series-s77686/8171-1.html" ... EV 675KM 后驱闪充版(36张)`，`s(\d+)` 即 specid。
（注意：这里的 specid 与口碑站的 specid 是同一套体系吗？——**不是每车型都一致，图库页里读到的最可靠，别猜。**）

**交付配套**：另生成单文件 `图库预览.html`（6 分段缩略图 + 点开原图 + 每张外链源页），方便用户挑图。

## 两类口碑必须区分（业务上很关键）

| 类型 | 维度名 | 含义 |
|---|---|---|
| **车主口碑** | 最满意 / 最不满意 / 空间 / 驾驶感受 / 续航 / 外观 / 内饰 / 性价比 / 智能化 | 真实提车车主写的 |
| **探店口碑** | 新车好评 / 新车槽点 / 空间 / … | 经销商试驾、探店体验，**不是车主** |

判定：维度里出现「新车好评 / 新车槽点 / 好评 / 槽点」→ 探店口碑。
实测某些车型的「满级精华」里探店口碑占比极高（iCAR V27 2026款 200KM四驱猎鹰500：204 篇中 185 篇探店、仅 19 篇车主），
交付时必须把这一构成告诉用户，否则会把经销商试驾稿当车主反馈用。

## 环境坑位

1. **`koubeiipv6.app.autohome.com.cn` 是 IPv6 优先域名** —— Python `urllib` 直连会 `SSL handshake timed out`。用 `curl -4`（强制 IPv4）或浏览器网络栈。
2. **Git Bash 下 `chrome --dump-dom > file` 会得到 0 字节**，必须用 Python `subprocess.run(capture_output=True)` 捕获后写文件。
3. **编码：列表接口返回 JSON（UTF-8）；详情页 HTML 是 GB2312/GBK，不是 UTF-8。**
   2026-09 实测：按 `utf-8, ignore` 解详情页会把中文整段吞掉，只剩 `ƦƥƤ 2026 210KMӥ500` 这种乱码。
   `fetch_details.py` 的 `decode_page()` 已按「读页面 charset → gb18030 → utf-8」兜底，不要改回硬编码。
4. 抓取节奏：串行 + `sleep 0.3~0.6`，200 篇约 5-8 分钟，无封禁。
5. 详情页入口 URL 用 `spec/<specid>/view_<id>_1.html` 即可，**不要**用 `detail/view_<纯数字>.html`（404）。
6. **详情页有两套模板，DOM 不一样，别硬套一套选择器：**
   - A 套（`spec/…/view_…_1.html`）：正文在 `<div class="space kb-item">` 里，含 `<h1>维度名<span class="star-num">分</span></h1>` + `<p class="kb-item-msg">`。
   - B 套（`detail/view_<base36>.html`，即用户在 App/分享里复制的那种链接）：正文在单个 `<div class="text-con">` 里，
     维度用 **`【最满意】`/`【最不满意】`/`【空间】` 全角括号** 就地分行，**没有 kb-item / star-num**。
     → 解析 B 套要按 `【(.+?)】` 切段，评分另从页面上的 `<dl class="choose-dl"><dt>空间</dt><dd>…<span class="testfont">4</span>` 取。
7. **正文存在字体反爬（PUA 码位）**：详情页里部分常用汉字被替换成 `<span style='font-family:myfont'>&#xed88;</span>` 这类私用区实体，
   靠自定义字体 `myfont` 还原显示。`&#xed88;`≈的、`&#xedc0;`≈外、`&#xeda4;`≈较、`&#xecfb;`≈自、`&#xed0d;`≈侧、`&#xed0b;`≈近、`&#xecf1;`≈副、`&#xec48;`≈点、`&#xedd0;`≈足。
   **直接抓 HTML 得到的正文会缺字**。要全文无损需下载 `myfont` 字体并按字形/坐标建映射表；
   若只做素材提炼/统计，缺几个虚词通常可接受，但**不要**直接把带 `&#xed..;` 的文本当成品交付。

## 标准产物

1. `data/raw/spec_<specid>_raw.json` — 列表全量原始数据
2. `data/<等级>_full.json` — 筛选后 + 详情页全文
3. `output/<车型>_<等级>口碑.html` — 单文件可视化报告（统计卡 + 维度均分条形图 + 样本画像 + 搜索/排序/评分筛选 + 分页 + 可展开全文卡片 + 原文外链）
4. `output/<车型>_<等级>口碑.csv` — UTF-8-BOM，Excel 直接打开，含各维度分列

## 复用脚本

见本 skill `scripts/`：
- `fetch_list.py` — 列表全量抓取（curl -4 分页）+ 勋章分布统计
- `fetch_details.py` — 详情页抓取 + 正文分段解析
- `batch_fetch.py` — 按勋章筛选后批量抓全文并落盘
- `gen_report.py` — 生成 HTML 报告 + CSV
- `fetch_images.py` — **单条口碑配图采集**（接口 piclist 优先 + HTML 兜底，下载原图）

调用：`python fetch_list.py <specid> 10 data/raw`
