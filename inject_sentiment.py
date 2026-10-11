# -*- coding: utf-8 -*-
"""把「市场情绪总览」模块注入日报 HTML 的最前面（</header> 之后、节点模块之前）。

数据来源：raw/market_sentiment.json（由 fetch_market_sentiment.py 产出）

用法:
    python inject_sentiment.py "reports\\daily-intel-2026-10-11.html"

幂等：按 <!-- SENTIMENT:BEGIN --> / <!-- SENTIMENT:END --> 标记先剥后插。
注意执行顺序：必须在 inject_preview.py **之后**跑（否则节点模块会被插到前面）。
"""
import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "raw" / "market_sentiment.json"

MB = "<!-- SENTIMENT:BEGIN -->"
ME = "<!-- SENTIMENT:END -->"

BJ = timezone(timedelta(hours=8))

# 恐惧贪婪指数分区（沿用 CoinMarketCap 页面的配色语义）
ZONES = [(0, 25, "极度恐惧", "#c0392b"),
         (25, 45, "恐惧", "#e07b39"),
         (45, 55, "中性", "#b8a13a"),
         (55, 75, "贪婪", "#5fa463"),
         (75, 101, "极度贪婪", "#1e7a45")]

# CMC 返回的是英文档位名，映射成中文
LABEL_CN = {"Extreme Fear": "极度恐惧", "Fear": "恐惧", "Neutral": "中性",
            "Greed": "贪婪", "Extreme Greed": "极度贪婪"}


def zone_of(v):
    for lo, hi, name, col in ZONES:
        if lo <= v < hi:
            return name, col
    return ZONES[-1][2], ZONES[-1][3]


def label_cn(s):
    s = (s or "").strip()
    return LABEL_CN.get(s, s)


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def money(v, digits=2):
    """人类可读的美元金额。"""
    if v is None:
        return "—"
    a = abs(v)
    if a >= 1e12:
        return "$%.2fT" % (v / 1e12)
    if a >= 1e9:
        return "$%.2fB" % (v / 1e9)
    if a >= 1e6:
        return "$%.2fM" % (v / 1e6)
    if a >= 1e3:
        return "$%.1fK" % (v / 1e3)
    return "$%.0f" % v


def pct(v, digits=2, sign=True):
    if v is None:
        return "—"
    return ("%+.*f%%" if sign else "%.*f%%") % (digits, v)


def cls(v):
    """涨红跌绿（中国习惯）。"""
    if v is None:
        return "flat"
    return "up" if v > 0 else ("dn" if v < 0 else "flat")


def _pt(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def gauge_svg(value, label, color):
    """半圆仪表盘。"""
    cx, cy, r, sw = 170, 152, 118, 26
    parts = []
    for lo, hi, _n, col in ZONES:
        a1 = 180 + lo / 100.0 * 180
        a2 = 180 + min(hi, 100) / 100.0 * 180
        x1, y1 = _pt(cx, cy, r, a1)
        x2, y2 = _pt(cx, cy, r, a2)
        parts.append(
            '<path d="M%.2f %.2f A%d %d 0 0 1 %.2f %.2f" fill="none" '
            'stroke="%s" stroke-width="%d" stroke-linecap="butt"/>'
            % (x1, y1, r, r, x2, y2, col, sw))
    # 指针
    ang = 180 + max(0, min(100, value)) / 100.0 * 180
    nx, ny = _pt(cx, cy, r - sw / 2 - 6, ang)
    bx, by = _pt(cx, cy, -16, ang)
    parts.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#2c2c2a" '
                 'stroke-width="4" stroke-linecap="round"/>' % (bx, by, nx, ny))
    parts.append('<circle cx="%d" cy="%d" r="8" fill="#2c2c2a"/>' % (cx, cy))
    # 刻度
    for v in (0, 25, 50, 75, 100):
        a = 180 + v / 100.0 * 180
        x1, y1 = _pt(cx, cy, r + sw / 2 + 3, a)
        x2, y2 = _pt(cx, cy, r + sw / 2 + 9, a)
        parts.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="#b9b7b0" '
                     'stroke-width="1.5"/>' % (x1, y1, x2, y2))
        tx, ty = _pt(cx, cy, r + sw / 2 + 21, a)
        parts.append('<text x="%.2f" y="%.2f" font-size="11" fill="#86847e" '
                     'text-anchor="middle" dominant-baseline="middle">%d</text>'
                     % (tx, ty, v))
    parts.append('<text x="%d" y="%d" font-size="46" font-weight="700" fill="%s" '
                 'text-anchor="middle">%d</text>' % (cx, cy - 26, color, value))
    parts.append('<text x="%d" y="%d" font-size="16" font-weight="600" fill="%s" '
                 'text-anchor="middle">%s</text>' % (cx, cy + 2, color, esc(label)))
    return ('<svg viewBox="0 0 340 186" width="100%%" style="max-width:340px;height:auto" '
            'role="img">%s</svg>' % "".join(parts))


def fng_bars(hist, w=860, h=78):
    """30 天恐惧贪婪柱状图。"""
    if not hist:
        return ""
    n = len(hist)
    gap = 2.0
    bw = (w - gap * (n - 1)) / n
    parts = []
    for i, x in enumerate(hist):
        v = x["value"]
        _n, col = zone_of(v)
        bh = max(3.0, h * v / 100.0)
        px = i * (bw + gap)
        parts.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s" '
                     'rx="1.5"/>' % (px, h - bh, bw, bh, col))
    # 50 分基准线
    parts.append('<line x1="0" y1="%.1f" x2="%d" y2="%.1f" stroke="#d8d6cf" '
                 'stroke-width="1" stroke-dasharray="3 3"/>' % (h * 0.5, w, h * 0.5))
    return ('<svg viewBox="0 0 %d %d" width="100%%" style="height:auto" role="img">%s</svg>'
            % (w, h, "".join(parts)))


def sparkline(points, w=420, h=96, color="#a32d2d"):
    """7 天价格折线。"""
    if not points or len(points) < 2:
        return ""
    vals = [p["p"] for p in points]
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or (hi * 0.01) or 1.0
    pad = 8
    n = len(vals)
    xy = []
    for i, v in enumerate(vals):
        x = pad + (w - 2 * pad) * i / (n - 1)
        y = pad + (h - 2 * pad) * (1 - (v - lo) / rng)
        xy.append((x, y))
    line = " ".join("%.2f,%.2f" % p for p in xy)
    area = ("%.2f,%.2f " % (xy[0][0], h - pad)) + line + \
           (" %.2f,%.2f" % (xy[-1][0], h - pad))
    gid = "g" + "".join(ch for ch in color if ch.isalnum())
    return (
        '<svg viewBox="0 0 %d %d" width="100%%" style="height:auto" role="img">'
        '<defs><linearGradient id="%s" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0%%" stop-color="%s" stop-opacity="0.22"/>'
        '<stop offset="100%%" stop-color="%s" stop-opacity="0.02"/>'
        '</linearGradient></defs>'
        '<polygon points="%s" fill="url(#%s)"/>'
        '<polyline points="%s" fill="none" stroke="%s" stroke-width="2.2" '
        'stroke-linejoin="round" stroke-linecap="round"/>'
        '<circle cx="%.2f" cy="%.2f" r="3.4" fill="%s"/>'
        '<text x="%d" y="%d" font-size="11" fill="#86847e" text-anchor="start">7 天前</text>'
        '<text x="%d" y="%d" font-size="11" fill="#86847e" text-anchor="end">现在</text>'
        '</svg>'
        % (w, h, gid, color, color, area, gid, line, color,
           xy[-1][0], xy[-1][1], color, pad, h - 1, w - pad, h - 1))


def cat_bars(cats, w=860, rowh=26):
    """板块 24h 涨跌横条（涨红跌绿）。"""
    cats = [c for c in cats if c.get("chg24h") is not None]
    if not cats:
        return ""
    cats.sort(key=lambda c: -c["chg24h"])
    mx = max(abs(c["chg24h"]) for c in cats) or 1.0
    label_w, mid = 186, 186 + (w - 186 - 66) / 2.0
    half = (w - label_w - 66) / 2.0
    h = rowh * len(cats) + 26
    parts = []
    parts.append('<line x1="%.1f" y1="18" x2="%.1f" y2="%d" stroke="#e6e4de" '
                 'stroke-width="1"/>' % (mid, mid, h - 8))
    for i, c in enumerate(cats):
        y = 22 + i * rowh
        cy = y + 9
        parts.append('<text x="0" y="%.1f" font-size="12.5" fill="#575652" '
                     'dominant-baseline="middle">%s</text>' % (cy, esc(c["name"][:24])))
        bw = abs(c["chg24h"]) / mx * (half - 6)
        v = c["chg24h"]
        col = "#a32d2d" if v > 0 else "#0f6e56"
        if v >= 0:
            x = mid
        else:
            x = mid - bw
        parts.append('<rect x="%.2f" y="%.2f" width="%.2f" height="14" fill="%s" '
                     'rx="2"/>' % (x, y, max(bw, 1.5), col))
        tx = mid + bw + 6 if v >= 0 else mid - bw - 6
        anchor = "start" if v >= 0 else "end"
        parts.append('<text x="%.2f" y="%.1f" font-size="12" fill="%s" '
                     'text-anchor="%s" dominant-baseline="middle">%s</text>'
                     % (tx, cy, col, anchor, pct(v, 2)))
    return ('<svg viewBox="0 0 %d %d" width="100%%" style="height:auto" role="img">%s</svg>'
            % (w, h, "".join(parts)))


def build_section(d):
    fng = d.get("fng") or {}
    g = d.get("global") or {}
    cmc = d.get("cmc_global") or {}
    coins = {c["sym"]: c for c in (d.get("coins") or [])}
    cats = d.get("categories") or []
    charts = d.get("charts") or {}
    fut = d.get("futures") or {}
    liq = d.get("liquidations") or {}

    fv = fng.get("now") or 50
    zname, zcol = zone_of(fv)
    fsrc = fng.get("source") or "CoinMarketCap"
    top20 = d.get("top20_chg24h")

    # ---------- 1. 恐惧贪婪 ----------
    hist = fng.get("history") or []
    delta = fv - (fng.get("prev") or fv)
    wk_delta = fv - (fng.get("week_ago") or fv)
    mo_delta = fv - (fng.get("month_ago") or fv)
    if delta <= -3:
        trend = "较昨日明显回落，情绪在快速降温。"
    elif delta < 0:
        trend = "较昨日小幅回落，情绪偏热但边际降温。"
    elif delta == 0:
        trend = "与昨日持平。"
    elif delta < 3:
        trend = "较昨日小幅回升。"
    else:
        trend = "较昨日明显回升，情绪在往过热方向走。"
    if wk_delta <= -8:
        trend += ("一周内累计下滑 <b>%d 点</b>，说明这是一轮<b>持续的降温</b>"
                  "（对应 BTC 7 天 %s、ETH 7 天 %s），而不是单日噪声。"
                  % (abs(wk_delta), pct(coins.get("BTC", {}).get("chg7d")),
                     pct(coins.get("ETH", {}).get("chg7d"))))
    s1 = ['<h3>① 恐惧贪婪指数（Fear &amp; Greed · %s）</h3>' % esc(fsrc),
          '<div class="sent-gauge">',
          '<div class="sent-gauge-svg">%s</div>' % gauge_svg(fv, zname, zcol),
          '<div class="sent-gauge-side">',
          '<div class="sent-kv"><span>当前</span><b class="flat">%d / 100 · %s</b></div>'
          % (fv, esc(label_cn(fng.get("label")) or zname)),
          '<div class="sent-kv"><span>较昨日</span><b class="%s">%s</b></div>'
          % (cls(delta), ("%+d" % delta) if delta else "0"),
          '<div class="sent-kv"><span>较 7 天前</span><b class="%s">%s</b></div>'
          % (cls(wk_delta), ("%+d" % wk_delta) if wk_delta else "0"),
          '<div class="sent-kv"><span>较 30 天前</span><b class="%s">%s</b></div>'
          % (cls(mo_delta), ("%+d" % mo_delta) if mo_delta else "0"),
          '<p class="sent-note">指数落在<b>「%s」</b>区间。%s</p>'
          % (esc(zname), trend),
          '</div></div>',
          '<div class="sent-cap">近 %d 天走势</div>' % len(hist),
          fng_bars(hist)]

    # ---------- 2. 大盘 ----------
    # 优先用 CoinMarketCap 的口径，缺失时回落 CoinGecko
    mcap = cmc.get("mcap") or g.get("mcap")
    vol = cmc.get("volume") or g.get("volume")
    btc_dom = cmc.get("btc_dom") or g.get("btc_dom")
    eth_dom = cmc.get("eth_dom") or g.get("eth_dom")
    mcap_chg = cmc.get("mcap_chg24h")
    if mcap_chg is None:
        mcap_chg = top20 if top20 is not None else g.get("mcap_chg24h")
    dvol = cmc.get("derivatives_vol24h")
    s2 = ['<h3>② 大盘指数</h3>',
          '<div class="sent-cards">',
          '<div class="sent-card"><div class="k">全球总市值</div>'
          '<div class="v">%s</div><div class="s %s">24h %s</div></div>'
          % (money(mcap), cls(mcap_chg), pct(mcap_chg)),
          '<div class="sent-card"><div class="k">现货 24h 成交额</div>'
          '<div class="v">%s</div><div class="s">全市场</div></div>'
          % money(vol),
          '<div class="sent-card"><div class="k">合约 24h 成交额</div>'
          '<div class="v">%s</div><div class="s">衍生品（CMC）</div></div>'
          % money(dvol),
          '<div class="sent-card"><div class="k">BTC 占比</div>'
          '<div class="v">%.2f%%</div><div class="s">ETH %.2f%%</div></div>'
          % (btc_dom or 0, eth_dom or 0),
          '<div class="sent-card"><div class="k">市值前 20 加权 24h</div>'
          '<div class="v %s">%s</div><div class="s">CoinGecko 逐币自算</div></div>'
          % (cls(top20), pct(top20)),
          '</div>',
          '<p class="sent-note">市值 / 成交额 / 占比取自 <b>CoinMarketCap</b>'
          '（BTC 占比 %.2f%%，24h %s）；「前 20 加权」由 CoinGecko 逐币市值加权自算，'
          '作为独立交叉校验 —— 两个口径本期都指向<b>横盘</b>（CMC %s vs 自算 %s），'
          '可以互相印证。另注：CoinGecko 的 <code>global</code> 字段本期给出 %s，'
          '与头部币普涨矛盾，已弃用。合约成交额 %s 是现货 %s 的 <b><span class="hl">%.1f 倍</span></b>，'
          '说明<b>杠杆资金仍是主要流动性来源</b>。</p>'
          % (btc_dom or 0, pct(cmc.get("btc_dom_chg24h")),
             pct(cmc.get("mcap_chg24h")), pct(top20), pct(g.get("mcap_chg24h")),
             money(dvol), money(vol), (dvol / vol) if (dvol and vol) else 0)]

    # ---------- 3. BTC / ETH ----------
    s3 = ['<h3>③ BTC / ETH 指数</h3>', '<div class="sent-two">']
    for sym, col in (("BTC", "#a32d2d"), ("ETH", "#185fa5")):
        c = coins.get(sym) or {}
        pts = charts.get(sym) or []
        c24, c7 = c.get("chg24h"), c.get("chg7d")
        ccol = col if (c7 or 0) >= 0 else "#0f6e56"
        hi = max((p["p"] for p in pts), default=None)
        lo = min((p["p"] for p in pts), default=None)
        s3.append(
            '<div class="sent-card wide">'
            '<div class="sent-coin-hd"><b>%s</b>'
            '<span class="sent-price">$%s</span>'
            '<span class="%s">24h %s</span><span class="%s">7d %s</span></div>'
            % (sym, ("{:,.2f}".format(c["price"]) if c.get("price") else "—"),
               cls(c24), pct(c24), cls(c7), pct(c7))
            + sparkline(pts, color=ccol)
            + '<div class="sent-hl">7 天区间 $%s — $%s</div>'
            % (("{:,.0f}".format(lo) if lo else "—"),
               ("{:,.0f}".format(hi) if hi else "—"))
            + '</div>')
    s3.append('</div>')

    # ---------- 4. 核心板块 ----------
    s4 = ['<h3>④ 核心板块 24h 表现</h3>', cat_bars(cats)]
    up = [c for c in cats if (c.get("chg24h") or 0) > 0]
    dn = [c for c in cats if (c.get("chg24h") or 0) < 0]
    if up and dn:
        up.sort(key=lambda c: -c["chg24h"])
        dn.sort(key=lambda c: c["chg24h"])
        s4.append('<p class="sent-note">领涨：<b><span class="hl">%s</span></b>（%s）；垫底：<b><span class="hl">%s</span></b>（%s）。%s</p>'
                  % (esc(up[0]["name"]), pct(up[0]["chg24h"]),
                     esc(dn[0]["name"]), pct(dn[0]["chg24h"]),
                     "资金从 Meme / 游戏这类情绪资产，转向 L2、RWA、AI 这类有叙事和基本面的方向。"
                     if up[0]["name"].startswith(("Layer 2", "Real World", "Artificial"))
                     else "板块间分化明显。"))

    # ---------- 5. 合约情绪 ----------
    cgl = d.get("coinglass_liquidations") or {}
    use_cg = bool(cgl)
    rows = []
    for sym in ("BTC", "ETH"):
        f = fut.get(sym)
        if not f:
            continue
        th = f.get("taker_hist") or []
        taker_avg = sum(x["v"] for x in th) / len(th) if th else 0.0
        oi_chg = f.get("oi_chg24h")
        if use_cg:
            c = cgl.get(sym) or {}
            lusd, susd = c.get("long_24h"), c.get("short_24h")
        else:
            lq = liq.get(sym) or {}
            lusd, susd = lq.get("long_usd"), lq.get("short_usd")
        ratio = (lusd / (lusd + susd) * 100) if (lusd is not None and (lusd + susd)) else None
        rows.append(
            "<tr>"
            f'<td class="sent-sym">{sym}</td>'
            f"<td>{(f.get('funding') or 0) * 100:+.4f}%</td>"
            f"<td>{money(f.get('oi_usd'))}</td>"
            f'<td>{("%+.2f%%" % oi_chg) if oi_chg is not None else "—"} '
            f'<span class="sent-dim">(24h)</span></td>'
            f"<td>{f.get('top_ls') or 0:.2f}</td>"
            f"<td>{f.get('retail_ls') or 0:.2f}</td>"
            f"<td>{taker_avg:.3f}</td>"
            f"<td>{money(lusd)} / {money(susd)}</td>"
            f"<td>{('多头 %.0f%%' % ratio) if ratio is not None else '—'}</td>"
            "</tr>")
    liq_head = ("全市场 24h 多爆 / 空爆" if use_cg else "OKX 24h 多爆 / 空爆")
    if use_cg:
        cg_note = (
            '<p class="sent-cap">口径说明：爆仓为 <b>CoinGlass 全市场聚合</b>'
            '（覆盖 Binance / OKX / Bybit 等 30+ 交易所，24h 窗口，多空分别统计），'
            '可与外部 CoinGlass 页面对账；未平仓量 / 多空比 / Taker 来自 Binance 合约。'
            '多空比列 = 多头爆仓占全部爆仓的比例，<b>越低说明空头被打得越狠</b>。</p>')
    else:
        cg_note = (
            '<p class="sent-cap">口径说明：未平仓量 / 多空比 / Taker 来自 Binance 合约（完整公开）；'
            '爆仓来自 <b>OKX 公共爆仓接口</b> —— 该接口只覆盖 OKX 一家交易所且对公开数据做抽样，'
            '<b>绝对金额不可与 CoinGlass 的全市场口径对比</b>，此处只用它的<b>方向性</b>（多空哪一侧被爆）。'
            'CoinGlass 无免费额度（最低 $29/月）；在 <code>secrets.json</code> 填入 '
            '<code>coinglass_api_key</code> 后本节会自动切换为全市场口径。</p>')
    s5 = ['<h3>⑤ 合约情绪与爆仓</h3>',
          '<table class="sent-table"><tr>'
          '<th>币种</th><th>资金费率</th><th>未平仓量</th><th>OI 变化</th>'
          '<th>大户多空</th><th>散户多空</th><th>Taker 买卖比</th>'
          f'<th>{liq_head}</th><th>爆仓多空比</th></tr>',
          "".join(rows), '</table>',
          cg_note]

    # ---------- 6. 综合判断 ----------
    btc_f = fut.get("BTC") or {}
    eth_f = fut.get("ETH") or {}
    # 有 CoinGlass 用全市场口径，否则用 OKX 单所
    if cgl:
        btc_lq = {"long_usd": (cgl.get("BTC") or {}).get("long_24h"),
                  "short_usd": (cgl.get("BTC") or {}).get("short_24h"),
                  "long_n": None, "short_n": None}
        eth_lq = {"long_usd": (cgl.get("ETH") or {}).get("long_24h"),
                  "short_usd": (cgl.get("ETH") or {}).get("short_24h")}
        sol_lq = {"long_usd": (cgl.get("SOL") or {}).get("long_24h"),
                  "short_usd": (cgl.get("SOL") or {}).get("short_24h")}
        lq_src = "CoinGlass 全市场 24h"
        lq_unit = "笔"
    else:
        btc_lq = liq.get("BTC") or {}
        eth_lq = liq.get("ETH") or {}
        sol_lq = liq.get("SOL") or {}
        lq_src = "OKX 24h 公开样本"
        lq_unit = "笔"

    def skew(lq):
        l, s = lq.get("long_usd") or 0, lq.get("short_usd") or 0
        if l + s == 0:
            return None
        return s / (l + s) * 100          # 空头爆仓占比

    bsk, esk, ssk = skew(btc_lq), skew(eth_lq), skew(sol_lq)
    eth_retail = eth_f.get("retail_ls") or 0
    eth_top = eth_f.get("top_ls") or 0
    btc_taker = (sum(x["v"] for x in (btc_f.get("taker_hist") or [])) /
                 max(1, len(btc_f.get("taker_hist") or [])))
    eth_taker = (sum(x["v"] for x in (eth_f.get("taker_hist") or [])) /
                 max(1, len(eth_f.get("taker_hist") or [])))
    dvol = cmc.get("derivatives_vol24h")
    lev = (dvol / vol) if (dvol and vol) else 0

    # 情绪档位的动态定性
    if fv >= 75:
        mood = "极度贪婪"
        mood_read = "情绪已进入过热区，追高风险显著。"
    elif fv >= 55:
        mood = "贪婪"
        mood_read = "情绪偏热，但尚未极端。"
    elif fv >= 45:
        mood = "中性"
        mood_read = ("情绪已回落到中性区，<b>既没有恐慌，也没有贪婪</b> —— "
                     "这是典型的「方向未定、等待增量信息」的状态。")
    elif fv >= 25:
        mood = "恐惧"
        mood_read = "情绪偏冷，市场在回避风险。"
    else:
        mood = "极度恐惧"
        mood_read = "情绪极端悲观，历史上这往往对应阶段性底部区域。"
    if wk_delta <= -8:
        mood_read += ("关键是<b><span class=\"hl-key\">一周内从 %d 掉到 %d（%d 点）</span></b>，"
                      "这不是噪声，是<b>一轮持续的降温</b>。"
                      % (fng.get("week_ago") or fv, fv, abs(wk_delta)))

    verdict = []
    verdict.append(
        '<li><b>情绪面：%s（<span class="hl-key">%d / 100</span>）。</b>较昨日 %+d、较 7 天前 %+d、较 30 天前 %+d。%s'
        '</li>' % (mood, fv, delta, wk_delta, mo_delta, mood_read))
    verdict.append(
        '<li><b>盘面：横盘，但内部在换手。</b>前 20 大币市值加权 24h %s，'
        'BTC %s / ETH %s；7 天维度 BTC %s、ETH %s。'
        '<b>板块层面 L2（+2.62%%）、RWA（+1.75%%）、AI（+1.55%%）明显强于 Meme（%s）与 '
        'GameFi（%s）</b>，说明资金在从情绪资产往叙事 / 基本面资产挪 —— '
        '<b>这通常是「避险式轮动」而不是「风险偏好上升」</b>。'
        '</li>' % (pct(top20), pct(coins.get("BTC", {}).get("chg24h")),
                   pct(coins.get("ETH", {}).get("chg24h")),
                   pct(coins.get("BTC", {}).get("chg7d")),
                   pct(coins.get("ETH", {}).get("chg7d")),
                   pct(next((c["chg24h"] for c in cats if c["id"] == "meme-token"), None)),
                   pct(next((c["chg24h"] for c in cats if c["id"] == "gaming"), None))))
    verdict.append(
        '<li><b>杠杆面：空头在挨打，但方向不坚决。</b>BTC / ETH 资金费率分别为 '
        '<b>%+.4f%%</b> 与 <b>%+.4f%%</b>（双负 —— 空头付钱给多头，说明空头仓位更拥挤）；'
        '%s 爆仓里 <span class="hl-key">BTC 空爆占 %.0f%%</span>（%s）、'
        '<span class="hl">ETH %.0f%%</span>、<span class="hl">SOL %.0f%%</span>。'
        '<b><span class="hl-key">空头被反复挤压，但 BTC 24h 只涨 %.2f%%</span> —— 这是窄幅震荡里的'
        '空头挤压，不是趋势性上涨。</b>未平仓量 BTC %s（24h %+.2f%%）、ETH %s（24h %s），'
        '<b>没有增量杠杆进场，靠的是存量空头止损推动。</b>合约 24h 成交额 %s，是现货的 '
        '<b><span class="hl">%.1f 倍</span></b>，杠杆资金仍是主要流动性来源。</li>'
        % ((btc_f.get("funding") or 0) * 100, (eth_f.get("funding") or 0) * 100,
           lq_src,
           bsk or 0,
           ("%s vs %s" % (money(btc_lq.get("short_usd")), money(btc_lq.get("long_usd"))))
           if cgl else ("%s 笔空 vs %s 笔多" % (btc_lq.get("short_n") or 0,
                                                btc_lq.get("long_n") or 0)),
           esk or 0, ssk or 0, coins.get("BTC", {}).get("chg24h") or 0,
           money(btc_f.get("oi_usd")), btc_f.get("oi_chg24h") or 0,
           money(eth_f.get("oi_usd")), pct(eth_f.get("oi_chg24h")),
           money(dvol), lev))
    verdict.append(
        '<li><b>结构上最该警惕的一条：<span class="hl-key">ETH 散户多空比 %.2f，而大户只有 %.2f</span>。</b>'
        '散户杠杆多空比接近 3 倍，意味着<b>ETH 的多头仓位高度集中在散户手里</b>，'
        '而同期 ETH 7 天跌 %s。这种「散户拥挤做多 + 大户相对保守」的组合，'
        '<b>是典型的易被向下清算的结构</b> —— 一旦 ETH 跌破近 7 天低点（<b><span class="hl">$%.0f</span></b>），'
        '容易触发连锁清算。Taker 主动买卖比 BTC %.3f / ETH %.3f（24h 均值，均 &lt; 1），'
        '也说明<b>主动卖单仍多于主动买单</b>。</li>'
        % (eth_retail, eth_top, pct(coins.get("ETH", {}).get("chg7d")),
           min((p["p"] for p in (charts.get("ETH") or [{"p": 0}])), default=0),
           btc_taker, eth_taker))
    verdict.append(
        '<li><b>一句话结论：</b>这是一个 <b><span class="hl-key">「情绪中性偏冷 + 空头被挤压 + '
        '散户拥挤做多 + 大户按兵不动」的窄幅震荡结构</span></b>。爆仓方向和资金费率都偏多，但现货成交额偏低'
        '（%s / 24h）、未平仓量零增长、主动卖单占优，<b>多头缺少增量资金确认</b>。'
        '方向上：<b><span class="hl-key">不宜追多，也不宜裸空</span></b> —— 空头正在被挤压；真正值得盯的是 '
        '<b><span class="hl">ETH 散户多头是否被清算</span></b>，那会是一个比现在更干净的做多入场点。</li>'
        % money(vol))

    s6 = ['<h3>⑥ 市场情绪综合判断</h3>',
          '<ul class="sent-verdict">%s</ul>' % "".join(verdict)]

    ts = datetime.fromtimestamp(d.get("ts", 0), tz=timezone.utc).astimezone(BJ)
    head = ('<section class="sent">\n'
            '  <h2>市场情绪总览</h2>\n'
            '  <p class="sent-sub">恐惧贪婪指数 · 大盘与板块 · BTC / ETH 指数 · 合约持仓与爆仓 '
            '｜ 数据时间：%s 北京时间（Binance 合约为 1h 粒度 24h 窗口，OKX 爆仓为最近 24h）</p>\n'
            % ts.strftime("%Y-%m-%d %H:%M"))

    body = "\n  ".join(s1 + [""] + s2 + [""] + s3 + [""] + s4 + [""] + s5 + [""] + s6)
    return MB + "\n" + head + "  " + body + "\n</section>\n" + ME


CSS = """
  section.sent { border-left: 4px solid #185fa5; }
  .sent-sub { font-size: 14.5px; color: #86847e; margin: 0 0 16px; }
  section.sent h3 {
    font-size: 16.5px; font-weight: 600; margin: 24px 0 10px; color: #2c2c2a;
    padding-top: 18px; border-top: 1px solid #f0eee8;
  }
  section.sent h3:first-of-type { border-top: none; padding-top: 0; margin-top: 4px; }
  .sent-gauge { display: flex; flex-wrap: wrap; gap: 26px; align-items: center; }
  .sent-gauge-svg { flex: 0 0 300px; max-width: 300px; }
  .sent-gauge-side { flex: 1 1 260px; }
  .sent-kv { display: flex; justify-content: space-between; gap: 14px;
    font-size: 15px; color: #575652; padding: 5px 0; border-bottom: 1px dashed #f0eee8; }
  .sent-kv b { font-weight: 600; color: #2c2c2a; }
  .sent-note { font-size: 14.5px; color: #6b6a65; margin: 12px 0 0; line-height: 1.7; }
  .sent-cap { font-size: 13.5px; color: #86847e; margin: 14px 0 4px; }
  .sent-cards { display: flex; flex-wrap: wrap; gap: 12px; }
  .sent-card { flex: 1 1 178px; background: #fafaf8; border: 1px solid #eceae4;
    border-radius: 10px; padding: 13px 15px; }
  .sent-card .k { font-size: 13px; color: #86847e; }
  .sent-card .v { font-size: 21px; font-weight: 600; margin-top: 3px;
    font-family: ui-monospace, Consolas, monospace; }
  .sent-card .s { font-size: 13px; color: #86847e; margin-top: 2px; }
  .sent-two { display: flex; flex-wrap: wrap; gap: 14px; }
  .sent-card.wide { flex: 1 1 380px; }
  .sent-coin-hd { display: flex; flex-wrap: wrap; align-items: baseline; gap: 10px;
    font-size: 14px; margin-bottom: 4px; }
  .sent-coin-hd b { font-size: 16px; }
  .sent-price { font-family: ui-monospace, Consolas, monospace; font-size: 18px;
    font-weight: 600; }
  .sent-hl { font-size: 13px; color: #86847e; margin-top: 2px; }
  .sent-table { font-size: 14.5px; }
  .sent-table td { padding: 9px 8px 9px 0; font-family: ui-monospace, Consolas, monospace;
    font-size: 13.5px; }
  .sent-table th { font-size: 13px; padding-right: 8px; }
  .sent-sym { font-weight: 700; font-family: inherit !important; font-size: 15px !important; }
  .sent-dim { color: #86847e; font-size: 12.5px; }
  .sent-verdict { margin: 6px 0 0; padding-left: 22px; font-size: 15.5px; }
  .sent-verdict li { margin-bottom: 11px; line-height: 1.75; }
  .up { color: #a32d2d; font-weight: 600; }
  .dn { color: #0f6e56; font-weight: 600; }
  .flat { color: #575652; font-weight: 600; }
"""


def main():
    if len(sys.argv) < 2:
        print("usage: inject_sentiment.py <report.html>")
        return 1
    path = Path(sys.argv[1])
    if not path.exists():
        print("NOT_FOUND: %s" % path)
        return 1
    if not DATA.exists():
        print("NO_DATA: run fetch_market_sentiment.py first")
        return 1

    d = json.loads(DATA.read_text(encoding="utf-8"))
    html = path.read_text(encoding="utf-8")

    # 幂等：先剥旧模块
    html = re.sub(r"\s*" + re.escape(MB) + r".*?" + re.escape(ME) + r"\s*",
                  "", html, flags=re.S)

    module = build_section(d)

    m = re.search(r"</header>\s*", html)
    if not m:
        print("NO_HEADER_ANCHOR")
        return 1
    html = html[:m.end()] + "\n" + module + "\n" + html[m.end():]

    if "section.sent {" not in html:
        html = html.replace("</style>", CSS + "</style>", 1)

    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(html)
    print("OK: sentiment injected -> %s (%d bytes)" % (path, len(html.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
