---
name: daily-report-delivery
description: 把自动化生成的日报/周报/日历交付到桌面并长期维护——命名策略（固定名 / 带日期 / 带周期）、publish 脚本、多步收尾顺序、md→HTML 脚本化渲染、HTML 片段幂等注入、密排速览体版式、浏览器端实时计算相对时间、过期文件自动归档、带日期文件的健康检查。适用于"每天生成一份报告放桌面""把 md 渲染成网页""报告越堆越多要归档""报告样式每天都不一样"这类请求。触发词：日报交付、桌面成品、报告自动化、md 转 HTML、速览体、报告命名规则、桌面整理、报告归档、publish 脚本、自动化 prompt。
agent_created: true
---

# 报告交付到桌面

把「模型生成的报告」变成「用户每天双击就能看、且不会越堆越乱」的成品。核心原则一句话：
**模型只写内容，版式与维护交给脚本。**

## 总览

用户不会每天去翻带日期的目录。**把成品投递到桌面**，是这类「每天看一眼」需求的标准交付方式。

这条链路包含四件事，按顺序：**命名策略 → 自动化末尾同步 → 脚本渲染 HTML → 长期维护（归档 + 健康检查）**。
配套的「到点弹窗提醒」见另一个 skill：`windows-scheduled-popup-reminder`。

### 先选命名策略：固定名 vs 带日期

| 策略 | 适合 | 例子 |
|---|---|---|
| **固定文件名**（每次覆盖） | 「永远只看最新」的看板、日历 | `marketmeeting.html` |
| **带日期文件名**（不覆盖） | 日报、快照 —— 用户会想翻历史 | `2026-09-22-情报收集.html` |
| **带周期文件名**（按季/按月） | 变化慢、但要能就地刷新 | `2026-Q3-会议日志.html` |

**别默认用固定名** —— 日报类固定名会把历史覆盖掉，用户某天想回看就没了。反过来，日历类用带日期名会一天堆一个文件。
**问清楚**，或者按上面的表判断。

| 做法 | 说明 |
|---|---|
| **单独一个 publish 脚本** | 例如 `publish_desktop.py`：不带参数自动取输出目录下**最新一期**（按 mtime），也可传路径指定。日期从**源文件名**正则提取，不要用 `date.today()`（否则补跑历史期会用错日期） |
| **自动化末尾同步** | 生成脚本跑完，在自动化 prompt 里**强制**加一步「复制到桌面」。异常分支也要写明这步不能跳 |

### 交付目录：桌面根目录，还是桌面上的一个文件夹？

**默认别散在桌面根目录** —— 一份日报一天 2 个文件（HTML + PNG），几天就把桌面铺满了。

| 放法 | 适合 |
|---|---|
| **桌面根目录** | 只有 1-2 个文件、且用户明确要求「直接放桌面」 |
| **桌面上的一个文件夹**（推荐） | 多份报告 / 带日期 / 同时出 PNG —— 桌面只留一个图标 |

**判断信号**：如果发现用户**手动把文件拖进了某个文件夹**，那就是他想要的交付位置 —— 顺着改，别问。
（本例：用户把 4 个成品拖进 `Desktop\情报收集\`，之后又加了 PNG，根目录会变成 8 个文件 —— 明显该收进文件夹。）

实现上给每个脚本一个 `DELIVER` 常量，改路径只改这一处：

```python
DESKTOP = Path.home() / "Desktop"
DELIVER = DESKTOP / "情报收集"      # 交付目录：成品都收在这里，桌面根目录保持干净
```

**改交付目录时要同步改 4 个地方**（漏一个就会静默失效）：

1. 各生成/发布脚本的 `DELIVER` 常量
2. 归档脚本（`tidy_desktop.py`）的**扫描目录** —— 它扫哪里决定它归档哪里
3. 健康检查脚本的**通配符前缀**
4. 两个自动化 prompt 里的产出路径 + 自检路径

> 第 4 条最容易漏：prompt 里的路径写错了，模型的自检会去错的地方找文件，然后报告「交付失败」——而实际交付是成功的。


### 改自动化 prompt 时必写的三件事

1. **交付步骤要标成「必做」**，并单独放进 prompt 靠前的独立段落（不要埋在最后一句里）。
2. **异常分支也要重申**，例如「X 数据源失败时仍必须执行桌面同步」——否则模型会在出错时顺手把交付一起跳过。
3. **写完加一段「交付自检」**，列出可验证的硬条件（文件已生成 / 页面日期是当天 / 已 present_files）。模型自检后会真的去核对。

> ⚠️ prompt 里会写死解释器与脚本的**绝对路径**。路径或版本一变，**所有引用了它的 prompt 都要同步改**，否则交付会静默失败（正文照常生成，只有桌面那份不更新，很难发现）。

### 多步收尾时，顺序要写死在 prompt 里

产物需要「生成 → 加工 → 发布」多步时，**顺序错一步结果就不对，而且不报错**。
例：日报的节点模块是**注入**到已生成的 HTML 里的，所以必须 `写归档 → inject_preview.py → publish_desktop.py`。
先发布再注入 = 桌面那份永远缺模块，但没有任何报错。prompt 里要写成「第 1 步 / 第 2 步 / 第 3 步，顺序不能错」。

## 渲染：让脚本出 HTML，别让模型手写

### md → HTML：同样用脚本转，别让模型手写 HTML

如果上游产出是 markdown（很多「写报告」类自动化都是），**不要**在 prompt 里让模型「再写一份 HTML」——每天样式都会漂。

正确做法：写一个自带极简 md→HTML 转换器的脚本（无第三方依赖，80 行足够），支持 h1-h6、`**粗体**`、`*斜体*`、`[文字](链接)`、裸 URL 自动链接、行内代码、`>` 引用（连续行合并）、表格（检测 `|---|` 对齐行）、有序/无序列表、`---` 分隔线、段落合并。

关键实现顺序：**先 `html.escape()` 再跑行内正则**（URL 里的 `&` 会被正确转成 `&amp;`，而 `[` `]` `(` `)` 不受影响，链接语法照样匹配）。

prompt 里只需写：写 md → 跑脚本 → present_files。样式由脚本保证，天天一致。

### HTML 片段用脚本生成 + 幂等注入，别让模型手写

日报/周报里常有一段**结构固定、数据来自 JSON** 的模块（如「未来 7 天节点」「本周待办」）。
**不要**在 prompt 里让模型每天手写这段 HTML —— 样式会漂、字段会漏。

正确做法：写一个**幂等注入脚本**，用 marker 注释识别并替换：

```python
MARK_BEGIN = "<!-- PREVIEW-MODULE:BEGIN -->"
MARK_END   = "<!-- PREVIEW-MODULE:END -->"

# 先剥掉上一次注入的（两侧空白一起吃掉，否则每次跑都会多攒一个换行）
html = re.sub(r"\s*" + re.escape(MARK_BEGIN) + r".*?" + re.escape(MARK_END) + r"\s*",
              "", html, flags=re.S)
# 再插到锚点后（如 </header> 之后），分隔符用固定的 "\n\n"
m = re.search(r"</header>\s*", html)
html = html[:m.end()] + "\n\n" + module + "\n" + html[m.end():]
# 样式只注一次
if "section.pv {" not in html:
    html = html.replace("</style>", PV_CSS + "</style>", 1)
```

好处：脚本可单独跑（补跑历史期）、可重复跑（幂等）、样式与数据源单点维护。
**幂等是关键** —— 否则重跑会插出两块、三块。
**验证幂等的正确方法**：连跑 3 次，字节数与 marker 数量都必须恒定。
只检查「marker 只有一个」不够 —— 上面那版只吃尾部空白的写法不会重复插模块，但每次会多攒一个换行（实测 22843 → 22844 递增）。

### 另一种常用版式：密排速览体（emoji 分类 + 单行一条）

公众号那种「📅 日期 + emoji 分类 + 一条一行 + 行末链接」的情报速览，比展开式报告更适合**每天扫一眼**。
数据密度高，用脚本渲染同样能保证样式稳定。

**md 结构约定**（模型写这个，脚本认这个）：

```markdown
# 📅 2026.9.22 AI 全网核心情报速览     ← 页面标题（月/日不补零）

> 口径：...                            ← 可选，灰色小字注解

## 👑 基座与开源权重                    ← 分类：emoji + 短标题

- 🟠 小米开源 **[MiMo-V2.6]**：说明文字。 https://url   ← 条目
```

**解析器要处理的三件事**：

```python
RE_ITEM = re.compile(r"^[-*]\s+(.*)$")
RE_H2   = re.compile(r"^##\s+(.*)$")
RE_URL_TAIL = re.compile(r"\s*(https?://\S+)\s*$")   # 只认行末 URL

def split_url(text):
    m = RE_URL_TAIL.search(text)
    return (text[:m.start()].rstrip(), m.group(1)) if m else (text, None)
```

**设计要点**：

| 要点 | 说明 |
|---|---|
| **URL 必须在行末** | 只认行末 URL，才能把正文和链接干净拆开。**要在 prompt 里明确写死这条**，否则模型会把链接单独放一行 |
| **行内语法先转义再替换** | `html.escape()` → 再跑 `**粗体**` / `` `code` `` / `[文字](链接)`，顺序反了会破坏链接语法 |
| **emoji 要约定配色** | 让模型「同一家公司固定同一个色块」（🟢 OpenAI · 🟣 Anthropic · 🔵 Google · 🟠 小米 · ⚡ xAI · 🟡 阿里 · 🔴 Meta），否则每天颜色乱跳，扫读优势就没了 |
| **分类 emoji 也给候选表** | 👑 基座 / ⚡ 推理端侧 / 🦾 具身智能 / 🎨 视觉生成 / 🎙️ 语音同传 / 🧪 评测治理 / 💰 融资 / 🛠️ 开发工具 |
| **渲染后打印条数** | `sections: N \| items: M`，让模型能自检数量是否落在预期区间；解析不到就报 `NO_ITEMS_PARSED` 并提示检查 `- ` 前缀 |
| **版式** | 单栏 `max-width: 760px`、正文 15.5px / line-height 1.78、条目间距 9px、链接 13px 灰色 `word-break: break-all`。**密度靠收紧行距，不靠缩字号** |

**口径要跟版式匹配**：密排速览体一次要 10-15 条才填得满。如果沿用过严的「只收当天 + 只收权威源」口径，经常只筛出 2-4 条，页面会很空。
换版式时**要一并放宽收录口径**（允许 48 小时内发酵的动态、厂商官方 X、评测机构榜单、有出处的传闻），但**日期核验不能松** —— 这两件事是独立的，别一起放开。

### 导出 PNG：长图分享 / 配图（`html2png.py`）

报告要发微信、发朋友圈、贴文档时，HTML 不够用 —— 需要一张**整页长图**。

**Chrome 无头 CLI 没有整页参数** —— `--screenshot` 只截 `--window-size` 指定的视口，页面超出部分直接丢。所以必须**两趟**：

```python
# 第 1 趟：注入量高脚本，dump-dom 把高度读回来
PROBE = ("<script>window.addEventListener('load',function(){"
         "document.title='__H__='+document.documentElement.scrollHeight;});</script>")
src = html.replace("</body>", PROBE + "</body>", 1)
# --dump-dom 输出的 DOM 里 <title> 已变成 __H__=1507
h = int(re.search(r"__H__=(\d+)", dump_output).group(1))

# 第 2 趟：用这个高度截图
chrome --headless=new --hide-scrollbars \
       --force-device-scale-factor=2 \
       --window-size=760,{h} --screenshot=out.png file:///...
```

四个要点：

| 要点 | 说明 |
|---|---|
| **必须两趟** | 不能靠估算高度 —— 估短了底部被切，估长了底部一大片白 |
| **`--force-device-scale-factor`** | 导出 2 倍图文字锐利。**但长文档不能无脑 2x** —— 见下 |
| **`--hide-scrollbars`** | 否则右侧会有一条滚动条进图 |
| **宽度按版式选** | 窄栏版式（速览体）用 760；宽版报告用 1000-1200。跟 CSS 的 `max-width` 对齐 |

**自适应降采样（长文档必须做）**：6800px 的内容按 2 倍出图 = 13650px、2.2MB 的 PNG，微信和多数看图软件都吃不消。
按**输出总高**反推像素比，优先 2x，超限就退 1.5x / 1x：

```python
def pick_scale(css_height, want=2.0, max_h=8000):
    for s in (2.0, 1.5, 1.0):
        if s <= want and css_height * s <= max_h:
            return s
    return 1.0
```

实测效果：速览体 1507px → 2x（1520×3014, 693KB）；会议日志 3880px → 2x（2080×7760, 1.0MB）；链上日报 6801px → **降到 1x**（1000×6825, 611KB）。

**导出前先确认 JS 跑完**：如果页面有浏览器端实时计算的区块（「未来 7 天」这类），`--virtual-time-budget=3000` 必须带上，否则截到的是空区块。**验收方法：打开 PNG 看图，别只看文件生成成功。**

**这也顺便解决了「AI 生图不可用」的问题**：示意图、图标、封面版式、数据图表都可以用 SVG / HTML+CSS 画出来，再用这条路导出 PNG。做不了的只有照片级写实图和 AI 插画。

### ⚠️ 加文件类型时，别忘了同步「按单位保留」的逻辑

给交付物加了 PNG 之后，`tidy_desktop.py` 立刻出 bug：把**当前季度**的会议日志归档了。

原因：保留逻辑原本是 `sorted_quarters[keep_quarters:]` —— 加了 PNG 后每个季度变成 **2 个文件**，按文件数切片等于只保留 1 个季度。

**正确写法：先按单位去重，再按单位保留。**

```python
# ❌ 按文件数切（一单位多文件时会误伤）
for (y, q), p in scan_quarter()[keep_quarters:]:
    ...

# ✅ 按季度去重后再切
q_seen = list(dict.fromkeys(k for k, _ in quarters))
kept_q = set(q_seen[:keep_quarters])
for (y, q), p in quarters:
    if (y, q) not in kept_q:
        ...
```

**通则**：任何「保留最近 N 个 X」的逻辑，只要一个 X 可能对应多个文件，就必须先按 X 去重。
改这类脚本后**务必用 `--dry-run` 加一个小 N 验证边界**（`--keep-quarters 1` 应该只归档最老的季度，而不是归档当前季度）。

### 换版式时：留旧脚本做备用，别删

新渲染器上线后，旧的那个（另一种版式）**保留在目录里但标注「备用」**，并在 prompt 里写清「当前用哪个」。

理由：版式偏好会反复（用户可能过两周想看回深度版）。删掉后要重新写一遍；留着只是多一个文件。
配套做法：健康检查脚本把两个都列进检查项，但标签区分「当前使用」和「备用」。

### 关键设计：能在浏览器端实时算的，就别在生成时算死

如果页面里有「未来 7 天」「距现在还有 X 天」「下次提醒时间」这类**相对时间**内容：

- ❌ 生成时算好写进 HTML → 页面放两天就变成假数据，用户还以为没节点
- ✅ 把数据以 JSON 内嵌进页面，用一小段 JS 在 `DOMContentLoaded` 时按 `new Date()` 实时渲染 → **打开即当天视角，不需要每天刷新**

内嵌方式（Python 侧）：

```python
html = html.replace("</body>",
    EXTRA_JS.replace("__EVENTS__",
        json.dumps(slim, ensure_ascii=False, separators=(",", ":"))) + "</body>", 1)
```

JS 侧用 `new Date(s.replace(' ', 'T'))` 把 `"2026-09-25 16:00"` 解析为**本地时间**（不要用 `Date.parse` 直接吃带空格的字符串，各浏览器行为不一致）。

### 验证方法

Chrome 无头 CLI 一次命令同时验 DOM 和视觉：

```bash
# 验动态区块真的渲染出来了（看注入后的 DOM）
chrome.exe --headless=new --disable-gpu --virtual-time-budget=4000 --dump-dom \
  --user-data-dir=<临时目录> "file:///C:/path/to/page.html" > dom.html

# 验视觉效果
chrome.exe --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=4000 \
  --window-size=1440,1500 --screenshot="out.png" \
  --user-data-dir=<临时目录> "file:///C:/path/to/page.html"
```

`--virtual-time-budget` 不能省，否则 JS 还没跑完就截图/导出 DOM 了。

## 维护：让它跑一年不烂

### 带日期交付必须配一个「归档整理」脚本

选了带日期命名，桌面就会无限堆积（日报一天两个文件 = 一年 700+）。**这是带日期方案的固有代价，必须一并解决**，否则用户过两周就会抱怨桌面乱。

推荐做法：`tidy_desktop.py`，**移动而不是删除**，接在 publish 脚本末尾自动跑。

```python
KEEP_DAYS = 7          # 桌面保留最近几天
ARCHIVE = BASE / "archive"

RE_DAILY = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-情报收集(-AI)?\.html$")

def plan(keep_days=KEEP_DAYS):
    # 1) 只认自己生成的文件名 —— 桌面其他文件一律不碰
    found = [(d, p) for p in DESKTOP.iterdir()
             if p.is_file() and (m := RE_DAILY.match(p.name))]
    # 2) 按「日期」保留，不是按文件数（一天两个文件算同一天）
    days = list(dict.fromkeys(d for d, _ in sorted(found, reverse=True)))
    kept = set(days[:keep_days])
    # 3) 目标按月份分目录，避免归档目录本身又堆成一层
    return [(p, ARCHIVE / d.strftime("%Y-%m") / p.name)
            for d, p in found if d not in kept]

def tidy(dry_run=False):
    for src, dst in plan():
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))   # 移动，永不删除
```

四条设计要点：

1. **只认白名单正则** —— 桌面是用户的私人空间，绝不能按 `*.html` 或 `*` 扫。任何匹配不上的文件一律跳过。
2. **`shutil.move` 不是 `os.remove`** —— 移动完整可逆，归档目录里随时能翻回来。删除是不可逆的，不要碰。
3. **按「天」保留而不是按「文件数」** —— 一天生成多个文件时，按文件数保留会让实际保留天数缩水一半。
4. **`--dry-run` 开关** —— 上线前先跑一次给用户看会动哪些文件；也方便日后调试。

**接进 publish 脚本而不是写进自动化 prompt**：模型每天要记的步骤越少越可靠。放脚本里 = 零遗忘。

```python
# publish_desktop.py 末尾
def tidy_desktop_now():
    try:
        import tidy_desktop
        tidy_desktop.tidy()
    except Exception as e:
        print("TIDY_SKIPPED:", type(e).__name__, e)   # 整理失败不影响交付主流程
```

**验证时注意**：当天只有一个日期时默认保留窗口内，脚本会输出「无需整理」—— 这是正常的。要验证移动逻辑本身，用 `--keep 0` 强制全部归档，确认落盘后**手动移回去**再收工。

### 健康检查脚本遇到带日期文件，必须用通配符

自检脚本检查「桌面成品在不在」时，**如果文件名带日期，绝对不能写死路径** —— 每天都会误报「缺失」。

用通配符 + 至少匹配到一个：

```powershell
$globs = [ordered]@{
    '桌面·链上情报收集（*-情报收集.html）'   = "$DESKTOP\*-情报收集.html"
    '桌面·AI 情报收集（*-情报收集-AI.html）' = "$DESKTOP\*-情报收集-AI.html"
    '桌面·会议日志（*-Q*-会议日志.html）'    = "$DESKTOP\*-Q*-会议日志.html"
    '会议日志本地副本'                       = "$DAILY\meeting-logs\*-Q*-会议日志.html"
}
foreach ($k in $globs.Keys) {
    if (-not (Get-ChildItem -Path $globs[$k] -ErrorAction SilentlyContinue)) {
        $bad += "【缺失】$k`r`n         匹配不到：$($globs[$k])"
    }
}
```

注意通配符要**足够窄**，否则会把无关文件当成通过（`*-会议日志.html` 比 `*.html` 安全）。

### Windows 上写文件记得 `newline=""`

Python 的 `Path.write_text()` / `open(..., "w")` 在 Windows 上会把 `\n` 翻译成 `\r\n`，导致**磁盘字节数比脚本打印的大**，对不上账。用：

```python
with path.open("w", encoding="utf-8", newline="") as fh:
    fh.write(html)
```

HTML 渲染不受影响，但字节数一致能让「改了什么、变了多少」这类判断可靠。
