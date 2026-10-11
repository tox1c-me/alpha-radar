# -*- coding: utf-8 -*-
"""市场情绪数据抓取 —— 恐惧贪婪指数 / 大盘 / 板块 / 合约持仓 / 爆仓。

数据源（全部免密钥）：
  - 恐惧贪婪指数：api.alternative.me/fng   （CoinMarketCap 页面同源指数）
  - 大盘 / 币价 / 板块：api.coingecko.com
  - 爆仓明细：OKX 公共 API  /api/v5/public/liquidation-orders
  - 合约情绪：Binance 合约公共 API（资金费率 / 未平仓量 / 多空比 / 主动买卖比）

产出：raw/market_sentiment.json
"""
import json
import os
import socket
import time
import urllib.error
import urllib.request

from config import PROXY, RAW_DIR, secrets as _secrets

OUT = str(RAW_DIR)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36")

# OKX 永续合约面值（1 张 = N 个币）
CT_VAL = {"BTC": 0.01, "ETH": 0.1, "SOL": 1.0, "XRP": 100.0, "DOGE": 1000.0}


SECRET = _secrets()
CMC_KEY = SECRET.get("coinmarketcap_api_key") or os.environ.get("CMC_API_KEY", "")
CG_KEY = SECRET.get("coinglass_api_key") or os.environ.get("COINGLASS_API_KEY", "")


def _proxy_alive():
    s = socket.socket()
    s.settimeout(1.2)
    try:
        s.connect(("127.0.0.1", 7897))
        return True
    except Exception:
        return False
    finally:
        s.close()


if _proxy_alive():
    OPENER = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
else:
    OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
OPENER.addheaders = [("User-Agent", UA), ("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")]


def get_json(url, timeout=30, tries=3, headers=None):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url)
            for k, v in (headers or {}).items():
                req.add_header(k, v)
            return json.loads(OPENER.open(req, timeout=timeout).read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            last = e
            # 429 限流要给足退避，否则连续几次都被拒
            wait = (8, 20, 40)[i] if e.code == 429 else 1.5 * (i + 1)
            time.sleep(wait)
        except Exception as e:            # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    print("  ERR", url[:90], last, flush=True)
    return None


CMC_HDR = {"Origin": "https://coinmarketcap.com", "Referer": "https://coinmarketcap.com/"}
CMC_ZONE = [(0, 25, "Extreme Fear"), (25, 45, "Fear"), (45, 55, "Neutral"),
            (55, 75, "Greed"), (75, 101, "Extreme Greed")]

# CoinMarketCap 官方 API。有 key 走认证端点，没有 key 走官方 Keyless（/public-api 前缀，免账号）。
CMC_BASE = "https://pro-api.coinmarketcap.com"
CMC_PREFIX = "" if CMC_KEY else "/public-api"
CMC_AUTH = {"X-CMC_PRO_API_KEY": CMC_KEY} if CMC_KEY else {}
CMC_CHANNEL = "官方 API（已认证）" if CMC_KEY else "官方 Keyless（免密钥）"


def cmc_get(path, params=""):
    """走 CMC 官方接口（认证或 Keyless）。"""
    hdr = dict(CMC_HDR)
    hdr.update(CMC_AUTH)
    return get_json(CMC_BASE + CMC_PREFIX + path + params, headers=hdr)


def _cmc_label(v):
    for lo, hi, n in CMC_ZONE:
        if lo <= v < hi:
            return n
    return "Extreme Greed"


def cmc_fng(days=30):
    """CoinMarketCap 恐惧贪婪指数（官方 API，30 天历史）。"""
    d = cmc_get("/v3/fear-and-greed/historical", f"?count={days}")
    rows = None
    if d and isinstance(d.get("data"), list) and d["data"]:
        rows = [{"value": int(x["value"]),
                 "label": x.get("value_classification") or _cmc_label(int(x["value"])),
                 "ts": int(x["timestamp"])} for x in d["data"]]
    if not rows:                          # 回落 CMC 站点内部接口
        now = int(time.time())
        d2 = get_json("https://api.coinmarketcap.com/data-api/v3/fear-greed/chart"
                      f"?start={now - (days + 8) * 86400}&end={now}", headers=CMC_HDR)
        if d2 and d2.get("data", {}).get("dataList"):
            rows = [{"value": int(x["score"]),
                     "label": x.get("name") or _cmc_label(int(x["score"])),
                     "ts": int(x["timestamp"])} for x in d2["data"]["dataList"]]
    if not rows:
        return None
    rows.sort(key=lambda r: r["ts"])
    rows = rows[-days:]
    now_r = rows[-1]
    prev = rows[-2] if len(rows) > 1 else now_r
    wk = rows[-8] if len(rows) >= 8 else rows[0]
    return {"source": "CoinMarketCap", "channel": CMC_CHANNEL,
            "now": now_r["value"], "label": now_r["label"],
            "prev": prev["value"], "week_ago": wk["value"], "month_ago": rows[0]["value"],
            "history": rows}


def fng(days=30):
    """恐惧贪婪指数：优先 CoinMarketCap 自有指数，失败回落 alternative.me。"""
    c = cmc_fng(days)
    if c:
        return c
    print("  CMC F&G 失败，回落 alternative.me", flush=True)
    d = get_json("https://api.alternative.me/fng/?limit=%d" % days)
    if not d or "data" not in d:
        return None
    hist = [{"value": int(x["value"]), "label": x["value_classification"],
             "ts": int(x["timestamp"])} for x in d["data"]]
    hist.reverse()
    now_r = hist[-1]
    prev = hist[-2] if len(hist) > 1 else now_r
    wk = hist[-8] if len(hist) >= 8 else hist[0]
    return {"source": "alternative.me", "now": now_r["value"], "label": now_r["label"],
            "prev": prev["value"], "week_ago": wk["value"], "month_ago": hist[0]["value"],
            "history": hist}


def cmc_global():
    """CoinMarketCap 全市场指标（官方接口优先，站点内部接口兜底）。"""
    d = cmc_get("/v1/global-metrics/quotes/latest")
    if d and isinstance(d.get("data"), dict) and d["data"].get("quote"):
        x = d["data"]
        q = x["quote"].get("USD") or {}
        return {
            "mcap": q.get("total_market_cap"),
            "mcap_chg24h": q.get("total_market_cap_yesterday_percentage_change"),
            "volume": q.get("total_volume_24h"),
            "volume_reported": q.get("total_volume_24h_reported"),
            "volume_chg24h": q.get("total_volume_24h_yesterday_percentage_change"),
            "btc_dom": x.get("btc_dominance"),
            "eth_dom": x.get("eth_dominance"),
            "btc_dom_chg24h": x.get("btc_dominance_24h_percentage_change"),
            "derivatives_vol24h": x.get("derivatives_volume_24h"),
            "derivatives_chg24h": x.get("derivatives_24h_percentage_change"),
            "stablecoin_vol24h": x.get("stablecoin_volume_24h"),
            "defi_mcap": x.get("defi_market_cap"),
            "channel": CMC_CHANNEL,
        }
    # 兜底：站点内部 data-api
    d2 = get_json("https://api.coinmarketcap.com/data-api/v3/global-metrics/quotes/latest",
                  headers=CMC_HDR)
    if not d2 or "data" not in d2:
        return None
    x = d2["data"]
    qs = x.get("quotes") or []
    q = qs[0] if isinstance(qs, list) and qs else (qs if isinstance(qs, dict) else {})
    return {
        "mcap": q.get("totalMarketCap"),
        "mcap_chg24h": q.get("totalMarketCapYesterdayPercentageChange"),
        "volume": q.get("totalVolume24H"),
        "volume_reported": q.get("totalVolume24HReported"),
        "volume_chg24h": q.get("totalVolume24HYesterdayPercentageChange"),
        "btc_dom": x.get("btcDominance"),
        "eth_dom": x.get("ethDominance"),
        "btc_dom_chg24h": x.get("btcDominance24hPercentageChange"),
        "derivatives_vol24h": q.get("derivativesVolume24H"),
        "derivatives_chg24h": q.get("derivatives24HPercentageChange"),
        "stablecoin_vol24h": q.get("stablecoinVolume24H"),
        "defi_mcap": q.get("defiMarketCap"),
        "channel": "站点内部 data-api（兜底）",
    }


# ------------------------------------------------------------ CoinGlass（需 API Key）
CG_BASE = "https://open-api-v4.coinglass.com"


def cg_get(path, params=""):
    if not CG_KEY:
        return None
    return get_json(CG_BASE + path + params,
                    headers={"CG-API-KEY": CG_KEY, "accept": "application/json"})


def coinglass_liquidations():
    """CoinGlass 全市场爆仓（1h/4h/12h/24h 多空分别统计）—— 需 API Key。

    端点：/api/futures/liquidation/coin-list
    """
    d = cg_get("/api/futures/liquidation/coin-list")
    if not d or str(d.get("code")) not in ("0", "200"):
        return None
    rows = d.get("data") or []
    out = {}
    for r in rows:
        sym = (r.get("symbol") or "").upper()
        if sym not in ("BTC", "ETH", "SOL", "XRP", "DOGE", "BNB"):
            continue
        out[sym] = {
            "long_1h": r.get("long_liquidation_usd_1h"),
            "short_1h": r.get("short_liquidation_usd_1h"),
            "long_4h": r.get("long_liquidation_usd_4h"),
            "short_4h": r.get("short_liquidation_usd_4h"),
            "long_12h": r.get("long_liquidation_usd_12h"),
            "short_12h": r.get("short_liquidation_usd_12h"),
            "long_24h": r.get("long_liquidation_usd_24h"),
            "short_24h": r.get("short_liquidation_usd_24h"),
        }
    return out or None


def coinglass_ratio():
    """CoinGlass 合约/现货成交量比值 + 山寨季指数（需 API Key）。"""
    out = {}
    r = cg_get("/api/futures_spot_volume_ratio")
    if r and str(r.get("code")) in ("0", "200") and r.get("data"):
        out["futures_spot_ratio"] = r["data"]
    a = cg_get("/api/index/altcoin-season")
    if a and str(a.get("code")) in ("0", "200") and a.get("data"):
        out["altcoin_season"] = a["data"]
    return out or None


def coingecko():
    time.sleep(1.0)
    g = get_json("https://api.coingecko.com/api/v3/global")
    out = {}
    if g and "data" in g:
        d = g["data"]
        out["global"] = {
            "mcap": d["total_market_cap"]["usd"],
            "mcap_chg24h": d.get("market_cap_change_percentage_24h_usd"),
            "volume": d["total_volume"]["usd"],
            "btc_dom": d["market_cap_percentage"]["btc"],
            "eth_dom": d["market_cap_percentage"]["eth"],
            "coins": d.get("active_cryptocurrencies"),
        }
    time.sleep(4.0)
    mk = get_json("https://api.coingecko.com/api/v3/coins/markets"
                  "?vs_currency=usd&order=market_cap_desc&per_page=20&page=1"
                  "&price_change_percentage=24h,7d")
    if mk:
        out["coins"] = [{
            "sym": c["symbol"].upper(), "name": c["name"],
            "price": c["current_price"],
            "chg24h": c.get("price_change_percentage_24h"),
            "chg7d": c.get("price_change_percentage_7d_in_currency"),
            "mcap": c.get("market_cap"), "vol": c.get("total_volume"),
        } for c in mk]
    time.sleep(4.0)
    cat = get_json("https://api.coingecko.com/api/v3/coins/categories")
    if cat:
        keep = {"layer-1", "layer-2", "decentralized-finance-defi", "meme-token",
                "artificial-intelligence", "real-world-assets-rwa",
                "stablecoins", "solana-ecosystem", "gaming", "privacy-coins",
                "exchange-based-tokens", "yield-farming"}
        out["categories"] = [{
            "id": c["id"], "name": c["name"],
            "mcap": c.get("market_cap"), "chg24h": c.get("market_cap_change_24h"),
            "vol": c.get("volume_24h"),
        } for c in cat if c["id"] in keep]
    # 价格走势（7 天，小时级 -> 每 6 小时取样一次，控制体积）
    charts = {}
    for cid, sym in (("bitcoin", "BTC"), ("ethereum", "ETH")):
        time.sleep(4.0)                   # CoinGecko 免费档限速，间隔拉开发
        ch = get_json(f"https://api.coingecko.com/api/v3/coins/{cid}/market_chart"
                      f"?vs_currency=usd&days=7&interval=hourly")
        if ch and "prices" in ch:
            pts = ch["prices"][::6]
            charts[sym] = [{"t": int(p[0]), "p": p[1]} for p in pts]
            charts[sym + "_mcap"] = [{"t": int(p[0]), "p": p[1]}
                                     for p in ch.get("market_caps", [])[::6]]
    if charts:
        out["charts"] = charts
    # 大盘 24h 变化：CoinGecko 的 global 字段偶发滞后，另算 top-20 市值加权作交叉校验
    if mk:
        num = den = 0.0
        for c in mk:
            ch = c.get("price_change_percentage_24h")
            mc = c.get("market_cap") or 0
            if ch is None or not mc:
                continue
            num += mc / (1 + ch / 100.0)
            den += mc
        if den:
            out["top20_chg24h"] = (den / num - 1) * 100
    return out


def okx_liquidations(max_pages=10):
    """OKX 公共爆仓明细 —— 翻页取满最近 24 小时（每页 100 笔，用 after=最早 ts 往前翻）。

    注意：OKX 只公开自己交易所的爆仓单，且单页上限 100 条。
    本函数翻页直到跨越 24h 或翻完 max_pages，得到一个「OKX 口径的 24h 爆仓」样本。
    这不是全市场数据（全市场需 CoinGlass，其接口已需密钥），报告中须标注口径。
    """
    res = {}
    for ccy in ("BTC", "ETH", "SOL"):
        cv = CT_VAL.get(ccy, 1.0)
        rows, after = [], ""
        for _ in range(max_pages):
            u = ("https://www.okx.com/api/v5/public/liquidation-orders"
                 f"?instType=SWAP&uly={ccy}-USDT&state=filled&limit=100")
            if after:
                u += "&after=" + after
            d = get_json(u, tries=2)
            if not d or d.get("code") != "0":
                break
            page = [x for g in d.get("data", []) for x in (g.get("details") or [])]
            if not page:
                break
            rows += page
            ts = [int(x["ts"]) for x in page]
            after = str(min(ts))
            if max(ts) - min(ts) > 24 * 3600 * 1000:
                break
            time.sleep(0.7)
        if not rows:
            continue
        dedup = {int(x["ts"]): x for x in rows}          # 去重（翻页边界会重叠）
        rows = []
        for x in dedup.values():
            sz = float(x.get("sz") or 0) * cv
            px = float(x.get("bkPx") or 0)
            rows.append({"side": x.get("posSide"), "coin": sz,
                         "px": px, "usd": sz * px, "t": int(x.get("ts") or 0)})
        rows.sort(key=lambda r: r["t"])
        # 只保留最近 24h
        cutoff = rows[-1]["t"] - 24 * 3600 * 1000
        rows = [r for r in rows if r["t"] >= cutoff]
        longs = [r for r in rows if r["side"] == "long"]
        shorts = [r for r in rows if r["side"] == "short"]
        res[ccy] = {
            "n": len(rows),
            "window_h": round((rows[-1]["t"] - rows[0]["t"]) / 3600000, 1),
            "newest": rows[-1]["t"],
            "long_usd": sum(r["usd"] for r in longs),
            "short_usd": sum(r["usd"] for r in shorts),
            "long_n": len(longs), "short_n": len(shorts),
            "largest": max(rows, key=lambda r: r["usd"]),
            "px_lo": min(r["px"] for r in rows),
            "px_hi": max(r["px"] for r in rows),
        }
    return res


def binance_futures():
    res = {}
    for sym in ("BTCUSDT", "ETHUSDT"):
        d = {}
        pi = get_json(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={sym}")
        if pi:
            d["mark"] = float(pi["markPrice"])
            d["funding"] = float(pi["lastFundingRate"])
            d["next_funding"] = pi.get("nextFundingTime")
        oi = get_json("https://fapi.binance.com/futures/data/openInterestHist"
                      f"?symbol={sym}&period=1h&limit=25")
        if oi:
            d["oi_usd"] = float(oi[-1]["sumOpenInterestValue"])
            d["oi_btc"] = float(oi[-1]["sumOpenInterest"])
            d["oi_chg24h"] = (float(oi[-1]["sumOpenInterestValue"]) /
                              float(oi[0]["sumOpenInterestValue"]) - 1) * 100
            d["oi_hist"] = [{"t": x["timestamp"],
                             "v": float(x["sumOpenInterestValue"])} for x in oi]
        ls = get_json("https://fapi.binance.com/futures/data/topLongShortPositionRatio"
                      f"?symbol={sym}&period=1h&limit=25")
        if ls:
            d["top_ls"] = float(ls[-1]["longShortRatio"])
            d["top_long_pct"] = float(ls[-1]["longAccount"]) * 100
            d["top_ls_hist"] = [{"t": x["timestamp"],
                                 "v": float(x["longShortRatio"])} for x in ls]
        gl = get_json("https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
                      f"?symbol={sym}&period=1h&limit=25")
        if gl:
            d["retail_ls"] = float(gl[-1]["longShortRatio"])
            d["retail_long_pct"] = float(gl[-1]["longAccount"]) * 100
        tk = get_json("https://fapi.binance.com/futures/data/takerlongshortRatio"
                      f"?symbol={sym}&period=1h&limit=25")
        if tk:
            d["taker_ratio"] = float(tk[-1]["buySellRatio"])
            d["taker_buy"] = float(tk[-1]["buyVol"])
            d["taker_sell"] = float(tk[-1]["sellVol"])
            d["taker_hist"] = [{"t": x["timestamp"],
                                "v": float(x["buySellRatio"])} for x in tk]
        t24 = get_json(f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={sym}")
        if t24:
            d["fut_vol24h_usd"] = float(t24["quoteVolume"])
            d["fut_chg24h"] = float(t24["priceChangePercent"])
        if d:
            res[sym.replace("USDT", "")] = d
    return res


def main():
    out = {"ts": int(time.time())}
    prev = {}
    p_old = os.path.join(OUT, "market_sentiment.json")
    if os.path.exists(p_old):
        try:
            prev = json.load(open(p_old, encoding="utf-8"))
        except Exception:                 # noqa: BLE001
            prev = {}

    print("[1/5] 恐惧贪婪指数（CoinMarketCap）...", flush=True)
    out["fng"] = fng()
    if out["fng"]:
        f = out["fng"]
        print("    源", f["source"], "|", f.get("channel", ""), "|", f["now"], f["label"],
              "| 昨", f["prev"], "| 7天前", f["week_ago"],
              "| 30天前", f["month_ago"], "| 样本", len(f["history"]))
    print("[2/5] CoinGecko 大盘 / 币价 / 板块 / 走势 ...", flush=True)
    cg = coingecko()
    out.update(cg)
    if cg.get("global"):
        g = cg["global"]
        print("    mcap %.2fT | 24h %s%% | vol %.1fB | BTC.D %.1f%%" % (
            g["mcap"] / 1e12, g["mcap_chg24h"], g["volume"] / 1e9, g["btc_dom"]))
    print("    币价", len(cg.get("coins") or []), "| 板块", len(cg.get("categories") or []),
          "| 走势", list((cg.get("charts") or {}).keys()))
    print("    [2b] CoinMarketCap 全市场指标 ...", flush=True)
    cm = cmc_global()
    if cm:
        out["cmc_global"] = cm
        print("    CMC(%s) mcap %.2fT | 24h %s%% | vol %.1fB | BTC.D %.2f%% (24h %+.2f%%)" % (
            cm.get("channel", ""), (cm["mcap"] or 0) / 1e12, cm["mcap_chg24h"],
            (cm["volume"] or 0) / 1e9, cm["btc_dom"] or 0, cm["btc_dom_chg24h"] or 0))
    print("[3/5] 爆仓明细 ...", flush=True)
    if CG_KEY:
        cgl = coinglass_liquidations()
        if cgl:
            out["coinglass_liquidations"] = cgl
            print("    [CoinGlass 全市场 24h]")
            for k, v in cgl.items():
                print("      %s 多爆 $%.1fM / 空爆 $%.1fM" % (
                    k, (v.get("long_24h") or 0) / 1e6, (v.get("short_24h") or 0) / 1e6))
            r = coinglass_ratio()
            if r:
                out["coinglass_ratio"] = r
                print("      合约/现货量比 + 山寨季指数 已取")
        else:
            print("    CoinGlass 调用失败，回落 OKX", flush=True)
    else:
        print("    (无 CoinGlass API Key，使用 OKX 公共接口)", flush=True)
    out["liquidations"] = okx_liquidations()
    for k, v in (out["liquidations"] or {}).items():
        print("    OKX %s n=%d 窗口%.1fh 多爆$%.0f 空爆$%.0f" % (
            k, v["n"], v["window_h"], v["long_usd"], v["short_usd"]))
    print("[4/5] Binance 合约情绪 ...", flush=True)
    out["futures"] = binance_futures()
    for k, v in (out["futures"] or {}).items():
        print("    %s 资金费率 %.4f%% | OI $%.2fB (24h %+.2f%%) | 大户多空 %.2f | 散户多空 %.2f | taker %.2f" % (
            k, (v.get("funding") or 0) * 100, (v.get("oi_usd") or 0) / 1e9,
            v.get("oi_chg24h") or 0, v.get("top_ls") or 0,
            v.get("retail_ls") or 0, v.get("taker_ratio") or 0))
    print("[5/5] 写盘 ...", flush=True)
    # 关键块缺失时复用上一份数据（CoinGecko 429 / OKX 偶发 SSL 不该让整节消失）
    for k in ("coins", "categories", "charts", "top20_chg24h", "global"):
        if not out.get(k) and prev.get(k):
            out[k] = prev[k]
            out.setdefault("stale", []).append(k)
            print("    [复用上次] %s" % k, flush=True)
    if prev.get("liquidations"):
        cur = out.setdefault("liquidations", {})
        for ccy, v in prev["liquidations"].items():
            if ccy not in cur:
                cur[ccy] = v
                out.setdefault("stale", []).append("liquidations." + ccy)
                print("    [复用上次] liquidations.%s" % ccy, flush=True)
    for k in ("coinglass_liquidations", "coinglass_ratio"):
        if not out.get(k) and prev.get(k):
            out[k] = prev[k]
            out.setdefault("stale", []).append(k)
            print("    [复用上次] %s" % k, flush=True)
    os.makedirs(OUT, exist_ok=True)
    with open(p_old, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote", p_old, len(json.dumps(out)), "bytes")


if __name__ == "__main__":
    main()
