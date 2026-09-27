#!/bin/sh
# Launch the native CLI with AIX Toolbox tools and a UTF-8 terminal locale.
set -eu

if [ "$(id -u)" -eq 0 ]; then
    echo 'Run Codex as an unprivileged user, not root.' >&2
    exit 1
fi

PATH=/opt/freeware/bin:/usr/bin:/etc:/usr/sbin:/usr/ucb:/sbin
LC_ALL=EN_US.UTF-8
export PATH LC_ALL

if [ "$(locale charmap)" != UTF-8 ]; then
    echo 'AIX EN_US.UTF-8 locale is missing; install bos.loc.utf.EN_US.' >&2
    exit 1
fi

codex_bin=${CODEX_AIX_BIN:-/codex-build/target/debug/codex}
exec "$codex_bin" "$@"
