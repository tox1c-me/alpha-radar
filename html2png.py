# -*- coding: utf-8 -*-
"""把本地 HTML 渲染成整页 PNG（Chrome 无头，两趟：先量高，再截图）。

为什么两趟
----------
Chrome 无头 CLI 的 `--screenshot` 只截 `--window-size` 指定的视口，**没有整页参数**。
所以先注入一段脚本把 `document.documentElement.scrollHeight` 写进 title，
用 `--dump-dom` 读回来，再用这个高度去截图。

用法
----
    python html2png.py <input.html> [output.png]
    python html2png.py <input.html> --width 760 --scale 2

参数
----
    --width   视口宽度，默认 760（速览体/公众号版式的窄栏）
    --scale   设备像素比，默认 2（导出 2 倍图，文字锐利）
    --pad     底部额外留白像素，默认 0
"""

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from config import CHROME, CHROME_PROFILE as PROFILE

PROBE = ("<script>window.addEventListener('load',function(){"
         "document.title='__H__='+document.documentElement.scrollHeight;});</script>")


def run(args):
    return subprocess.run(args, capture_output=True, text=True,
                          errors="replace", timeout=120)


def base_args():
    return [CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
            "--no-default-browser-check", f"--user-data-dir={PROFILE}"]


def measure(html: Path, width: int) -> int:
    """量出整页高度。"""
    src = html.read_text(encoding="utf-8")
    if "</body>" not in src:
        src += PROBE
    else:
        src = src.replace("</body>", PROBE + "</body>", 1)

    tmp = Path(tempfile.mkdtemp(prefix="html2png_")) / "measure.html"
    tmp.write_text(src, encoding="utf-8", newline="")

    r = run(base_args() + [f"--window-size={width},900",
                           "--virtual-time-budget=3000",
                           "--dump-dom", tmp.as_uri()])
    m = re.search(r"__H__=(\d+)", r.stdout)
    if not m:
        raise RuntimeError("量高失败：DOM 里没找到 __H__ 标记")
    return int(m.group(1))


def shoot(html: Path, out: Path, width: int, height: int, scale: float) -> None:
    r = run(base_args() + ["--hide-scrollbars",
                           f"--force-device-scale-factor={scale}",
                           f"--window-size={width},{height}",
                           "--virtual-time-budget=3000",
                           f"--screenshot={out}", html.as_uri()])
    if not out.exists():
        raise RuntimeError("截图失败：%s\n%s" % (r.returncode, r.stderr[-500:]))


def pick_scale(css_height: int, want: float = 2.0, max_h: int = 8000) -> float:
    """挑一个合适的像素比，别让长文档导出成 13000px 的巨图。

    长报告（链上日报那种 6800px 内容）按 2 倍出图会得到 13650px、2MB+ 的 PNG ——
    微信和多数看图软件都吃不消。所以按输出总高反推：优先 2x，超限就退 1.5x / 1x。
    """
    for s in (2.0, 1.5, 1.0):
        if s <= want and css_height * s <= max_h:
            return s
    return 1.0


def render(html, out, width=760, scale=2, pad=0, max_h=8000, quiet=False):
    """把 HTML 渲染成整页 PNG。可被其他脚本 import 调用。

    html / out 支持 str 或 Path。返回输出 Path。
    """
    html, out = Path(html), Path(out)
    if not html.exists():
        raise FileNotFoundError("HTML 不存在：%s" % html)

    h = measure(html, width)
    s = pick_scale(h + pad, scale, max_h)
    shoot(html, out, width, h + pad, s)

    if not quiet:
        note = "" if s == scale else "  (降采样：内容 %dpx 太高)" % h
        print("  png: %s  (%dx%d px, scale %gx, %.1f KB)%s"
              % (out.name, int(width * s), int((h + pad) * s), s,
                 out.stat().st_size / 1024, note))
    return out


def main():
    ap = argparse.ArgumentParser(description="本地 HTML → 整页 PNG")
    ap.add_argument("html")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--width", type=int, default=760)
    ap.add_argument("--scale", type=float, default=2)
    ap.add_argument("--pad", type=int, default=0)
    ap.add_argument("--max-h", type=int, default=8000,
                    help="输出总高上限，超过则自动降采样（默认 8000px）")
    a = ap.parse_args()

    src = Path(a.html)
    if not src.exists():
        print("NOT_FOUND:", src)
        return 1
    out = Path(a.out) if a.out else src.with_suffix(".png")

    print("source:", src)
    render(src, out, width=a.width, scale=a.scale, pad=a.pad, max_h=a.max_h)
    print("output:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
