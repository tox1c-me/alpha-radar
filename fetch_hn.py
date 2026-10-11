"""HN 24h 内 >80 分热帖，带时间戳与讨论量，用于日报 L4 / L1 选题。"""
import json
import socket
import time
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/153.0.0.0 Safari/537.36"


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
    OP = urllib.request.build_opener(urllib.request.ProxyHandler(
        {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}))
else:
    OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
OP.addheaders = [("User-Agent", UA)]


def get(u):
    return json.loads(OP.open(u, timeout=30).read())


ids = get("https://hacker-news.firebaseio.com/v0/topstories.json")[:140]
now = time.time()
out = []
for i in ids:
    try:
        it = get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json")
    except Exception:
        continue
    if not it or it.get("score", 0) < 80:
        continue
    age = (now - it.get("time", 0)) / 3600.0
    if age > 26:
        continue
    out.append({
        "id": i, "score": it.get("score"), "age_h": round(age, 1),
        "comments": it.get("descendants", 0),
        "title": it.get("title"), "url": it.get("url"),
        "hn": f"https://news.ycombinator.com/item?id={i}",
        "bj": time.strftime("%m-%d %H:%M", time.localtime(it.get("time", 0))),
    })
out.sort(key=lambda x: -x["score"])
from config import RAW_DIR
json.dump(out, open(RAW_DIR / "hn_detail.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("items", len(out))
for o in out:
    print(f'{o["score"]:4d} | {o["bj"]} | {o["age_h"]:>4}h | c{o["comments"]:>3} | {o["title"][:95]}')
