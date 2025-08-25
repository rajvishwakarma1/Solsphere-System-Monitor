import os
import sys
import time
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
SCRIPTS = ROOT / "scripts"

PY = sys.executable or "python"
IS_WINDOWS = platform.system() == "Windows"

PROCS = []

def start(cmd, cwd):
    print(f"\n>>> Starting: {cmd} (cwd={cwd})")
    # Use shell=True only for npm on Windows for PATH resolution
    use_shell = IS_WINDOWS and (cmd[0] in {"npm", "npm.cmd"})
    p = subprocess.Popen(cmd, cwd=str(cwd), shell=use_shell)
    PROCS.append(p)
    return p

try:
    # 1) Backend API
    backend_cmd = [PY, "-u", "app.py"]
    start(backend_cmd, BACKEND)
    time.sleep(2)

    # 2) Frontend (Vite)
    # On Windows npm is npm.cmd
    npm_exe = "npm.cmd" if IS_WINDOWS else "npm"
    frontend_cmd = [npm_exe, "run", "dev"]
    start(frontend_cmd, FRONTEND)
    time.sleep(3)

    # 3) Seeder live mode
    seeder_cmd = [PY, "-u", str(SCRIPTS / "seed_demo.py"), "--loop", "--interval", "10"]
    # Allow overriding API URL and KEY via environment
    env = os.environ.copy()
    env.setdefault("DEMO_API_URL", "http://localhost:5000/report")
    env.setdefault("DEMO_API_KEY", "StrongInterviewKey")

    print("\n>>> Starting live demo seeder (updates every 10s)...")
    p = subprocess.Popen(seeder_cmd, cwd=str(SCRIPTS), env=env)
    PROCS.append(p)

    print("\nAll services started:\n- Backend: http://localhost:5000\n- Frontend (Vite Dev): check terminal output for URL (e.g., http://localhost:5173)\n- Seeder: posting updates every 10s\n\nPress Ctrl+C to stop all.")

    # Keep the orchestrator alive until interrupted
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopping processes...")
finally:
    for p in PROCS:
        try:
            p.terminate()
        except Exception:
            pass
    # Give them a moment to exit
    time.sleep(1)
    for p in PROCS:
        try:
            if p.poll() is None:
                p.kill()
        except Exception:
            pass
    print("All stopped.")
