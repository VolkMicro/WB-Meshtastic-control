#!/usr/bin/env python3
"""Setup SSH key on WB controller"""
import subprocess
import sys

HOST = "10.14.0.139"
USER = "root"
PASSWORD = "wirenboard"
PUBKEY = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINJLlUdBzG1F4B7qu0Kjai8hVaWtz2AKruXilgH9s18v wb-meshtastic'

cmd = f"""mkdir -p ~/.ssh && \
echo '{PUBKEY}' >> ~/.ssh/authorized_keys && \
chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys && \
echo '✅ SSH key added' """

# Try using sshpass
try:
    result = subprocess.run(
        ["sshpass", "-p", PASSWORD, "ssh", "-o", "StrictHostKeyChecking=no",
         f"{USER}@{HOST}", cmd],
        capture_output=True, text=True, timeout=30
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)
except FileNotFoundError:
    print("sshpass not found. Trying alternative...")
    # Fallback: use simple ssh with expect or interactive
    subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no", f"{USER}@{HOST}", cmd],
        timeout=30
    )
