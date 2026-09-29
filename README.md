# 汽车之家口碑采集

> WorkBuddy Skill · 屋里涛说

按车型/配置抓取汽车之家口碑列表与全文，支持按口碑勋章等级筛选，导出 HTML 可视化报告 + CSV。也支持只抓某条口碑的配图。

## 技能清单

| 技能 | 说明 |
|---|---|
| **autohome-koubei-scrape** · 口碑采集 | 从 `k.autohome.com.cn` 采集。支持按勋章等级筛选（满级精华 / 精华 / 推荐），产出 HTML 报告 + CSV；或只抓单条口碑的原图批量下载 + 预览画廊。 |


## 安装

把 `skills/` 下的技能目录拷贝到 WorkBuddy 的技能目录：

```bash
cp -r skills/* ~/.workbuddy/skills/
```

Windows PowerShell：

```powershell
Copy-Item .\skills\* "$env:USERPROFILE\.workbuddy\skills\" -Recurse -Force
```

重启 WorkBuddy 后，技能列表即可看到。

## 使用要点

- 触发词：爬取汽车之家某车型的口碑、抓某车的满级精华、采集汽车之家口碑素材、爬取这条口碑里的图片、口碑图片下载。
- 脚本分工：`fetch_list.py`（列表）/ `fetch_details.py`（详情）/ `fetch_gallery.py`（配图）/ `fetch_images.py`（原图）/ `gen_report.py`（报告）/ `batch_fetch.py`（批量）/ `dump.py`（导出）。

## 环境依赖

- Python 3.13
- 网络访问

## 目录规范

```
autohome-koubei-scrape/
└── skills/
    ├── autohome-koubei-scrape/
```

每个技能遵循统一结构：`SKILL.md`（必需，含 name/description frontmatter）+ `scripts/`（可选）+ `references/`（可选）。

---

## License

MIT — 随意取用、修改、二次分发。
