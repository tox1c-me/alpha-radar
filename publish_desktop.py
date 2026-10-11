# -*- coding: utf-8 -*-
"""把链上情报日报同步到桌面，文件名带日期：YYYY-MM-DD-情报收集.html

用法：
    python publish_desktop.py                    # 自动取 DailyIntel\\reports 下最新一期
    python publish_desktop.py <某个html路径>      # 指定某一期

文件名里的日期取自源文件名（daily-intel-YYYY-MM-DD.html）；取不到则用当天日期。
"""

import glob
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

from config import DELIVER_DIR as DELIVER, KEEP_DAYS, REPORTS_DIR, ROOT as BASE


def newest(patterns):
    best, best_mt = None, -1.0
    for pat in patterns:
        for p in glob.glob(pat):
            mt = os.path.getmtime(p)
            if mt > best_mt:
                best, best_mt = p, mt
    return best


def report_date(path: Path) -> str:
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", path.stem)
    if m:
        return "%s-%s-%s" % m.groups()
    return date.today().isoformat()


def main():
    if len(sys.argv) > 1:
        src = Path(sys.argv[1])
        if not src.exists():
            print("SOURCE_NOT_FOUND:", src)
            return 1
    else:
        found = newest([
            str(REPORTS_DIR / "daily-intel-*.html"),
            str(BASE / "daily-intel-*.html"),
        ])
        if not found:
            print("NO_REPORT_FOUND")
            return 1
        src = Path(found)

    d = report_date(src)
    DELIVER.mkdir(parents=True, exist_ok=True)
    target = DELIVER / ("%s-情报收集.html" % d)
    shutil.copyfile(src, target)
    print("source:", src)
    print("target:", target)
    print("date:", d)
    print("size:", target.stat().st_size)

    render_png(target, width=1000)
    tidy_desktop_now()
    return 0


def render_png(html, width):
    """顺带出整页 PNG（方便发微信/贴文档）。失败不影响交付主流程。"""
    try:
        import html2png
        html2png.render(html, Path(html).with_suffix(".png"),
                        width=width, scale=2, pad=24)
    except Exception as e:
        print("PNG_SKIPPED:", type(e).__name__, e)


def tidy_desktop_now():
    """桌面整理：把过期日报移进归档（移动，不删除）。失败不影响主流程。"""
    try:
        import tidy_desktop
        tidy_desktop.tidy()
    except Exception as e:
        print("TIDY_SKIPPED:", type(e).__name__, e)


if __name__ == "__main__":
    sys.exit(main())
