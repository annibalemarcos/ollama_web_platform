from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict

try:
    import psutil  # type: ignore
except Exception:  # noqa: BLE001
    psutil = None  # type: ignore

_LAST_NET: tuple[float, int, int] | None = None


def _bytes_to_gb(value: float) -> float:
    return round(float(value) / (1024 ** 3), 2)


def _bytes_to_mb(value: float) -> float:
    return round(float(value) / (1024 ** 2), 1)


def _human_rate(value: float) -> str:
    value = max(0.0, float(value or 0))
    if value >= 1024 ** 2:
        return f"{value / (1024 ** 2):.1f} MB/s"
    if value >= 1024:
        return f"{value / 1024:.0f} KB/s"
    return f"{value:.0f} B/s"


def _process_bucket() -> Dict[str, Dict[str, Any]]:
    buckets = {
        "ollama": {"count": 0, "memory_mb": 0.0, "cpu_percent": 0.0},
        "python": {"count": 0, "memory_mb": 0.0, "cpu_percent": 0.0},
    }
    if psutil is None:
        return buckets

    for proc in psutil.process_iter(["name", "memory_info"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if not name:
                continue
            target = None
            if "ollama" in name:
                target = "ollama"
            elif name.startswith("python") or "python.exe" in name:
                target = "python"
            if not target:
                continue
            buckets[target]["count"] += 1
            mem = proc.info.get("memory_info")
            if mem:
                buckets[target]["memory_mb"] += _bytes_to_mb(mem.rss)
            try:
                buckets[target]["cpu_percent"] += proc.cpu_percent(interval=None)
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001
            continue

    for item in buckets.values():
        item["memory_mb"] = round(item["memory_mb"], 1)
        item["cpu_percent"] = round(item["cpu_percent"], 1)
    return buckets


def collect_pc_stats() -> Dict[str, Any]:
    global _LAST_NET

    if psutil is None:
        return {"ok": False, "available": False, "message": "psutil não está instalado."}

    now = time.time()
    cpu_percent = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()

    try:
        disk_root = Path.cwd().anchor or os.path.abspath(os.sep)
        disk = psutil.disk_usage(disk_root)
    except Exception:  # noqa: BLE001
        disk = psutil.disk_usage(os.path.abspath(os.sep))

    net = psutil.net_io_counters()
    down_rate = 0.0
    up_rate = 0.0
    if net is not None:
        if _LAST_NET:
            last_time, last_recv, last_sent = _LAST_NET
            elapsed = max(0.001, now - last_time)
            down_rate = max(0.0, (net.bytes_recv - last_recv) / elapsed)
            up_rate = max(0.0, (net.bytes_sent - last_sent) / elapsed)
        _LAST_NET = (now, net.bytes_recv, net.bytes_sent)

    processes = _process_bucket()

    return {
        "ok": True,
        "available": True,
        "timestamp": now,
        "cpu": {"percent": round(float(cpu_percent), 1), "count": psutil.cpu_count(logical=True) or 0},
        "memory": {
            "percent": round(float(memory.percent), 1),
            "used_gb": _bytes_to_gb(memory.used),
            "available_gb": _bytes_to_gb(memory.available),
            "total_gb": _bytes_to_gb(memory.total),
        },
        "disk": {"percent": round(float(disk.percent), 1), "used_gb": _bytes_to_gb(disk.used), "total_gb": _bytes_to_gb(disk.total)},
        "network": {
            "download_bps": round(down_rate, 1),
            "upload_bps": round(up_rate, 1),
            "download_label": _human_rate(down_rate),
            "upload_label": _human_rate(up_rate),
        },
        "processes": processes,
    }
