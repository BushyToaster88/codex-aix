# Codex CLI on AIX

This fork contains an experimental AIX 7.3 / POWER port of the Codex CLI and
agent harness. It was built and smoke-tested natively on POWER8 with IBM Open
SDK for Rust/Cargo 1.96.1 and AIX Toolbox GCC/G++ 13.3.0. There is no AIX
binary in the standard Codex installers: build this fork on AIX instead.

## Prerequisites

- AIX 7.3 on POWER, an **unprivileged** build/run account, and a spacious
  filesystem for the checkout, Cargo cache, and build output. The tested host
  used a dedicated 32 GB filesystem. A debug executable was about 1.57 GB.
- AIX Toolbox Rust/Cargo, GCC/G++, Python 3, `git`, `patch`, and `protoc` under
  `/opt/freeware/bin`.
- The `EN_US.UTF-8` locale. On the tested host this required AIX installation
  media filesets `bos.loc.utf.EN_US` and `bos.loc.com.utf`. Check with
  `LC_ALL=EN_US.UTF-8 locale charmap`; it must print `UTF-8`.

Do not compile Cargo dependencies or run the agent as root. The scripts default
`CARGO_HOME` to `/codex-build/cargo-home` and `CARGO_TARGET_DIR` to
`/codex-build/target`; set these variables to other writable, sufficiently
large locations if you do not have that layout.
Check `ulimit -f` for the build account too: its permitted file size must
exceed the executable size (about 1.57 GB on the tested build).

## Build and test as the unprivileged account

The fork's default branch is `aix-port`. From a writable directory:

```sh
export PATH=/opt/freeware/bin:/usr/bin:/etc:/usr/sbin:/usr/ucb:/sbin
export LC_ALL=EN_US.UTF-8
git clone --filter=blob:none --sparse https://github.com/BushyToaster88/codex-aix.git
cd codex-aix
git sparse-checkout set codex-rs scripts/aix
sh scripts/aix/build-cli.sh
sh scripts/aix/test-native.sh
```

`build-cli.sh` fetches locked dependencies, applies checksum-verified AIX
patches to nine pinned Cargo releases, builds the native XCOFF executable,
and checks `--version`. The patches change only the local Cargo source cache,
not dependency resolution. If the cache is fully populated,
`CODEX_AIX_SKIP_FETCH=1` skips the workspace-wide fetch; set
`CARGO_NET_OFFLINE=true` as well to prohibit network access.

`test-native.sh` runs focused AIX unit tests and five loopback-only mock agent
checks without model credentials. `CODEX_AIX_FULL_TESTS=1` enables two larger
test binaries that may require more than 512 MB of paging space. Set
`CODEX_AIX_BIN` if the built binary is not at the default target path.

## Install the native binary

These are the steps used on the tested host. The commands assume the default
`CARGO_TARGET_DIR` and an otherwise unused `/usr/bin/codex`. Perform this
section as root **after** building as the unprivileged account. Check for an
existing installation before replacing anything.

First ensure `/opt` can hold the executable; check the volume group's free
physical partitions before resizing. On the tested host `/opt` needed another
4 GB, its logical volume belonged to `rootvg`, and that volume group had
ample free space. Confirm those details on your own machine:

```sh
df -g /opt
lsfs -q /opt
lsvg rootvg
lsvg -l rootvg
# Only if needed and rootvg has enough free space:
chfs -a size=+4G /opt
```

An AIX root shell may also have a 1 GB file-size limit. Raise the hard and
soft limits for this install shell, then copy and verify the full binary:

```sh
ulimit -Hf unlimited
ulimit -Sf unlimited
ls -l /opt/freeware/bin/codex /usr/bin/codex  # Stop if either already exists.
cp /codex-build/target/debug/codex /opt/freeware/bin/codex.new
cksum /codex-build/target/debug/codex /opt/freeware/bin/codex.new
# Verify both checksum AND byte count match before continuing.
chown root:system /opt/freeware/bin/codex.new
chmod 755 /opt/freeware/bin/codex.new
mv /opt/freeware/bin/codex.new /opt/freeware/bin/codex
ln -s /opt/freeware/bin/codex /usr/bin/codex
```

The `/usr/bin` link makes `codex` resolve from the default AIX login `PATH`;
the installed target is the native XCOFF executable, not an alias or a shell
wrapper. If your build used another `CARGO_TARGET_DIR`, replace the source
path above. A future update should use the same temporary-file and checksum
procedure, after checking the existing installation.

## Run as an unprivileged user

Configure that account's `~/.profile` for the Toolbox tools and UTF-8 locale.
For example, adapt its existing `PATH` assignment to include `/opt/freeware/bin`
and exclude the current directory (`.`), then add:

```sh
LC_ALL=EN_US.UTF-8
export PATH LC_ALL
```

Start a fresh login session as that account and check:

```sh
locale charmap                 # UTF-8
command -v codex              # /opt/freeware/bin/codex or /usr/bin/codex
codex --version
codex --help
codex
```

If your prompt is `#`, check `id`: do not run the agent as root. On a headless
host, `codex login --device-auth` is an option if your account supports it;
complete authentication privately. Never put device codes or `auth.json` in
this repository or in logs.

The TUI and immediate PTY keyboard input were checked on AIX. OSC 52/tmux
terminal clipboard copy works, but native clipboard reads and image paste are
unavailable. The hidden HTTP/3 `tcp-tunnel` command is excluded. The default
native test suite and offline build wrapper passed; a real model-authenticated
session has **not** yet been tested.

## Security boundary

There is no AIX OS sandbox backend. Restricted native command execution and
the filesystem helper fail closed, but these checks do not constitute an AIX
sandbox. To let an agent run local commands, an operator must explicitly use
`-s danger-full-access`, which grants it everything the unprivileged Unix
account can access. Use an isolated account and disposable work directory,
without privileged access or sensitive files. Do not run the agent as root.
