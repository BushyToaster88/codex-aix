# Codex CLI on AIX

This directory contains the AIX 7.3 / POWER port of the Codex CLI and agent
harness. It was built and smoke-tested natively on POWER8 with the IBM Open SDK
for Rust/Cargo 1.96.1 and AIX Toolbox GCC/G++ 13.3.0.

## Build and run

Install Rust/Cargo, GCC/G++, Python 3, `patch`, `git`, `protoc`, and the
`EN_US.UTF-8` locale (AIX filesets `bos.loc.utf.EN_US` and `bos.loc.com.utf`).
Use an unprivileged account with enough free disk space and paging space.
The scripts expect AIX Toolbox programs under `/opt/freeware/bin` and default
the Cargo cache and target directory to `/codex-build`; set `CARGO_HOME` and
`CARGO_TARGET_DIR` to use other locations.

From the repository root:

```sh
sh scripts/aix/build-cli.sh
sh scripts/aix/test-native.sh
sh scripts/aix/run-codex.sh --version
```

`build-cli.sh` fetches locked dependencies, applies checksum-verified AIX
patches to nine pinned Cargo releases, builds the CLI, and checks `--version`.
The patches affect the local Cargo source cache; they do not change dependency
resolution. Once the cache is populated, `CODEX_AIX_SKIP_FETCH=1` skips the
workspace-wide fetch. Set `CARGO_NET_OFFLINE=true` as well for an offline build.
`test-native.sh` runs focused native unit tests and five credential-free,
loopback-only mock agent checks. `CODEX_AIX_FULL_TESTS=1` enables two additional
large test binaries that may need more than 512 MB of paging space. Set
`CODEX_AIX_BIN` to override the wrapper/test binary path.

The TUI works on an AIX terminal, including PTY input and terminal clipboard
copy via OSC 52/tmux. Native clipboard reads and image paste are unavailable.
The hidden HTTP/3 `tcp-tunnel` CLI subcommand is excluded on AIX. The default
native test suite and offline build wrapper passed on the tested AIX host; a
real model-authenticated session has **not** been tested.

## Security boundary

There is no AIX OS sandbox backend. Restricted native command execution and
the filesystem helper fail closed; these checks do not constitute an AIX
sandbox. To let an agent run local commands, an operator must explicitly use
`-s danger-full-access`, which grants the agent everything its Unix account
can access. Use only an unprivileged, isolated account and a disposable work
directory. Do not run the build or agent as root. The wrapper does not relax
sandbox settings or store credentials.

For private authentication on a headless machine, use `codex login --device-auth`
if your account supports it. Keep login codes and `auth.json` out of logs and
this repository.
