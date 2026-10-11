"""X 数据源不可用时的补充外部源：行情 / 交易所公告 / 加密风险事件 / 加密新闻。

背景：本机 chrome-devtools MCP 未注册、用户 Chrome 未开调试端口，
且 Chrome 的 App-Bound Encryption(v20) 导致克隆 profile 无法解密 auth_token，
因此今天拿不到 X 时间线。为保证日报 L3（链上机会/风险）仍有可验证内容，补这几个源。
"""
import json
import os
import socket
import urllib.request
import xml.etree.ElementTree as ET

from config import PROXY, RAW_DIR

OUT = str(RAW_DIR)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36")


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


def get(url, timeout=30):
    return OPENER.open(url, timeout=timeout).read()


def dump(name, obj):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    print("wrote", p, flush=True)


def rss_items(url, limit=25):
    raw = get(url).decode("utf-8", "replace")
    root = ET.fromstring(raw)
    items = []
    for it in root.iter():
        if it.tag.split("}")[-1] not in ("item", "entry"):
            continue
        d = {}
        for ch in it:
            tag = ch.tag.split("}")[-1]
            if tag in ("title", "link", "pubDate", "published", "updated", "description", "summary"):
                if tag == "link" and not (ch.text or "").strip():
                    d["link"] = ch.attrib.get("href", "")
                else:
                    d[tag] = (ch.text or "").strip()
        if d.get("title"):
            items.append(d)
        if len(items) >= limit:
            break
    return items


def main():
    # 1) 行情
    try:
        g = json.loads(get("https://api.coingecko.com/api/v3/global"))
        dump("cg_global.json", g)
    except Exception as e:
        print("cg_global ERR", e)
    try:
        m = json.loads(get("https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd"
                           "&order=market_cap_desc&per_page=30&price_change_percentage=24h"))
        dump("cg_markets.json", [{
            "sym": c["symbol"].upper(), "name": c["name"], "price": c["current_price"],
            "chg24h": c.get("price_change_percentage_24h_in_currency"),
            "mcap": c["market_cap"], "vol": c["total_volume"],
        } for c in m])
    except Exception as e:
        print("cg_markets ERR", e)

    # 2) 币安公告（上币 / 打新 / 活动）
    for name, u in [
        ("bn_ann_type1.json", "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=25"),
        ("bn_ann_type48.json", "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=48&pageNo=1&pageSize=25"),
    ]:
        try:
            dump(name, json.loads(get(u)))
        except Exception as e:
            print(name, "ERR", e)

    # 3) 加密风险事件 / 新闻
    for name, u in [
        ("rekt.json", "https://rekt.news/rss/"),
        ("decrypt.json", "https://decrypt.co/feed"),
        ("cointelegraph.json", "https://cointelegraph.com/rss"),
    ]:
        try:
            dump(name, rss_items(u, 25))
        except Exception as e:
            print(name, "ERR", e)


if __name__ == "__main__":
    main()
