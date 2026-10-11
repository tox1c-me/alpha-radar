# -*- coding: utf-8 -*-
"""生成市场节点日历（.ics），可导入 Outlook / Google Calendar / 手机。

数据源与会议日志、弹窗提醒完全一致（唯一真相）：
  events.json         —— 有精确时间的节点 → 生成**定时事件**（提前 1 天 + 2 小时提醒）
  calendar-extra.json —— 仅有日期的节点   → 生成**全天事件**（提前 1 天提醒）

北京 = UTC+8，脚本自动换算。
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import ROOT as BASE
OUT = BASE / "market-calendar-2026H2.ics"

CALNAME = "市场关键节点 2026 H2"
PRODID = "-//DailyIntel//Market Calendar 2026H2//CN"


def esc(s: str) -> str:
    return (s.replace("\\", "\\\\").replace(",", "\\,")
             .replace(";", "\\;").replace("\n", "\\n"))


def clean_body(body: str) -> str:
    """去掉开头的「北京时间 …」段，把剩余段落合成一句（中文标点后不补空格）。"""
    parts = [p.strip() for p in body.split("\n\n") if p.strip()]
    if parts and parts[0].startswith("北京时间"):
        parts = parts[1:]
    parts = [" ".join(p.split()) for p in parts]
    out = ""
    for p in parts:
        if out and out[-1] not in "。！？；：，、":
            out += " "
        out += p
    return out


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    out = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:" + PRODID,
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:" + CALNAME,
        "X-WR-TIMEZONE:Asia/Shanghai",
    ]

    n_timed = n_allday = 0

    # ---- 1. 有精确时间的节点：定时事件 ----
    events = json.loads((BASE / "events.json").read_text(encoding="utf-8"))
    for i, e in enumerate(events, 1):
        bj = datetime.strptime(e["time"], "%Y-%m-%d %H:%M")   # 北京时间
        utc = bj - timedelta(hours=8)
        out += [
            "BEGIN:VEVENT",
            "UID:marketnode-%02d-%s@dailyintel" % (i, utc.strftime("%Y%m%dT%H%M%SZ")),
            "DTSTAMP:" + stamp,
            "DTSTART:" + utc.strftime("%Y%m%dT%H%M%SZ"),
            "DURATION:PT1H",
            "SUMMARY:" + esc(e["title"]),
            "DESCRIPTION:" + esc(clean_body(e["body"])),
            "CATEGORIES:" + esc("市场节点," + e["level"]),
            "BEGIN:VALARM\nTRIGGER:-P1D\nACTION:DISPLAY\nDESCRIPTION:%s\nEND:VALARM"
            % esc("明天：" + e["title"]),
            "BEGIN:VALARM\nTRIGGER:-PT2H\nACTION:DISPLAY\nDESCRIPTION:%s\nEND:VALARM"
            % esc("2 小时后：" + e["title"]),
            "END:VEVENT",
        ]
        n_timed += 1

    # ---- 2. 仅有日期的节点：全天事件 ----
    extra = json.loads((BASE / "calendar-extra.json").read_text(encoding="utf-8"))
    for j, x in enumerate(extra, 1):
        d = datetime.strptime(x["date"], "%Y-%m-%d")
        d_end = d + timedelta(days=1)          # ICS 全天事件结束日不含当天
        desc = x.get("note", "") or ""
        out += [
            "BEGIN:VEVENT",
            "UID:marketevent-%02d-%s@dailyintel" % (j, d.strftime("%Y%m%d")),
            "DTSTAMP:" + stamp,
            "DTSTART;VALUE=DATE:" + d.strftime("%Y%m%d"),
            "DTEND;VALUE=DATE:" + d_end.strftime("%Y%m%d"),
            "SUMMARY:" + esc(x["title"]),
            "DESCRIPTION:" + esc(desc),
            "CATEGORIES:" + esc("市场节点," + x["level"]),
            "TRANSP:TRANSPARENT",
            "BEGIN:VALARM\nTRIGGER:-P1D\nACTION:DISPLAY\nDESCRIPTION:%s\nEND:VALARM"
            % esc("明天：" + x["title"]),
            "END:VEVENT",
        ]
        n_allday += 1

    out.append("END:VCALENDAR")

    OUT.write_text("\r\n".join(out) + "\r\n", encoding="utf-8", newline="")

    print("timed events  :", n_timed)
    print("all-day events:", n_allday)
    print("written:", OUT)


if __name__ == "__main__":
    main()
