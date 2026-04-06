#!/bin/bash
mkdir -p ~/.ssh
cat >> ~/.ssh/authorized_keys << 'EOF'
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINJLlUdBzG1F4B7qu0Kjai8hVaWtz2AKruXilgH9s18v wb-meshtastic
EOF
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
echo "✅ SSH key added. Passwordless login enabled."
