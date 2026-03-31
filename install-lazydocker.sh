#!/bin/bash
set -e

ARCH=$(uname -m)
case $ARCH in
    x86_64) ARCH="x86_64" ;;
    aarch64|arm64) ARCH="arm64" ;;
esac

LATEST=$(curl -s https://api.github.com/repos/jesseduffield/lazydocker/releases/latest | grep -oP '"tag_name": "\K(.*)(?=")')
curl -sL "https://github.com/jesseduffield/lazydocker/releases/download/${LATEST}/lazydocker_${LATEST#v}_Linux_${ARCH}.tar.gz" | tar xz
mv lazydocker bin/lazydocker
chmod +x bin/lazydocker
