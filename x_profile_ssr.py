"""x.com 账号页 SSR 抓取器 —— 免登录拿「实时」最新推文。

原理
----
x.com 对未登录用户仍返回账号页的 SSR HTML，其中内嵌 **React Server Components
数据流**（Next.js App Router，`$R[n]` 引用格式），包含：

    profile_user_originals_timeline
      └ TimelineAddEntries → entries[] → content.tweet_results.result
          ├ details.created_at_ms   ← 毫秒时间戳（实时，非缓存）
          ├ details.full_text       ← 推文正文
          ├ counts.favorite_count / reply_count / retweet_count
          └ views.count             ← 阅读数

与 `syndication.twitter.com` 的关键区别
--------------------------------------
syndication 返回的是**陈旧 embed 缓存**（实测 BTCdayu 滞后 4 天、aa_AFeng 滞后 4 年），
不可用于日常抓取。账号页 SSR 是**实时**的，代价是未登录只渲染前几条（实测 2–5 条）。

对日报足够：15 个白名单账号 × 2–5 条 = 覆盖最近 1–2 天的最新动态。

用法
----
    python x_profile_ssr.py                     # 全部白名单
    python x_profile_ssr.py --only BTCdayu,SuperL9
    python x_profile_ssr.py --per-node 2 --hours 72
    python x_profile_ssr.py --keep-node         # 结束后不恢复原节点
"""
import argparse
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from x_synd_fetch import (HANDLES, NODES, OPENER, UA, egress_ip, group_now,
                          switch_node)
from config import CLASH_GROUP as GROUP

BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw")

HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

ENTRY_RE = re.compile(r'entry_id:"tweet-(\d+)"')
# 关键：必须用 `rest_id:"<id>",result:$R[n]={` 作为切分锚点。
# 旧版按 entry_id:"tweet-<id>" 切分是**错的**——entry_id 出现在该推文数据的**之后**，
# 所以 parts[i+1] 实际是**下一条**推文的内容，导致 id/时间/正文整体串位
# （实测 @aa_AFeng 的推文被解析成下一条的 ID，链接指向错误推文）。
TWEET_ANCHOR_RE = re.compile(r'rest_id:"(\d+)",result:\$R\[\d+\]=\{' + r'(?!\})')
MS_RE = re.compile(r"created_at_ms:(\d+)")
FT_RE = re.compile(r'full_text:"((?:[^"\\]|\\.)*)"')
SN_RE = re.compile(r'screen_name:"([^"]+)"')
FAV_RE = re.compile(r"favorite_count:(\d+)")
REP_RE = re.compile(r"reply_count:(\d+)")
RT_RE = re.compile(r"retweet_count:(\d+)")
# 2026-10-11 修复：views 字段改为 `views:$R[n]={count:"<n>"}`（此前是 `views:{count:"<n>"}`）。
# 两种形式都兼容，否则 views 全为 None。
VIEW_RE = re.compile(r'views:(?:\$R\[\d+\]=\{)count:"(\d+)"')
NAME_RE = re.compile(r'name:"([^"]*)",screen_name:"([^"]+)"')
PIN_RE = re.compile(r'context_type:"Pin"')


def _unescape(s):
    return (
        s.replace("\\n", "\n").replace('\\"', '"').replace("\\/", "/")
        .replace("\\u003c", "<").replace("\\u003e", ">").replace("\\u0026", "&")
    )


def parse_profile(html):
    """从账号页 SSR HTML 提取推文列表。

    按 `rest_id:"<id>",result:$R[n]={` 切段（TimelineTweet 的独有锚点），
    段内正则取 counts / details 字段。段天然终止于下一条 TimelineTweet。
    """
    parts = TWEET_ANCHOR_RE.split(html)
    out = {}
    for i in range(1, len(parts), 2):
        tid = parts[i]
        seg = parts[i + 1][:16000]
        if tid in out:
            continue
        if "counts:" not in seg or "details:" not in seg:
            continue
        ms = MS_RE.search(seg)
        ft = FT_RE.search(seg)
        if not (ms and ft):
            continue
        sn = SN_RE.search(seg)
        nm = NAME_RE.search(seg)
        out[tid] = {
            "id": tid,
            "handle": (nm.group(2) if nm else (sn.group(1) if sn else None)),
            "name": nm.group(1) if nm else None,
            "created_at_ms": int(ms.group(1)),
            "dt": datetime.fromtimestamp(
                int(ms.group(1)) / 1000, tz=timezone.utc
            ).isoformat(),
            "text": _unescape(ft.group(1)),
            "likes": int(FAV_RE.search(seg).group(1)) if FAV_RE.search(seg) else None,
            "replies": int(REP_RE.search(seg).group(1)) if REP_RE.search(seg) else None,
            "rts": int(RT_RE.search(seg).group(1)) if RT_RE.search(seg) else None,
            "views": int(VIEW_RE.search(seg).group(1)) if VIEW_RE.search(seg) else None,
            "url": f"https://x.com/{nm.group(2) if nm else sn.group(1) if sn else 'i'}/status/{tid}",
            "pinned": False,
        }
    return list(out.values())


# 直连 opener —— Clash 未运行时用（实测某些网络环境下 x.com 可直连）
DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def fetch_profile(handle, timeout=30, opener=None):
    url = f"https://x.com/{handle}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with (opener or OPENER).open(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, f"__ERR__ {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=72)
    ap.add_argument("--per-node", type=int, default=2)
    ap.add_argument("--only", default="")
    ap.add_argument("--keep-node", action="store_true")
    ap.add_argument("--direct", action="store_true",
                    help="不走 Clash，直连 x.com（Clash Verge 未运行时用）")
    args = ap.parse_args()

    handles = [h.strip() for h in args.only.split(",") if h.strip()] or HANDLES
    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.hours)

    opener = DIRECT_OPENER if args.direct else OPENER
    if args.direct:
        orig = None
        print(f"[init] DIRECT 模式：直连 x.com，不切 Clash 节点 | 抓 {len(handles)} 个账号 | 窗口 {args.hours}h")
    else:
        orig = group_now()
        print(f"[init] 组「{GROUP}」当前 = {orig} | 抓 {len(handles)} 个账号 | 窗口 {args.hours}h")

    rows, report, node_i, switched = [], [], 0, 0

    for idx, h in enumerate(handles):
        if not args.direct and idx % args.per_node == 0:
            node = NODES[node_i % len(NODES)]
            node_i += 1
            switch_node(node)
            switched += 1
            print(f"\n[node] -> {node}  (egress {egress_ip()})")

        st, body = fetch_profile(h, opener=opener)
        if st != 200 and not args.direct:
            node = NODES[node_i % len(NODES)]
            node_i += 1
            switch_node(node)
            st, body = fetch_profile(h, opener=opener)
            print(f"  {h:16s} retry@{node} -> {st}")

        if st != 200:
            print(f"  {h:16s} FAIL {st} {str(body)[:70]}")
            report.append({"handle": h, "status": st, "n": 0})
            continue

        tw = parse_profile(body)
        if not tw:
            print(f"  {h:16s} 200 但解析 0 条 (len={len(body)})")
            report.append({"handle": h, "status": "parse0", "n": 0})
            continue

        with open(os.path.join(RAW, f"x_profile_{h}.json"), "w", encoding="utf-8") as f:
            json.dump(tw, f, ensure_ascii=False, indent=1)

        fresh = [
            t for t in tw
            if datetime.fromtimestamp(t["created_at_ms"] / 1000, tz=timezone.utc) >= cutoff
        ]
        rows.extend(fresh)
        latest = max(tw, key=lambda t: t["created_at_ms"])
        ldt = datetime.fromtimestamp(latest["created_at_ms"] / 1000, tz=timezone.utc) + timedelta(hours=8)
        print(f"  {h:16s} 200 | 抓到 {len(tw):2d} 条 | 窗口内 {len(fresh):2d} | 最新 {ldt:%m-%d %H:%M} BJ")
        report.append({"handle": h, "status": 200, "n": len(tw), "fresh": len(fresh)})
        time.sleep(1.2)

    if not args.direct and not args.keep_node and orig:
        switch_node(orig)
        print(f"\n[node] 恢复 -> {orig}")

    # 汇总：从全部 x_profile_<handle>.json 重建（支持分批补抓），去重 + 窗口过滤
    merged = {}
    for p in glob.glob(os.path.join(RAW, "x_profile_*.json")):
        if os.path.basename(p) == "x_profile_latest.json":
            continue
        try:
            for t in json.load(open(p, encoding="utf-8")):
                merged[t["id"]] = t
        except Exception:
            pass
    allrows = [
        t for t in merged.values()
        if datetime.fromtimestamp(t["created_at_ms"] / 1000, tz=timezone.utc) >= cutoff
    ]
    allrows.sort(key=lambda t: t["created_at_ms"], reverse=True)
    out = os.path.join(RAW, "x_profile_latest.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(allrows, f, ensure_ascii=False, indent=1)

    print(f"\n{'=' * 62}")
    print(f"汇总 {len(allrows)} 条（窗口 {args.hours}h，共 {len(merged)} 条原始）-> {out}")
    print(f"成功 {sum(1 for r in report if r['status'] == 200)}/{len(handles)} | 换节点 {switched} 次")
    for r in report:
        if r["status"] != 200:
            print(f"  失败：{r['handle']} ({r['status']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
