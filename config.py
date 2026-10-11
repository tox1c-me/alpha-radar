# -*- coding: utf-8 -*-
"""集中配置。所有项都可用环境变量覆盖，默认值适配 Windows。

放一个 config.py 在仓库根目录即可；不想改代码就设环境变量。
"""
import json
import os
from pathlib import Path

# 仓库根目录（= 本文件所在目录）
ROOT = Path(__file__).resolve().parent

# 工作目录
RAW_DIR = Path(os.environ.get("DI_RAW_DIR", ROOT / "raw"))          # 抓取原始产物
REPORTS_DIR = Path(os.environ.get("DI_REPORTS_DIR", ROOT / "reports"))  # 归档报告
LOGS_DIR = Path(os.environ.get("DI_LOGS_DIR", ROOT / "logs"))       # 剔除与执行日志
ARCHIVE_DIR = Path(os.environ.get("DI_ARCHIVE_DIR", ROOT / "archive"))  # 过期归档

# 交付目录：成品只收在这个文件夹里，桌面根目录保持干净
DESKTOP = Path(os.environ.get("DI_DESKTOP", Path.home() / "Desktop"))
DELIVER_DIR = Path(os.environ.get("DI_DELIVER_DIR", DESKTOP / "情报收集"))

# 交付目录里保留最近几天的日报，更早的移到 ARCHIVE_DIR（移动，不删除）
KEEP_DAYS = int(os.environ.get("DI_KEEP_DAYS", "7"))

# ---------------------------------------------------------------- 网络
# HTTP(S) 代理。Clash Verge 默认混合端口 7897；留空 = 直连
PROXY = os.environ.get("DI_PROXY", "http://127.0.0.1:7897")
PROXY_HOST = os.environ.get("DI_PROXY_HOST", "127.0.0.1")
PROXY_PORT = int(os.environ.get("DI_PROXY_PORT", "7897"))

# ---------------------------------------------------------------- Clash 控制 API
# 用于「每抓 N 个账号换一次出口 IP」突破单 IP 配额。
# Clash Verge → 设置 → 外部控制：打开、记下端口与 secret。
CLASH_API = os.environ.get("DI_CLASH_API", "http://127.0.0.1:9097")
CLASH_SECRET = os.environ.get("DI_CLASH_SECRET", "set-your-secret")
# 策略组名（在你的订阅配置里，通常是机场名）
CLASH_GROUP = os.environ.get("DI_CLASH_GROUP", "机场")
# 轮换用的节点白名单。逗号分隔，需与订阅里的节点名完全一致。
CLASH_NODES = [n.strip() for n in os.environ.get(
    "DI_CLASH_NODES",
    "🇭🇰香港 01 | 高级专线,🇯🇵日本 01 | 高级专线,"
    "🇺🇸美国 01 | 专线,🇯🇵日本 05 | 高级专线").split(",") if n.strip()]

# ---------------------------------------------------------------- Chrome（整页截图）
CHROME = os.environ.get(
    "DI_CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
CHROME_PROFILE = os.environ.get(
    "DI_CHROME_PROFILE",
    str(Path(os.environ.get("TEMP", "/tmp")) / "alpha-radar-shot-profile"))

# ---------------------------------------------------------------- 截图参数
PNG_WIDTH = int(os.environ.get("DI_PNG_WIDTH", "1000"))
PNG_SCALE = float(os.environ.get("DI_PNG_SCALE", "2"))


def secrets():
    """读 secrets.json（可选，已在 .gitignore 里）。缺失或为空都不影响运行。"""
    p = ROOT / "secrets.json"
    if not p.exists():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return {k: v.strip() for k, v in d.items()
                if isinstance(v, str) and not k.startswith("_")}
    except Exception:
        return {}


def ensure_dirs():
    for d in (RAW_DIR, REPORTS_DIR, LOGS_DIR, ARCHIVE_DIR, DELIVER_DIR):
        d.mkdir(parents=True, exist_ok=True)
