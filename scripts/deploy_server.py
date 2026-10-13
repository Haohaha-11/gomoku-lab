"""Run on hk_88 after copying the release archive to /tmp/gomoku-lab-release.tar.gz."""
from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess
import tarfile


def run(*args):
    subprocess.run(args, check=True, cwd=release)


base = Path("/opt/gomoku-lab")
release = base / "releases" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
release.mkdir(parents=True, exist_ok=False)
with tarfile.open("/tmp/gomoku-lab-release.tar.gz") as archive:
    archive.extractall(release, filter="data")
run("python3", "-m", "unittest", "discover", "-s", "tests", "-v")
current = base / "current"
previous = current.resolve() if current.exists() else None
pending = base / "next"
if pending.is_symlink():
    pending.unlink()
pending.symlink_to(release, target_is_directory=True)
os.replace(pending, current)
unit = """[Unit]
Description=Gomoku classroom experiment
After=network.target

[Service]
Type=simple
DynamicUser=yes
StateDirectory=gomoku-lab
WorkingDirectory=/opt/gomoku-lab/current
Environment=GOMOKU_DATA_DIR=/var/lib/gomoku-lab
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/usr/bin/python3 -m gomoku.server --host 127.0.0.1 --port 8767
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
MemoryMax=512M
CPUQuota=150%
Nice=5

[Install]
WantedBy=multi-user.target
"""
Path("/etc/systemd/system/gomoku-lab.service").write_text(unit)
run("systemctl", "daemon-reload")
run("systemctl", "enable", "--now", "gomoku-lab")
run("systemctl", "restart", "gomoku-lab")
config = Path("/etc/caddy/Caddyfile")
text = config.read_text()
anchor = "haoceanlab.cn {\n\treverse_proxy 127.0.0.1:8600\n}"
replacement = """haoceanlab.cn {
    redir /gomoku /gomoku/ 308
    handle_path /gomoku/* {
        reverse_proxy 127.0.0.1:8767
    }
    handle {
        reverse_proxy 127.0.0.1:8600
    }
}"""
if "handle_path /gomoku/*" not in text:
    if text.count(anchor) != 1:
        raise RuntimeError("Existing Caddy block differs; review before changing")
    backup = config.with_name("Caddyfile.before-gomoku-" + release.name)
    backup.write_text(text)
    candidate = config.with_name("Caddyfile.gomoku-candidate")
    candidate.write_text(text.replace(anchor, replacement))
    run("caddy", "validate", "--config", str(candidate), "--adapter", "caddyfile")
    os.replace(candidate, config)
    try:
        run("systemctl", "reload", "caddy")
    except Exception:
        config.write_text(text)
        run("systemctl", "reload", "caddy")
        raise
print(f"release={release}\nprevious={previous}\nurl=https://haoceanlab.cn/gomoku/")
