# -*- coding: utf-8 -*-
"""把 events.json 里的市场节点批量注册成 Windows 计划任务，到点弹窗提醒。
高影响事件提前 60 分钟 + 30 分钟各提醒一次；其余提前 60 分钟。"""

import json
import subprocess
from datetime import datetime, timedelta

from config import ROOT

BASE = str(ROOT)
PWSH = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
NOW = datetime.now()

with open(ROOT / "events.json", encoding="utf-8") as f:
    events = json.load(f)

created, skipped, failed = [], [], []

for e in events:
    target = datetime.strptime(e["time"], "%Y-%m-%d %H:%M")
    offsets = [60, 30] if e["level"] == "高" else [60]
    for off in offsets:
        t = target - timedelta(minutes=off)
        if t <= NOW:
            skipped.append((e["id"], off))
            continue
        name = "MarketAlert_%02d_%d" % (e["id"], off)
        arg = (
            "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "
            '"%s\\alert.ps1" -Index %d -Offset %d' % (BASE, e["id"], off)
        )
        cmd = (
            "$a = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '%s'; "
            "$t = New-ScheduledTaskTrigger -Once -At '%s'; "
            "$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries "
            "-DontStopIfGoingOnBatteries -StartWhenAvailable; "
            "Register-ScheduledTask -TaskName '%s' -Action $a -Trigger $t "
            "-Settings $s -Force | Out-Null; Write-Output 'OK'"
            % (arg, t.strftime("%Y-%m-%d %H:%M:%S"), name)
        )
        r = subprocess.run(
            [PWSH, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if "OK" in (r.stdout or ""):
            created.append((name, t))
        else:
            failed.append((name, (r.stderr or "")[:180]))

print("created: %d" % len(created))
for n, t in created:
    print("  %s  ->  %s" % (n, t.strftime("%m-%d %H:%M")))
if skipped:
    print("skipped (time already past): %d" % len(skipped))
for n, err in failed:
    print("FAILED: %s | %s" % (n, err))
