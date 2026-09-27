#!/bin/sh
# Focused AIX-only tests plus credential-free CLI/agent smoke checks.
set -eu

if [ "$(id -u)" -eq 0 ]; then
    echo 'Run native Codex tests as an unprivileged user, not root.' >&2
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
RUST_MIN_STACK=8388608
export PATH LC_ALL CARGO_HOME CARGO_TARGET_DIR CARGO_BUILD_JOBS CARGO_INCREMENTAL CC CXX RUST_MIN_STACK

cd "$repo_dir/codex-rs"
cargo test --locked -p codex-utils-pty --lib aix_tests -- --nocapture
cargo test --locked -p codex-core --lib build_exec_request_fails_closed_without_native_sandbox -- --nocapture
cargo test --locked -p codex-core --lib aix_native_exec_fails_closed_but_executor_managed_exec_is_preserved -- --nocapture
cargo test --locked -p codex-exec-server --lib aix_file_system_helper_rejects_missing_native_sandbox -- --nocapture
python3 "$script_dir/test-peer-uid.py"

# These large test binaries can exceed a stock 512 MB AIX paging space even
# when the production CLI builds. Keep them opt-in until paging is increased.
if [ "${CODEX_AIX_FULL_TESTS:-0}" = 1 ]; then
    cargo test --locked -p codex-tui --lib aix_unix_peer_owner_validation_uses_getpeereid -- --nocapture
    cargo test --locked -p codex-cli --bin codex tcp_tunnel_is_unavailable_without_aix_quic_support -- --nocapture
fi

codex_bin=${CODEX_AIX_BIN:-$CARGO_TARGET_DIR/debug/codex}
for mode in text restricted restricted-patch denied-escalation unsandboxed; do
    python3 "$script_dir/mock-responses.py" --mode "$mode" --codex-bin "$codex_bin"
done
