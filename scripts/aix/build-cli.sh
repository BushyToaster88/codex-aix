#!/bin/sh
# Build the Codex CLI with the pinned AIX Toolbox toolchain and dependency fixes.
set -eu

if [ "$(id -u)" -eq 0 ]; then
    echo 'Run this build as an unprivileged user, not root.' >&2
    exit 1
fi

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
repo_dir=$(CDPATH= cd "$script_dir/../.." && pwd -P)

PATH=/opt/freeware/bin:/usr/bin:/etc:/usr/sbin:/usr/ucb:/sbin
LC_ALL=EN_US.UTF-8
CARGO_HOME=${CARGO_HOME:-/codex-build/cargo-home}
CARGO_TARGET_DIR=${CARGO_TARGET_DIR:-/codex-build/target}
CARGO_BUILD_JOBS=${CARGO_BUILD_JOBS:-2}
CARGO_INCREMENTAL=${CARGO_INCREMENTAL:-0}
CC=${CC:-/opt/freeware/bin/gcc-13}
CXX=${CXX:-/opt/freeware/bin/g++-13}
RUST_MIN_STACK=${RUST_MIN_STACK:-8388608}
export PATH LC_ALL CARGO_HOME CARGO_TARGET_DIR CARGO_BUILD_JOBS CARGO_INCREMENTAL CC CXX RUST_MIN_STACK

cd "$repo_dir/codex-rs"
if [ "${CODEX_AIX_SKIP_FETCH:-0}" != 1 ]; then
    cargo fetch --locked --target powerpc64-ibm-aix
fi
sh "$script_dir/prepare-dependencies.sh"
cargo build --locked -p codex-cli --bin codex
"$CARGO_TARGET_DIR/debug/codex" --version
