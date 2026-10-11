# -*- coding: utf-8 -*-
"""
桌面整理：把过期的日报从桌面移进归档目录（移动，不删除）。

背景
----
日报按天命名（YYYY-MM-DD-情报收集.html），不覆盖历史 —— 好处是能翻旧期，
代价是桌面一年会堆 700+ 个文件。

策略
----
- 桌面只保留最近 KEEP_DAYS 天（按日期，不是按文件数）的日报
- 更早的**移动**到 archive/YYYY-MM/（按月份子目录）
- 会议日志（按季命名）只保留最新 2 个季度
- **只处理本脚本自己认得出来的文件名**，桌面上其他任何文件一概不碰
- 永不删除。移动是完整可逆的。

用法
----
    python tidy_desktop.py              # 实际执行
    python tidy_desktop.py --dry-run    # 只看会移动什么，不动文件
    python tidy_desktop.py --keep 14    # 改保留天数
"""
import argparse
import re
import shutil
import sys
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent
from config import DESKTOP
DELIVER = DESKTOP / "情报收集"      # 交付目录：成品都收在这里
ARCHIVE = BASE / "archive"

KEEP_DAYS = 7          # 桌面保留最近几天的日报
KEEP_QUARTERS = 2      # 桌面保留最新几个季度的会议日志

RE_DAILY = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-情报收集(-AI)?\.(?:html|png)$")
RE_QUARTER = re.compile(r"^(\d{4})-Q([1-4])-会议日志\.(?:html|png)$")


def scan_daily():
    """返回 [(date, path)]，按日期新→旧。"""
    found = []
    if not DELIVER.is_dir():
        return found
    for p in DELIVER.iterdir():
        if not p.is_file():
            continue
        m = RE_DAILY.match(p.name)
        if not m:
            continue
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        found.append((d, p))
    found.sort(key=lambda t: (t[0], t[1].name), reverse=True)
    return found


def scan_quarter():
    found = []
    if not DELIVER.is_dir():
        return found
    for p in DELIVER.iterdir():
        if not p.is_file():
            continue
        m = RE_QUARTER.match(p.name)
        if not m:
            continue
        found.append(((int(m.group(1)), int(m.group(2))), p))
    found.sort(key=lambda t: t[0], reverse=True)
    return found


def plan(keep_days=KEEP_DAYS, keep_quarters=KEEP_QUARTERS):
    """算出要移动的 (源, 目标) 列表，不碰文件系统。"""
    moves = []

    daily = scan_daily()
    # 按「天」保留，不是按文件数 —— 一天两个文件（链上 + AI）算同一天
    days_seen = []
    for d, p in daily:
        if d not in days_seen:
            days_seen.append(d)
    kept_days = set(days_seen[:keep_days])
    for d, p in daily:
        if d not in kept_days:
            moves.append((p, ARCHIVE / d.strftime("%Y-%m") / p.name))

    # 会议日志：同样按「季度」保留，不是按文件数
    # （一个季度有 .html + .png 两个文件，按文件数切会把当前季度误归档）
    quarters = scan_quarter()
    q_seen = []
    for k, _ in quarters:
        if k not in q_seen:
            q_seen.append(k)
    kept_q = set(q_seen[:keep_quarters])
    for (y, q), p in quarters:
        if (y, q) not in kept_q:
            moves.append((p, ARCHIVE / ("%d-Q%d" % (y, q)) / p.name))

    return moves


def tidy(dry_run=False, keep_days=KEEP_DAYS, keep_quarters=KEEP_QUARTERS):
    moves = plan(keep_days, keep_quarters)
    if not moves:
        print("OK: 桌面无需整理（保留最近 %d 天日报 / %d 个季度会议日志）"
              % (keep_days, keep_quarters))
        return 0

    print("%s %d 个文件："
          % ("[dry-run] 将会移动" if dry_run else "移动", len(moves)))
    for src, dst in moves:
        print("  %s\n    -> %s" % (src, dst))
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
    return 0


def main():
    ap = argparse.ArgumentParser(description="把过期的桌面日报移进归档目录（不删除）")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不移动文件")
    ap.add_argument("--keep", type=int, default=KEEP_DAYS, help="桌面保留最近几天的日报")
    ap.add_argument("--keep-quarters", type=int, default=KEEP_QUARTERS,
                    help="桌面保留最新几个季度的会议日志")
    args = ap.parse_args()
    return tidy(args.dry_run, args.keep, args.keep_quarters)


if __name__ == "__main__":
    sys.exit(main())
