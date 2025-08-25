import platform, time, json, requests, subprocess, re
from datetime import datetime, timezone

# Configuration constants
SERVER_URL = "http://localhost:5000/report"
API_KEY = "StrongInterviewKey"  # Must match backend
MACHINE_ID = platform.node()

# Utility to run a shell command and return its output
def run_cmd(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()
    except Exception as e:
        return str(e)

# Detect whether disk encryption is enabled
def get_disk_encryption():
    sys = platform.system()
    if sys == "Darwin":
        return "On" in run_cmd("fdesetup status")
    elif sys == "Windows":
        return "Percentage Encrypted: 100%" in run_cmd("manage-bde -status C:")
    else:
        return "crypt" in run_cmd("lsblk -o NAME,FSTYPE,MOUNTPOINT").lower()

# Check if OS updates are pending
def get_os_update_status():
    sys = platform.system()
    if sys == "Darwin":
        updates = run_cmd("softwareupdate -l")
        return {
            "current": platform.mac_ver()[0],
            "latest": "Update Available" if "available" in updates.lower() else "Up to date"
        }
    elif sys == "Windows":
        updates = run_cmd('powershell "Get-WindowsUpdate"')
        return {
            "current": platform.version(),
            "latest": "Update Available" if updates else "Up to date"
        }
    else:
        updates = run_cmd("apt list --upgradable 2>/dev/null | grep -v Listing")
        return {
            "current": platform.release(),
            "latest": "Update Available" if updates else "Up to date"
        }

# Check antivirus installation and activation status
def get_antivirus_status():
    sys = platform.system()
    if sys == "Windows":
        output = run_cmd('powershell "Get-MpComputerStatus | Select AMServiceEnabled,AntivirusEnabled"')
        return {
            "installed": "True" in output,
            "active": "True" in output
        }
    elif sys == "Darwin":
        running = bool(run_cmd("pgrep -l av"))
        return {"installed": running, "active": running}
    else:
        running = bool(run_cmd("pgrep -l clamav"))
        return {"installed": running, "active": running}

# Retrieve system sleep timeout in minutes
def get_sleep_settings():
    sys = platform.system()
    minutes = None

    if sys == "Darwin":
        out = run_cmd("pmset -g | grep ' sleep'")
        m = re.search(r"\bsleep\s+(\d+)", out)
        if m:
            minutes = int(m.group(1))

    elif sys == "Windows":
        out = run_cmd('powershell -NoProfile -Command "powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE"')
        m = re.search(r"Current\s+(?:AC|DC)\s+Power\s+Setting\s+Index:\s*0x([0-9a-fA-F]+)", out)
        if m:
            minutes = int(m.group(1), 16)
        else:
            m2 = re.search(r"Index:\s*(\d+)", out)
            if m2:
                val = int(m2.group(1))
                minutes = round(val / 60) if val > 600 else val

    else:
        out = run_cmd("gsettings get org.gnome.settings-daemon.plugins.power sleep-inactive-ac-timeout")
        m = re.search(r"(\d+)", out)
        if m:
            seconds = int(m.group(1))
            minutes = round(seconds / 60)

    # Normalize suspicious or invalid values
    if minutes is None:
        minutes = 0
    if minutes > 600:  # If value seems to be seconds, convert
        minutes = round(minutes / 60)
    if minutes < 0:
        minutes = 0
    if minutes > 10080:  # Limit to one week
        minutes = 10080

    return {"timeout_minutes": minutes}

# Collect all system data into a report
def collect_data():
    return {
        "machine_id": MACHINE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "os": platform.system(),
        "disk_encryption": get_disk_encryption(),
        "os_update": get_os_update_status(),
        "antivirus": get_antivirus_status(),
        "sleep_settings": get_sleep_settings()
    }

# Load last sent report to prevent redundant posts
def load_last():
    try:
        return json.load(open("last_state.json"))
    except FileNotFoundError:
        return None

# Save current report to local cache
def save_last(data):
    json.dump(data, open("last_state.json", "w"))

# Send data to backend server with API key header
def send(data):
    requests.post(SERVER_URL, json=data, headers={"X-API-Key": API_KEY})

# Main loop: collect, compare, send if changed, repeat
if __name__ == "__main__":
    while True:
        data = collect_data()
        if data != load_last():
            send(data)
            save_last(data)
            print(f"Sent at {data['timestamp']}")
        time.sleep(900)  # Run every 15 minutes
