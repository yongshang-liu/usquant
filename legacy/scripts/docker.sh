#!/bin/sh
set -eu
if command -v docker >/dev/null 2>&1; then
    exec docker "$@"
fi
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
exec /Applications/Docker.app/Contents/Resources/bin/docker "$@"
