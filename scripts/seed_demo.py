import argparse
import os
import random
import time
import requests
from datetime import datetime, timezone, timedelta

API_URL = os.environ.get("DEMO_API_URL", "http://localhost:5000/report")
API_KEY = os.environ.get("DEMO_API_KEY", "StrongInterviewKey")  # must match backend/app.py

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Helper to ISO timestamp offset by minutes from 'now'
def iso_ts(minutes_ago: int = 0):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def base_machines():
    return [
        {
            "machine_id": "WIN-ENG-01",
            "os": "Windows",
            "disk_encryption": True,
            "os_update": {"current": "10.0.19045", "latest": "Up to date"},
            "antivirus": {"installed": True, "active": True},
            "sleep_settings": {"timeout_minutes": 10},
            "timestamp": iso_ts(2),
        },
        {
            "machine_id": "WIN-FIN-02",
            "os": "Windows",
            "disk_encryption": False,
            "os_update": {"current": "10.0.19045", "latest": "Update Available"},
            "antivirus": {"installed": True, "active": False},
            "sleep_settings": {"timeout_minutes": 30},
            "timestamp": iso_ts(8),
        },
        {
            "machine_id": "MAC-DESIGN-01",
            "os": "Darwin",
            "disk_encryption": True,
            "os_update": {"current": "14.5", "latest": "Update Available"},
            "antivirus": {"installed": False, "active": False},
            "sleep_settings": {"timeout_minutes": 15},
            "timestamp": iso_ts(25),
        },
        {
            "machine_id": "LINUX-BUILD-01",
            "os": "Linux",
            "disk_encryption": False,
            "os_update": {"current": "6.8", "latest": "Up to date"},
            "antivirus": {"installed": True, "active": True},
            "sleep_settings": {"timeout_minutes": 5},
            "timestamp": iso_ts(60),
        },
        {
            "machine_id": "MAC-IT-02",
            "os": "Darwin",
            "disk_encryption": True,
            "os_update": {"current": "14.4", "latest": "Up to date"},
            "antivirus": {"installed": True, "active": True},
            "sleep_settings": {"timeout_minutes": 20},
            "timestamp": iso_ts(5),
        },
    ]


def post_one(m):
    try:
        r = requests.post(API_URL, json=m, headers=HEADERS, timeout=10)
        if r.ok:
            print(f"POST ok: {m['machine_id']}")
            return True
        print(f"POST fail: {m['machine_id']}: {r.status_code} {r.text}")
        return False
    except Exception as e:
        print(f"POST error: {m['machine_id']}: {e}")
        return False


def mutate(m):
    # Randomly tweak a field to simulate change
    choice = random.choice(["os_update", "antivirus", "sleep", "disk"])
    if choice == "os_update":
        latest = m.get("os_update", {}).get("latest", "Up to date")
        m.setdefault("os_update", {})
        m["os_update"]["latest"] = (
            "Update Available" if "up to date" in str(latest).lower() else "Up to date"
        )
    elif choice == "antivirus":
        av = m.setdefault("antivirus", {"installed": True, "active": True})
        # flip active sometimes; occasionally uninstall
        if random.random() < 0.15:
            av["installed"] = not av.get("installed", True)
            if not av["installed"]:
                av["active"] = False
        else:
            av["active"] = not av.get("active", True)
    elif choice == "sleep":
        cur = int(m.get("sleep_settings", {}).get("timeout_minutes", 10) or 10)
        delta = random.choice([-10, -5, 5, 10, 15])
        newv = max(0, min(120, cur + delta))
        m.setdefault("sleep_settings", {})["timeout_minutes"] = newv
    elif choice == "disk":
        if random.random() < 0.2:  # rarely flip disk encryption
            m["disk_encryption"] = not bool(m.get("disk_encryption", True))

    m["timestamp"] = datetime.now(timezone.utc).isoformat()
    return m


def seed_once():
    ok = 0
    for m in base_machines():
        ok += 1 if post_one(m) else 0
    print(f"\nSeed done: {ok}/{len(base_machines())} succeeded")


def seed_loop(interval: int):
    machines = base_machines()
    # Initial seed
    for m in machines:
        post_one(m)
    print("\nEntering live update mode. Press Ctrl+C to stop.\n")
    while True:
        try:
            m = random.choice(machines)
            mutate(m)
            post_one(m)
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\nStopped.")
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo machines and optionally simulate live updates.")
    parser.add_argument("--loop", action="store_true", help="Run continuously and post random updates")
    parser.add_argument("--interval", type=int, default=10, help="Seconds between updates in --loop mode (default 10)")
    args = parser.parse_args()

    if args.loop:
        seed_loop(args.interval)
    else:
        seed_once()
