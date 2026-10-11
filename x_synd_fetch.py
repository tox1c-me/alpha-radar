"""X 白名单时间线抓取器 —— 免登录 syndication 通道 + Clash 节点轮换。

背景：syndication.twitter.com 端点本身可免登录拿到 SSR 时间线（数据在 __NEXT_DATA__），
但对单一出口 IP 有小时级配额（实测首次 3 次后锁死）。解法 = 每抓 N 个账号切一次 Clash 节点换 IP。

用法：
    python x_synd_fetch.py                # 抓全部白名单，窗口 48h
    python x_synd_fetch.py --hours 24
    python x_synd_fetch.py --only BTCdayu,SuperL9
    python x_synd_fetch.py --per-node 1   # 每节点抓几个账号（默认 2）

产出：
    raw/x_synd_<handle>.json     单账号原始 entries
    raw/x_timeline_48h.json      汇总（格式兼容旧 whitelist.json：id/handle/dt/text/media）
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw")
from config import CLASH_API as CLASH, CLASH_GROUP as GROUP, \
    CLASH_NODES as NODES, CLASH_SECRET as SECRET, PROXY
# GROUP / NODES / CLASH / SECRET / PROXY 全部来自 config.py。
# 维护方法：订阅换了机场后，组名与节点名都会变。先列出来核对 ——
#   curl -s -H "Authorization: Bearer <secret>" http://127.0.0.1:9097/proxies
# 读 [组名]["all"] 与 config.CLASH_NODES 求差集，**逐节点实测 x.com 可达性**后再更新。

# 白名单 List 成员（x.com/i/lists/2102231737128632629）
HANDLES = [
    "aa_AFeng", "SuperL9", "xtony1314", "ytflzyyds", "wolfyxbt",
    "BTCdayu", "mmk_btc", "Web3shenqing", "0xJustdu", "GoldenCicada",
    "maid_crypto", "Joensmoon", "JieChao13754", "machibigbrother", "chairbtc",
]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36")

HEADERS = {
    "Referer": "https://platform.twitter.com/",
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Sec-Fetch-Storage-Access": "none",
}

OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
)


# ---------------------------------------------------------------- Clash 控制
def _clash(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        CLASH + path, data=data, method=method,
        headers={"Authorization": f"Bearer {SECRET}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read()


def group_now():
    d = json.loads(_clash("GET", "/proxies/" + urllib.parse.quote(GROUP)))
    return d.get("now")


def switch_node(name):
    _clash("PUT", "/proxies/" + urllib.parse.quote(GROUP), {"name": name})
    time.sleep(1.2)


def egress_ip():
    """当前出口 IP（走代理），用于确认换节点真的生效。"""
    try:
        with OPENER.open("https://api.ipify.org", timeout=12) as r:
            return r.read().decode().strip()
    except Exception as e:
        return f"ERR {e}"


# ---------------------------------------------------------------- 抓取与解析
def fetch_timeline(handle, timeout=30):
    url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with OPENER.open(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, f"__ERR__ {e}"


NEXT_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S
)


def parse(html):
    m = NEXT_RE.search(html)
    if not m:
        return []
    try:
        d = json.loads(m.group(1))
    except Exception:
        return []
    entries = (
        d.get("props", {}).get("pageProps", {}).get("timeline", {}).get("entries", [])
    )
    out = []
    for e in entries:
        t = (e.get("content") or {}).get("tweet")
        if not t:
            continue
        u = t.get("user") or {}
        out.append({
            "id": t.get("id_str"),
            "handle": u.get("screen_name"),
            "name": u.get("name"),
            "dt": t.get("created_at"),
            "text": t.get("full_text") or t.get("text") or "",
            "likes": t.get("favorite_count"),
            "replies": t.get("reply_count"),
            "rts": t.get("retweet_count"),
            "url": "https://x.com" + (t.get("permalink") or ""),
            "media": len(((t.get("extended_entities") or {}).get("media") or [])),
        })
    return out


def to_dt(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%a %b %d %H:%M:%S %z %Y")
    except Exception:
        return None


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=48)
    ap.add_argument("--per-node", type=int, default=2, help="每个节点抓几个账号后切换")
    ap.add_argument("--only", default="", help="逗号分隔的 handle，只抓这些")
    ap.add_argument("--keep-node", action="store_true", help="结束后不恢复原节点")
    args = ap.parse_args()

    handles = [h.strip() for h in args.only.split(",") if h.strip()] or HANDLES
    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)

    orig = group_now()
    print(f"[init] 组「{GROUP}」当前节点 = {orig}")
    print(f"[init] 待抓 {len(handles)} 个账号，窗口 {args.hours}h，每 {args.per_node} 个换节点")

    all_rows = []
    report = []
    node_i = 0
    switched = 0

    for idx, h in enumerate(handles):
        if idx % args.per_node == 0:
            node = NODES[node_i % len(NODES)]
            node_i += 1
            switch_node(node)
            switched += 1
            print(f"\n[node] -> {node}  (egress {egress_ip()})")

        st, body = fetch_timeline(h)
        if st != 200:
            # 撞配额：立刻换节点重试一次
            node = NODES[node_i % len(NODES)]
            node_i += 1
            switch_node(node)
            st, body = fetch_timeline(h)
            print(f"  {h:16s} retry@{node} -> {st}")

        if st != 200:
            print(f"  {h:16s} FAIL {st} {str(body)[:80]}")
            report.append({"handle": h, "status": st, "n": 0})
            continue

        rows = parse(body)
        if not rows:
            print(f"  {h:16s} 200 but parsed 0 entries (len={len(body)})")
            report.append({"handle": h, "status": "parse0", "n": 0})
            continue

        with open(os.path.join(RAW, f"x_synd_{h}.json"), "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)

        fresh = [r for r in rows if (to_dt(r["dt"]) or datetime(1970, 1, 1, tzinfo=timezone.utc)) >= cutoff]
        all_rows.extend(fresh)
        newest = max((r["dt"] for r in rows), default="-")
        print(f"  {h:16s} 200 | entries={len(rows):3d} | 窗口内={len(fresh):3d} | 最新={newest}")
        report.append({"handle": h, "status": 200, "n": len(rows), "fresh": len(fresh)})
        time.sleep(1.5)

    if not args.keep_node and orig:
        switch_node(orig)
        print(f"\n[node] 恢复 -> {orig}")

    # 汇总（按时间倒序，格式兼容旧 whitelist.json）
    all_rows.sort(key=lambda r: to_dt(r["dt"]) or datetime(1970, 1, 1, tzinfo=timezone.utc), reverse=True)
    out = os.path.join(RAW, f"x_timeline_{args.hours}h.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_rows, f, ensure_ascii=False, indent=1)

    print(f"\n{'='*60}")
    print(f"汇总：{len(all_rows)} 条（窗口 {args.hours}h）-> {out}")
    ok = sum(1 for r in report if r["status"] == 200)
    print(f"成功账号：{ok}/{len(handles)} | 换节点 {switched} 次")
    for r in report:
        if r["status"] != 200:
            print(f"  失败：{r['handle']} ({r['status']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
