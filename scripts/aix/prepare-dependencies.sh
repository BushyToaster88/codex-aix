#!/bin/sh
# Apply checksum-verified AIX compatibility fixes to pinned Cargo releases.
set -eu

if [ -z "${CARGO_HOME:-}" ]; then
    echo 'Set CARGO_HOME before running this script.' >&2
    exit 1
fi

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd -P)

prepare_crate() {
    package=$1
    source_file=$2
    original_cksum=$3
    patched_cksum=$4

    set -- "$CARGO_HOME"/registry/src/*/"$package"
    if [ "$#" -ne 1 ] || [ ! -d "$1" ]; then
        echo "Expected exactly one fetched $package source tree." >&2
        exit 1
    fi
    crate_dir=$1
    set -- $(cksum "$crate_dir/$source_file")
    case "$1:$2" in
        "$patched_cksum")
            echo "$package AIX patch is already applied."
            return
            ;;
        "$original_cksum")
            ;;
        *)
            echo "Unexpected $package source; refusing to patch." >&2
            exit 1
            ;;
    esac

    (cd "$crate_dir" && patch -p0 < "$script_dir/$package.patch")
    set -- $(cksum "$crate_dir/$source_file")
    if [ "$1:$2" != "$patched_cksum" ]; then
        echo "$package patch output did not match the verified source." >&2
        exit 1
    fi
    echo "Applied $package AIX patch."
}

# Upstream byteorder issue: https://github.com/BurntSushi/byteorder/pull/223
prepare_crate byteorder-1.5.0 src/lib.rs 187437046:106597 2731723507:107224
# socket2 exposes neither keepalive interval nor retry setters on AIX.
prepare_crate rama-net-0.3.0-alpha.4 src/socket/opts.rs 334598913:48441 2648849369:48853
# nix 0.28 expects a libc::sigaction union removed from the pinned libc ABI;
# newer nix releases use the common sa_sigaction field for AIX too.
prepare_crate nix-0.28.0 src/sys/signal.rs 1978358326:52106 2857246806:50523
# AIX exposes TIOCGWINSZ through libc::ioctl; nix 0.28 omits its ioctl macro
# and calls the would-block errno EAGAIN on this target.
prepare_crate rustyline-14.0.0 src/tty/unix.rs 1980373394:63662 3579788020:64028
# AIX has posix_openpt and acquires a controlling terminal by opening the
# slave after setsid, but libc does not expose openpty or TIOCSCTTY there.
prepare_crate portable-pty-0.9.0 src/unix.rs 1634569915:12978 3587462140:15748
# socket2 reports a u32 address length; AIX getnameinfo takes size_t.
prepare_crate dns-lookup-3.0.1 src/nameinfo.rs 2556903883:2927 600779793:2999
# tree-sitter's bundled endian header lacks AIX, despite GCC exposing exact
# __BYTE_ORDER__ and __ORDER_*_ENDIAN__ values for the target.
prepare_crate tree-sitter-0.25.10 src/portable/endian.h 2866510977:6856 2529646176:7986
# The pinned AIX libc loadquery binding takes void*, not char*.
prepare_crate backtrace-0.3.76 src/symbolize/gimli/libs_aix.rs 1028025627:3042 1515115055:3042
# AIX cfmakeraw leaves VEOF/VEOL values in the aliased VMIN/VTIME slots,
# buffering short TUI key sequences instead of reporting each key promptly.
prepare_crate rustix-1.1.4 src/backend/libc/termios/syscalls.rs 3289473950:18502 1186650177:18810
