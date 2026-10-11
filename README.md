# alpha-radar · 链上与安全情报日报

> Daily on-chain alpha + web-security intel digest. Scrapes a curated X whitelist
> (login-free), CISA KEV / GitHub Advisory / Hacker News, and market sentiment
> (CMC / OKX / Binance) into a single-page HTML report.

把「X 白名单账号 + 外部安全源 + 市场情绪」三类数据抓下来，去重过滤后生成一份**单页 HTML 日报**，并顺带导出整页 PNG，交付到桌面。

纯 Python 标准库，零第三方依赖。为 Windows 环境编写（用到 Chrome 无头截图与计划任务弹窗），核心抓取逻辑跨平台可用。

**先看效果**：`docs/sample-report.html`（2026-10-11 那期的完整成品，直接用浏览器打开）

---

## GitHub 仓库设置建议

**About / Description**（复制即用）：

```
Daily on-chain alpha + web-security intel digest. Scrapes a curated X whitelist (login-free), CISA KEV / GitHub Advisory / Hacker News, and market sentiment (CMC / OKX / Binance) into a single-page HTML report.
```

**Topics**：

```
osint  threat-intelligence  crypto  cisa-kev  market-sentiment  twitter-scraper  daily-report  python
```

**License**：MIT（见 `LICENSE`）

---

## 目录

- [它产出什么](#它产出什么)
- [快速开始](#快速开始)
- [数据源](#数据源)
- [流水线](#流水线)
- [配置](#配置)
- [目录结构](#目录结构)
- [踩坑记录](#踩坑记录)
- [免责声明](#免责声明)

---

## 它产出什么

一份 HTML 日报，结构固定：

| 区块 | 内容 |
|---|---|
| header | 标题 + 数据漏斗（抓取量 → 48h 内 → 剔除 → 进筛选 → 收录）+ 行情条 + 荧光标记图例 |
| **市场情绪总览** | ① 恐惧贪婪指数（半圆仪表盘 + 30 天柱状图）② 大盘指数（市值 / 现货成交额 / 合约成交额 / BTC·ETH 占比 / 前 20 加权）③ BTC·ETH 指数（7 天走势折线）④ 核心板块 24h 横条图 ⑤ 合约情绪与爆仓表格 ⑥ 综合判断 |
| 未来 7 天关键节点 | 由 `events.json` + `calendar-extra.json` 生成，36 小时内高影响节点置顶告警 |
| L1 必看 | 一手源原话、研究者 / 官方 / 平台级变化（≤6 条） |
| L2 AI 工具与 Agent | 只收能落地的工具实操 |
| L3 链上机会 | 空投、打新、链上 Alpha、具体标的与合约地址、风险预警 |
| L4 安全漏洞 | CISA KEV 新增表格 + GitHub Advisory + 值得看的 HN 讨论 |
| footer | 两行：收录口径 + 指向配套日志 |

**过程性内容不进成品**：剔除规则与明细、上期已收录不重复、数据源执行情况、主线复盘、数据快照，全部写到配套的 `logs/YYYY-MM-DD-剔除与执行日志.md`。成品只放可读内容。

另外可选产出：
- 同名整页 PNG（`html2png.py`，Chrome 无头两趟渲染：先量高再截图）
- 市场节点日历 `.ics`
- 季度会议日志 HTML
- Windows 计划任务：到点弹窗提醒（`build_tasks.py` + `alert.ps1`）

---

## 快速开始

```bash
git clone <this-repo> && cd alpha-radar
cp secrets.example.json secrets.json      # 全部留空也能跑

# 1. 抓 X 白名单账号（先试直连；不通再走 Clash 轮换）
python x_profile_ssr.py --direct --per-node 2 --hours 48

# 2. 抓外部安全源
python fetch_intel.py                     # CISA KEV / GitHub Advisory / HN
python fetch_hn.py                        # HN 明细（含链接）
python fetch_crypto.py                    # 币价 + 加密媒体 RSS

# 3. 抓市场情绪
python fetch_market_sentiment.py

# 4. 生成报告（examples/ 里有一份完整的成品样例可参考）
python examples/build_daily_example.py

# 5. 注入两个模块（顺序不能反）
python inject_preview.py   reports/daily-intel-YYYY-MM-DD.html
python inject_sentiment.py reports/daily-intel-YYYY-MM-DD.html

# 6. 交付到桌面 + 导出 PNG
python publish_desktop.py  reports/daily-intel-YYYY-MM-DD.html
```

> `examples/build_daily_example.py` 是一份**冻结的完整样例**（2026-10-11 那期），里面是硬编码的正文内容。
> 实际使用时，日报正文由你自己写（或交给 LLM 生成），脚本只负责数据抓取与版式渲染。

---

## 数据源

### 1. X 白名单账号（免登录）

`x_profile_ssr.py` 利用的是：**x.com 对未登录用户仍返回账号页的 SSR HTML**，其中内嵌 React Server Components 数据流，含 `full_text` + 毫秒级 `created_at_ms` + 互动数。每个账号能拿到最新 2–5 条**实时**推文。

两条通道：

| 通道 | 命令 | 说明 |
|---|---|---|
| 直连 | `--direct` | 优先试。不改变出口 IP。可用性每天变，**每次都要重新探测** |
| Clash 轮换 | 不加 `--direct` | 直连不通时用。每抓 N 个账号切一次节点换出口 IP，突破单 IP 配额 |

探测命令：

```bash
curl -s -o /dev/null -w "%{http_code}" -m 8 https://x.com/<handle>
# 200 → 直连可用；000 → 走 Clash
```

**解析器有个致命坑**（已修）：必须按 `rest_id:"<id>",result:$R[n]={` 切分，**不能**按 `entry_id:"tweet-<id>"` 切。后者在 SSR 流中出现在推文数据**之后**，会导致 id / 时间 / 正文 / 互动数整体串到下一条，**推文链接指向错误推文**。改用 `rest_id` 锚点后 48h 条数从 43 提升到 57。

解析器还会顺带抓到**引用链里的非白名单账号**（如 `@VitalikButerin`、`@MagicalTux`），这些常是一手官方源，**不要当噪音丢弃**。

### 2. 外部安全源

`fetch_intel.py` 抓三样：CISA KEV 已知被利用漏洞目录、GitHub Security Advisory、Hacker News 24h >80 分。
`fetch_hn.py` 单独跑一遍拿 HN 条目的完整链接（写 `raw/hn_detail.json`）。
`fetch_crypto.py` 抓 CoinGecko 行情 + Decrypt / Cointelegraph RSS。

### 3. 市场情绪

`fetch_market_sentiment.py` 产出 `raw/market_sentiment.json`，六块数据：

| 块 | 来源 | 需要 Key？ |
|---|---|---|
| 恐惧贪婪指数（30 天） | **CoinMarketCap 官方 Keyless** `/public-api/v3/fear-and-greed/historical` | 否 |
| 大盘（市值 / 成交额 / 占比 / 合约成交额） | **CoinMarketCap 官方 Keyless** `/public-api/v1/global-metrics/quotes/latest` | 否 |
| 核心板块 24h | CoinGecko `/coins/categories` | 否 |
| BTC / ETH 指数 + 7 天走势 | CoinGecko `market_chart` | 否 |
| 爆仓 | **OKX** `/api/v5/public/liquidation-orders`（翻页取满 24h） | 否 |
| 合约情绪 | **Binance 合约** `premiumIndex` / `openInterestHist` / `topLongShortPositionRatio` / `globalLongShortAccountRatio` / `takerlongshortRatio` | 否 |

> **全部免密钥可用。** 填了 API Key 会走更好的通道：
> - `coinmarketcap_api_key`：改走认证端点（更稳、可追踪）。免费 Basic 15,000 credits/月。
> - `coinglass_api_key`：爆仓从「OKX 单所样本」升级为「**全市场聚合**」（`open-api-v4.coinglass.com/api/futures/liquidation/coin-list`，请求头 `CG-API-KEY`）。**注意 CoinGlass 没有免费额度，最低 $29/月。**

**爆仓口径必须写明**：用 OKX 时它只覆盖一家交易所且对公开数据有抽样，**绝对金额不可与 CoinGlass 全市场口径对比**，只能看方向性（多空哪一侧被爆）。

---

## 流水线

```
                 ┌─ x_profile_ssr.py ──→ raw/x_profile_latest.json
数据抓取 ────────┼─ fetch_intel.py / fetch_hn.py / fetch_crypto.py
                 └─ fetch_market_sentiment.py ──→ raw/market_sentiment.json
                            ↓
                    过滤 / 去重 / 分层（L1–L4）
                            ↓
                  build_daily_*.py 生成 HTML
                            ↓
        inject_preview.py  → 未来 7 天关键节点
        inject_sentiment.py → 市场情绪总览
                            ↓
        publish_desktop.py → 交付目录 + 整页 PNG
                            ↓
                    present / 通知
```

**注入顺序不能反**：`inject_preview.py` 每次都把节点模块插到 `</header>` 正后方；先跑它、再跑 `inject_sentiment.py`，情绪模块才会落在节点模块**之前**。

---

## 配置

改 `config.py` 或设环境变量（前缀 `DI_`）：

| 环境变量 | 默认 | 说明 |
|---|---|---|
| `DI_PROXY` | `http://127.0.0.1:7897` | HTTP 代理，留空 = 直连 |
| `DI_CLASH_API` | `http://127.0.0.1:9097` | Clash 外部控制 API |
| `DI_CLASH_SECRET` | `set-your-secret` | Clash 外部控制的 secret |
| `DI_CLASH_GROUP` | `机场` | 策略组名（你的订阅名） |
| `DI_CLASH_NODES` | 港 / 日 / 美 四个节点 | 轮换用节点白名单，逗号分隔，**必须与订阅里的节点名完全一致** |
| `DI_DESKTOP` | `~/Desktop` | 桌面路径 |
| `DI_DELIVER_DIR` | `~/Desktop/情报收集` | 交付目录 |
| `DI_KEEP_DAYS` | `7` | 交付目录保留天数 |
| `DI_CHROME` | Chrome 默认安装路径 | 无头截图用 |
| `DI_PNG_WIDTH` / `DI_PNG_SCALE` | `1000` / `2` | PNG 宽度与缩放 |

---

## 目录结构

```
alpha-radar/
├── config.py                     # 集中配置（环境变量可覆盖）
├── secrets.example.json          # 复制为 secrets.json 填 Key
├── x_synd_fetch.py               # Clash 控制 + 白名单 + 节点轮换（被 x_profile_ssr 依赖）
├── x_profile_ssr.py              # X 账号页 SSR 抓取（免登录）
├── fetch_intel.py                # CISA KEV / GitHub Advisory / HN
├── fetch_hn.py                   # HN 明细（含链接）
├── fetch_crypto.py               # CoinGecko 行情 + 加密媒体 RSS
├── fetch_market_sentiment.py     # 恐惧贪婪 / 大盘 / 板块 / 爆仓 / 合约情绪
├── inject_preview.py             # 注入「未来 7 天关键节点」
├── inject_sentiment.py           # 注入「市场情绪总览」（内联 SVG 画图）
├── publish_desktop.py            # 交付到桌面 + 导出 PNG
├── html2png.py                   # HTML → 整页 PNG（Chrome 无头两趟）
├── tidy_desktop.py               # 过期日报归档（移动，不删除）
├── build_tasks.py                # 市场节点注册成 Windows 计划任务
├── alert.ps1                     # 到点弹窗脚本
├── build_meeting_log.py          # 季度会议日志
├── build_ics.py                  # 导出 .ics 日历
├── events.json                   # 有精确时间的市场节点
├── calendar-extra.json           # 仅日期的市场节点
├── examples/
│   ├── build_daily_example.py    # 一份完整的日报生成脚本（2026-10-11 期）
│   └── 2026-10-11-剔除与执行日志.md
└── skills/                       # 配套的 WorkBuddy / Claude Code Skill
    ├── x-following-audit/        # X 取数通道排查与画像分析
    ├── daily-report-delivery/    # 日报交付与长期维护
    └── windows-scheduled-popup-reminder/  # Windows 到点弹窗提醒
```

---

## 踩坑记录

这些坑踩过一遍就够，写下来省你时间。

### X 通道

- **直连可用性每天变。** 同一个 `curl` 探测，09-30 返回 000、10-08 返回 200。**每次都要重新探测，不能沿用上期结论。**
- **Clash 订阅会整体更换，组名与节点名都会变。** 脚本在 Clash API 阶段 traceback 时先看返回码：`404` = 组名不存在（换了机场），`400` = 节点名不在该组里。排查：
  ```bash
  curl -s -H "Authorization: Bearer <secret>" http://127.0.0.1:9097/proxies -o proxies.json
  # 读 ['proxies'][组名]['all']，与你的节点白名单求差集
  ```
- **`views` 字段格式会变。** 曾从 `views:{count:"N"}` 变为 `views:$R[n]={count:"N"}`，旧正则导致 views 全为 `None`。当前正则兼容两种形式。
- **已死的通道，别再试**：`syndication.twitter.com/srv/timeline-profile`（返回 200 但是**陈旧 embed 缓存**，实测滞后 4 天到 4 年）；Nitter 全系实例；guest token（`api.x.com/1.1/guest/activate.json` 已 404）；克隆已登录 Chrome 的 profile（Chrome 153 的 cookie 是 `v20` 前缀 App-Bound Encryption，换 `user-data-dir` 后 `auth_token` 静默解密失败）。

### 数据源

- **CoinGecko 免费档 429 限流严重。** 调用间隔要 ≥4s，且失败要**复用上一份数据**，否则整节会静默消失。
- **CoinGecko 的 `global.market_cap_change_percentage_24h_usd` 不可信。** 实测给 -2.5%，与头部币普涨矛盾。改用**前 20 大币市值加权自算**更贴合盘面。
- **CoinGlass 数据接口已需 API Key。** `open-api.coinglass.com/public/v2/*` 返回 `API key missing`；`fapi.coinglass.com/api/*` 返回 `code:0 success` 但**没有 data**。别再试免密钥路径。
- **CoinMarketCap 有官方 Keyless 通道**（`/public-api` 前缀），F&G 与全球指标都能免账号拿到。比爬它的站点内部 `data-api` 稳。

### 渲染与交付

- **Chrome 无头 CLI 的 `--screenshot` 只截视口，没有整页参数。** `html2png.py` 的做法是两趟：先注入脚本把 `scrollHeight` 写进 `title`，用 `--dump-dom` 读回来，再用这个高度截图。
- **必须带 `--user-data-dir` 指向临时目录**，否则会和用户正在跑的 Chrome 抢 profile 而失败。
- 日志里 `WSALookupServiceBegin failed with: 10108` 是无害噪音，退出码 0 即成功。
- **注入顺序不能反**（见上文流水线）。

---

## 免责声明

- 本项目只做**公开信息聚合**，不构成任何投资建议。
- 抓取行为请遵守目标站点的服务条款与当地法律法规。默认节奏已做保守设置，**不要调高并发**。
- 日报中出现的标的、合约地址、操作建议均来自公开推文与媒体转述，**未经独立核实**，据此操作风险自负。

## License

MIT
