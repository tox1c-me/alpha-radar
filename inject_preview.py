# -*- coding: utf-8 -*-
"""
给已生成的 Daily 情报日报 HTML 注入「未来 7 天关键节点」模块。

用法:
    python inject_preview.py "reports/daily-intel-2026-10-11.html" [today]

不传 today 时取系统当天日期。模块插在 </header> 之后、第一个 section 之前。
重复运行会先移除上一次注入的模块（按 marker 注释识别），幂等。
"""
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
EVENTS = BASE / "events.json"
EXTRA = BASE / "calendar-extra.json"

MARK_BEGIN = "<!-- PREVIEW-MODULE:BEGIN -->"
MARK_END = "<!-- PREVIEW-MODULE:END -->"

LEVEL_CLASS = {"高": "warn", "加密": "warn", "中": "new", "提示": "new"}


def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def build(today: date) -> str:
    horizon = today + timedelta(days=7)
    timed, dated = [], []

    for e in json.loads(EVENTS.read_text(encoding="utf-8")):
        dt = datetime.strptime(e["time"], "%Y-%m-%d %H:%M")
        if today <= dt.date() <= horizon:
            timed.append((dt, e))
    for e in json.loads(EXTRA.read_text(encoding="utf-8")):
        d = datetime.strptime(e["date"], "%Y-%m-%d").date()
        if today <= d <= horizon:
            dated.append((d, e))

    timed.sort(key=lambda x: x[0])
    dated.sort(key=lambda x: x[0])

    # 36 小时内的紧急项
    urgent = [e for dt, e in timed
              if timedelta(0) <= (dt - datetime.combine(today, datetime.min.time())) <= timedelta(hours=36)
              and e.get("level") in ("高", "加密")]

    rows = []
    if urgent:
        names = "、".join(esc(e["title"]) for e in urgent)
        rows.append(
            '<div class="pv-urgent"><b>⚠ 36 小时内高影响节点：</b>%s'
            '<br><span class="pv-dim">建议提前调整仓位。</span></div>' % names
        )

    if timed:
        body = []
        for dt, e in timed:
            delta = (dt.date() - today).days
            when = "今天" if delta == 0 else ("明天" if delta == 1 else "%d 天后" % delta)
            body.append(
                '<tr><td class="pv-when">%s<br><span class="pv-dim">%s</span></td>'
                '<td><span class="tag %s">%s</span> %s</td></tr>'
                % (esc(when), esc(dt.strftime("%m-%d %H:%M")),
                   LEVEL_CLASS.get(e.get("level"), "new"), esc(e.get("level", "")),
                   esc(e["title"]))
            )
        rows.append(
            '<p class="pv-sub">有精确时间 · <b>到点会在电脑上弹窗提醒</b></p>'
            '<table class="pv-table">%s</table>' % "".join(body)
        )
    else:
        rows.append('<p class="pv-sub">未来 7 天没有已登记的精确时间节点。</p>')

    if dated:
        body = []
        for d, e in dated:
            delta = (d - today).days
            when = "今天" if delta == 0 else ("明天" if delta == 1 else "%d 天后" % delta)
            body.append(
                '<tr><td class="pv-when">%s<br><span class="pv-dim">%s</span></td>'
                '<td><span class="tag %s">%s</span> %s'
                '<br><span class="pv-dim">%s</span></td></tr>'
                % (esc(when), esc(d.strftime("%m-%d")),
                   LEVEL_CLASS.get(e.get("level"), "new"), esc(e.get("level", "")),
                   esc(e["title"]), esc(e.get("note", "")))
            )
        rows.append(
            '<p class="pv-sub">仅日期 · <b>不弹窗</b>（无确切发布时间）</p>'
            '<table class="pv-table">%s</table>' % "".join(body)
        )

    if not timed and not dated:
        rows.append('<p class="pv-sub">数据源已超出有效期，请补充新节点。</p>')

    return (
        MARK_BEGIN
        + '\n<section class="pv">\n  <h2>未来 7 天关键节点</h2>\n'
        + '\n'.join("  " + r for r in rows)
        + '\n</section>\n'
        + MARK_END
    )


PV_CSS = """
  section.pv { border-left: 4px solid #0f6e56; }
  .pv-sub { font-size: 14.5px; color: #86847e; margin: 16px 0 6px; }
  .pv-table { margin-top: 2px; }
  .pv-when { white-space: nowrap; font-weight: 600; padding-right: 16px; }
  .pv-dim { color: #86847e; font-weight: 400; font-size: 13.5px; }
  .pv-urgent {
    background: #fcebeb; border: 1px solid #f0c6c6; border-radius: 9px;
    padding: 12px 15px; margin: 4px 0 6px; font-size: 15.5px; color: #a32d2d;
  }
"""


def main():
    if len(sys.argv) < 2:
        print("usage: inject_preview.py <report.html> [today YYYY-MM-DD]")
        return 1
    path = Path(sys.argv[1])
    if not path.exists():
        print("NOT_FOUND: %s" % path)
        return 1

    today = (datetime.strptime(sys.argv[2], "%Y-%m-%d").date()
             if len(sys.argv) > 2 else date.today())

    html = path.read_text(encoding="utf-8")

    # 幂等：先剥掉旧模块（连同两侧空白一起吃掉，否则每次跑都会多攒一个换行）
    html = re.sub(r"\s*" + re.escape(MARK_BEGIN) + r".*?" + re.escape(MARK_END) + r"\s*",
                  "", html, flags=re.S)

    module = build(today)

    # 插到 </header> 之后
    m = re.search(r"</header>\s*", html)
    if not m:
        print("NO_HEADER_ANCHOR")
        return 1
    html = html[:m.end()] + "\n\n" + module + "\n" + html[m.end():]

    # 注入样式（只注一次）
    if "section.pv {" not in html:
        html = html.replace("</style>", PV_CSS + "</style>", 1)

    # newline="" 避免 Windows 上把 \n 翻译成 \r\n（会让文件无谓变大、字节数对不上账）
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(html)
    print("OK: injected %d bytes -> %s" % (len(html.encode("utf-8")), path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
