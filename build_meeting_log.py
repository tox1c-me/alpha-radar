# -*- coding: utf-8 -*-
"""生成按季度拆分的「会议日志」页面。

数据源（唯一真相）：
  events.json         —— 有精确时间的节点（会注册弹窗提醒）
  calendar-extra.json —— 仅有日期的节点（不弹窗，只做日程显示）

输出（每个有数据的季度一个文件）：
  DailyIntel\\meeting-logs\\YYYY-QN-会议日志.html
  并同步一份到桌面

设计要点：
  · 「未来 7 天」只在**当前季度**的文件里渲染（其余季度是历史/未来快照，算了没意义）
  · 「电脑弹窗提醒时间表」同样只在当前季度文件里给（提醒是面向未来的）
  · 每个季度文件只列**本季度**的节点，季度归属按自然季度（Q3 = 7-9 月）
"""

import html as _html
import json
import re
import shutil
from datetime import datetime, date
from pathlib import Path

from config import DESKTOP, ROOT as BASE
DELIVER = DESKTOP / "情报收集"      # 交付目录：成品都收在这个文件夹里
OUT_DIR = BASE / "meeting-logs"

LV_CLASS = {"高": "h", "中": "m", "加密": "c", "提示": "n"}

MONTH_CN = {1: "1 月", 2: "2 月", 3: "3 月", 4: "4 月", 5: "5 月", 6: "6 月",
            7: "7 月", 8: "8 月", 9: "9 月", 10: "10 月", 11: "11 月", 12: "12 月"}


def quarter_of(d: date) -> int:
    return (d.month - 1) // 3 + 1


def clean_body(body: str) -> str:
    """events.json 的 body 形如：
       北京时间 09-25 16:00

       Deribit 季度期权交割（9 月最后一个周五）。
       季度最大规模期权到期……
    去掉第一段的「北京时间…」，其余合成一句（中文标点后不补空格）。
    """
    parts = [p.strip() for p in body.split("\n\n") if p.strip()]
    if parts and parts[0].startswith("北京时间"):
        parts = parts[1:]
    parts = [re.sub(r"\s+", " ", p.replace("\n", " ")) for p in parts]
    out = ""
    for p in parts:
        if out and out[-1] not in "。！？；：，、":
            out += " "
        out += p
    return out.strip()


def strip_title_prefix(desc: str, title: str) -> str:
    """body 里常把标题又复述一遍，去掉开头重复的部分，只留真正的关注点。"""
    d = desc.strip()
    if d.startswith(title):
        d = d[len(title):].lstrip("，。、：: ")
    return d or desc


def esc(s: str) -> str:
    return _html.escape(s, quote=False)


def load_nodes():
    """把两份数据源统一成同一个结构。"""
    nodes = []

    for e in json.loads((BASE / "events.json").read_text(encoding="utf-8")):
        dt = datetime.strptime(e["time"], "%Y-%m-%d %H:%M")
        nodes.append({
            "d": dt.date(),
            "dt": dt,
            "lv": e["level"],
            "ti": e["title"],
            "desc": clean_body(e["body"]),
            "precise": True,
        })

    for x in json.loads((BASE / "calendar-extra.json").read_text(encoding="utf-8")):
        d = datetime.strptime(x["date"], "%Y-%m-%d").date()
        nodes.append({
            "d": d,
            "dt": None,
            "lv": x["level"],
            "ti": x["title"],
            "desc": x.get("note", ""),
            "precise": False,
        })

    nodes.sort(key=lambda n: (n["d"], n["dt"].hour * 60 + n["dt"].minute if n["dt"] else 24 * 60))
    return nodes


CSS = """
  * { box-sizing: border-box; }
  body {
    margin: 0; padding: 40px 24px 72px;
    background: #f7f7f5; color: #2c2c2a;
    font-family: -apple-system, "Segoe UI", "Microsoft YaHei", system-ui, sans-serif;
    font-size: 16.5px; line-height: 1.75;
  }
  .wrap { max-width: 1000px; margin: 0 auto; }
  h1 { font-size: 28px; font-weight: 600; margin: 0 0 8px; }
  .sub { color: #6b6a65; font-size: 14.5px; margin-bottom: 24px; }
  .notice {
    background: #fff; border: 1px solid #e6e4de; border-left: 4px solid #185fa5;
    border-radius: 12px; padding: 18px 24px; margin-bottom: 26px; font-size: 15.5px;
  }
  h2 { font-size: 20px; font-weight: 600; margin: 34px 0 12px; padding-bottom: 8px; border-bottom: 2px solid #e6e4de; }
  table { width: 100%; border-collapse: collapse; font-size: 15.5px; background: #fff; border: 1px solid #e6e4de; border-radius: 12px; overflow: hidden; }
  th { text-align: left; font-weight: 600; font-size: 14px; color: #86847e; padding: 12px 14px; background: #faf9f6; border-bottom: 1px solid #e6e4de; }
  td { padding: 13px 14px; border-bottom: 1px solid #f4f2ec; vertical-align: top; }
  tr:last-child td { border-bottom: none; }
  td.d { white-space: nowrap; font-weight: 600; }
  td.bj { white-space: nowrap; color: #575652; font-size: 14.5px; }
  .lv { font-size: 12.5px; padding: 2px 8px; border-radius: 5px; white-space: nowrap; font-weight: 600; }
  .lv.h { background: #fcebeb; color: #a32d2d; }
  .lv.m { background: #faeeda; color: #854f0b; }
  .lv.c { background: #e6f1fb; color: #185fa5; }
  .lv.n { background: #f0eee8; color: #575652; }
  .note { color: #86847e; font-size: 14px; margin-top: 10px; }
  .empty { background: #fff; border: 1px dashed #e6e4de; border-radius: 12px; padding: 20px 24px; color: #86847e; font-size: 15.5px; }
  /* --- 动态区块 --- */
  .up-card {
    background: #fff; border: 1px solid #e6e4de; border-left: 4px solid #185fa5;
    border-radius: 12px; padding: 16px 22px 12px; margin-bottom: 26px;
  }
  .up-card.hot { border-left-color: #a32d2d; background: #fffbfb; }
  .up-card.calm { border-left-color: #86847e; }
  .up-card h3 { margin: 0 0 10px; font-size: 17px; font-weight: 600; }
  .up-card h3 .tag {
    font-size: 12.5px; font-weight: 600; color: #a32d2d;
    background: #fcebeb; padding: 2px 9px; border-radius: 5px; margin-left: 8px; vertical-align: middle;
  }
  .up-row { display: flex; gap: 12px; align-items: baseline; padding: 7px 0; border-bottom: 1px dashed #f0eee8; font-size: 15.5px; }
  .up-row:last-child { border-bottom: none; }
  .up-t { font-variant-numeric: tabular-nums; font-weight: 600; color: #185fa5; white-space: nowrap; }
  .up-d { color: #86847e; font-size: 13.5px; white-space: nowrap; }
  .up-note { color: #86847e; font-size: 13.5px; }
  .up-empty { color: #86847e; font-size: 15px; padding: 4px 0 8px; }
  .up-sub { font-size: 13px; font-weight: 600; color: #86847e; margin: 14px 0 4px; padding-top: 10px; border-top: 1px solid #f0eee8; }
  .up-sub:first-of-type { margin-top: 6px; padding-top: 0; border-top: none; }
  .up-row.dim .up-x { color: #575652; }
  .up-row.dim .up-t { color: #86847e; font-weight: 500; }
  td.a-alert { white-space: nowrap; font-weight: 600; color: #185fa5; font-variant-numeric: tabular-nums; }
  td.a-ev { white-space: nowrap; color: #86847e; font-variant-numeric: tabular-nums; }
  td.a-off { white-space: nowrap; color: #86847e; font-variant-numeric: tabular-nums; }
"""

DYNAMIC_JS = """
<script>
const EV = __EVENTS__;
const EXTRA = __EXTRA__;
const NOW = new Date();

function parseT(s) { return new Date(s.replace(' ', 'T')); }
function parseD(s) { const p = s.split('-'); return new Date(+p[0], +p[1] - 1, +p[2]); }
function pad(n) { return (n < 10 ? '0' : '') + n; }
function hm(d) { return pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes()); }
function lvClass(lv) { return lv === '高' ? 'h' : (lv === '中' ? 'm' : (lv === '加密' ? 'c' : 'n')); }
function rel(d) {
  const ms = d - NOW, h = ms / 3600000;
  if (h < 0) return '已过';
  if (h < 1) return '不到 1 小时';
  if (h < 24) return Math.round(h) + ' 小时后';
  const day = Math.floor(h / 24);
  if (day === 1) return '明天';
  return day + ' 天后';
}

(function () {
  const box = document.getElementById('upcoming');
  if (!box) return;
  const limit = new Date(NOW.getTime() + 7 * 86400000);
  const today = new Date(NOW.getFullYear(), NOW.getMonth(), NOW.getDate());

  const list = EV.filter(e => { const t = parseT(e.t); return t > NOW && t <= limit; })
                  .sort((a, b) => parseT(a.t) - parseT(b.t));
  const ex = EXTRA.filter(x => { const d = parseD(x.d); return d >= today && d <= limit; })
                  .sort((a, b) => parseD(a.d) - parseD(b.d));

  const hot = list.some(e => e.lv === '高' && (parseT(e.t) - NOW) < 36 * 3600000)
           || ex.some(x => x.lv === '高' && (parseD(x.d) - today) <= 2 * 86400000);
  const cls = (list.length + ex.length) === 0 ? 'up-card calm' : (hot ? 'up-card hot' : 'up-card');

  let html = '<div class="' + cls + '"><h3>未来 7 天关键节点';
  if (hot) html += '<span class="tag">36 小时内有高影响事件</span>';
  html += '</h3>';

  if (list.length + ex.length === 0) {
    html += '<div class="up-empty">未来 7 天没有已登记的节点。突发节点（央行临时讲话、ETF 审批截止、重大解锁）需自行留意。</div>';
  } else {
    if (list.length) {
      html += '<div class="up-sub">有精确时间 · 到点会弹窗提醒</div>';
      list.forEach(e => {
        const t = parseT(e.t);
        html += '<div class="up-row">'
              + '<span class="up-t">' + hm(t) + '</span>'
              + '<span class="up-d">' + rel(t) + '</span>'
              + '<span class="lv ' + lvClass(e.lv) + '">' + e.lv + '</span>'
              + '<span class="up-x">' + e.ti + '</span></div>';
      });
    }
    if (ex.length) {
      html += '<div class="up-sub">仅日期 · 无精确时间，不弹窗，需自行留意</div>';
      ex.forEach(x => {
        const d = parseD(x.d);
        const days = Math.round((d - today) / 86400000);
        const when = days === 0 ? '今天' : (days === 1 ? '明天' : days + ' 天后');
        html += '<div class="up-row dim">'
              + '<span class="up-t">' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + '</span>'
              + '<span class="up-d">' + when + '</span>'
              + '<span class="lv ' + lvClass(x.lv) + '">' + x.lv + '</span>'
              + '<span class="up-x">' + x.ti + ' <span class="up-note">' + (x.no || '') + '</span></span></div>';
      });
    }
  }
  html += '</div>';
  box.innerHTML = html;
})();

(function () {
  const box = document.getElementById('alerts');
  if (!box) return;
  const rows = [];
  EV.forEach(e => {
    const t = parseT(e.t);
    const offs = e.lv === '高' ? [60, 30] : [60];
    offs.forEach(o => {
      const a = new Date(t.getTime() - o * 60000);
      if (a > NOW) rows.push({ a: a, e: t, lv: e.lv, ti: e.ti, o: o });
    });
  });
  rows.sort((x, y) => x.a - y.a);

  if (!rows.length) {
    box.innerHTML = '<div class="empty">本季度提醒已全部过期。更新 events.json 后重跑 build_tasks.py 与 build_meeting_log.py。</div>';
    return;
  }
  let html = '<table><tr><th>弹窗时间</th><th>事件时间</th><th>级别</th><th>提前</th><th>事件</th></tr>';
  rows.forEach(r => {
    html += '<tr>'
          + '<td class="a-alert">' + hm(r.a) + '</td>'
          + '<td class="a-ev">' + hm(r.e) + '</td>'
          + '<td><span class="lv ' + lvClass(r.lv) + '">' + r.lv + '</span></td>'
          + '<td class="a-off">' + r.o + ' 分</td>'
          + '<td>' + r.ti + '</td></tr>';
  });
  html += '</table>';
  html += '<p class="note">共 ' + rows.length + ' 次弹窗。高影响事件提前 60 与 30 分钟各弹一次，其余提前 60 分钟。</p>';
  box.innerHTML = html;
})();
</script>
"""

FIXED_RHYTHM = """
<h2>每月固定节奏</h2>
<table>
  <tr><th>时间</th><th>事件</th><th>说明</th></tr>
  <tr><td class="d">每月 20 日 09:15</td><td>中国 LPR 报价</td><td>1 年期与 5 年期以上贷款市场报价利率</td></tr>
  <tr><td class="d">每月最后一天 09:30</td><td>中国官方 PMI</td><td>制造业与非制造业景气度</td></tr>
  <tr><td class="d">每月第一个周五</td><td>美国非农</td><td>遇节假日顺延</td></tr>
  <tr><td class="d">每月中旬</td><td>美国 CPI / PPI</td><td>通常在 10-15 日之间</td></tr>
  <tr><td class="d">每月月底</td><td>美国 PCE</td><td>美联储最看重的通胀指标</td></tr>
  <tr><td class="d">每月最后一个周五</td><td>Deribit 期权交割</td><td>季度月（3/6/9/12）规模最大</td></tr>
</table>
"""


def build_quarter(year, q, nodes, is_current):
    qn = [n for n in nodes if n["d"].year == year and quarter_of(n["d"]) == q]
    if not qn:
        return None

    months = sorted({n["d"].month for n in qn})
    first, last = qn[0]["d"], qn[-1]["d"]

    body = []

    if is_current:
        body.append('<div id="upcoming"></div>')

    body.append('<div class="notice">'
                '<b>级别：</b>'
                '<span class="lv h">高</span> 直接冲击风险资产定价，建议提前调整仓位 · '
                '<span class="lv m">中</span> 影响预期但不改趋势 · '
                '<span class="lv c">加密</span> 加密市场特有节点 · '
                '<span class="lv n">提示</span> 日程性质（非数据发布）'
                '<br><br>'
                '<b>时间换算：</b>美国夏令时于 <b>11 月 1 日结束</b>，此后美国数据发布时间在北京时间上'
                '<b>推迟 1 小时</b>（8:30 ET 从 20:30 变为 21:30 北京）。'
                '</div>')

    for m in months:
        mn = [n for n in qn if n["d"].month == m]
        body.append('<h2>%s %d</h2>' % (MONTH_CN[m], year))
        body.append('<table>'
                    '<tr><th>日期</th><th>北京时间</th><th>事件</th><th>级别</th><th>关注点</th></tr>')
        for n in mn:
            wd = "一二三四五六日"[n["d"].weekday()]
            bj = n["dt"].strftime("%H:%M") if n["dt"] else "—"
            body.append(
                '<tr>'
                '<td class="d">%d/%d %s</td>'
                '<td class="bj">%s</td>'
                '<td><b>%s</b></td>'
                '<td><span class="lv %s">%s</span></td>'
                '<td>%s</td>'
                '</tr>' % (
                    n["d"].month, n["d"].day, wd, bj,
                    esc(n["ti"]),
                    LV_CLASS.get(n["lv"], "n"), esc(n["lv"]),
                    esc(strip_title_prefix(n["desc"], n["ti"])),
                ))
        body.append('</table>')

    if is_current:
        body.append('<h2>电脑弹窗提醒时间表</h2>')
        body.append('<div id="alerts"></div>')

    body.append(FIXED_RHYTHM)

    body.append(
        '<p class="note" style="margin-top:20px">'
        '数据来源：Federal Reserve 官方 FOMC 日历、BLS / BEA / Census 发布日程、ECB / BoJ / BoE 官方日历。'
        '中国会议日期中政治局会议与中央经济工作会议不提前公布具体日期，按历史规律标注。'
        '<b>日程可能调整，临近时以官方为准。</b>'
        '</p>'
        '<p class="note">生成时间：%s</p>' % datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    title = "%d Q%d 会议日志" % (year, q)
    doc = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ · __YEAR__ 年 __Q__ 季度</title>
<style>__CSS__</style>
</head>
<body>
<div class="wrap">
<h1>__TITLE__</h1>
<div class="sub">__YEAR__ 年 __Q__ 季度 · __FIRST__ — __LAST__ · 共 __N__ 个节点 · 所有时间已换算为北京时间</div>
__BODY__
</div>
__JS__
</body>
</html>
"""

    script = ""
    if is_current:
        events = json.loads((BASE / "events.json").read_text(encoding="utf-8"))
        extra = json.loads((BASE / "calendar-extra.json").read_text(encoding="utf-8"))
        slim = [{"t": e["time"], "lv": e["level"], "ti": e["title"]} for e in events]
        slim_extra = [{"d": x["date"], "lv": x["level"], "ti": x["title"], "no": x.get("note", "")}
                      for x in extra]
        script = (DYNAMIC_JS
                  .replace("__EVENTS__", json.dumps(slim, ensure_ascii=False, separators=(",", ":")))
                  .replace("__EXTRA__", json.dumps(slim_extra, ensure_ascii=False, separators=(",", ":"))))

    doc = (doc
           .replace("__CSS__", CSS)
           .replace("__TITLE__", title)
           .replace("__YEAR__", str(year))
           .replace("__Q__", str(q))
           .replace("__FIRST__", first.strftime("%m-%d"))
           .replace("__LAST__", last.strftime("%m-%d"))
           .replace("__N__", str(len(qn)))
           .replace("__BODY__", "\n".join(body))
           .replace("__JS__", script))

    return doc


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    nodes = load_nodes()
    today = date.today()
    cur_y, cur_q = today.year, quarter_of(today)

    quarters = sorted({(n["d"].year, quarter_of(n["d"])) for n in nodes})
    written = []

    for (y, q) in quarters:
        is_current = (y == cur_y and q == cur_q)
        doc = build_quarter(y, q, nodes, is_current)
        if not doc:
            continue
        name = "%d-Q%d-会议日志.html" % (y, q)
        local = OUT_DIR / name
        local.write_text(doc, encoding="utf-8")
        shutil.copyfile(local, DELIVER / name)
        written.append((name, is_current, local.stat().st_size))

        # 顺带出整页 PNG（发微信/贴文档用）。失败不影响主流程。
        try:
            import html2png
            png = local.with_suffix(".png")
            html2png.render(local, png, width=1040, scale=2, pad=24)
            shutil.copyfile(png, DELIVER / png.name)
        except Exception as e:
            print("  PNG_SKIPPED:", type(e).__name__, e)

    # 清掉已不再生成的季度文件（数据被删/调整时）—— HTML 和 PNG 都要清
    valid = {n for n, _, _ in written}
    valid_png = {Path(n).with_suffix(".png").name for n in valid}
    for f in OUT_DIR.glob("*-Q*-会议日志.*"):
        if f.name not in valid and f.name not in valid_png:
            f.unlink()
        d = DELIVER / f.name
        if d.exists() and f.name not in valid and f.name not in valid_png:
            d.unlink()

    for name, is_cur, size in written:
        print("%-26s %-8s %6d bytes" % (name, "当前季度" if is_cur else "", size))
    print("quarters:", len(written), "| nodes:", len(nodes))


if __name__ == "__main__":
    main()
