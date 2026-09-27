#!/usr/bin/env python3
"""Small loopback Responses API fixture for native Codex smoke tests.

This is a scripted protocol peer, not a model. It never forwards requests or
needs credentials. The command probe only prints a fixed marker.
"""

import argparse
import json
import os
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer


CALL_ID = "aix-smoke-call"
MARKER = "AIX_CODEX_EXEC_OK"


def event(value):
    return f"event: {value['type']}\ndata: {json.dumps(value)}\n\n"


def response(response_id, item):
    events = [
        {"type": "response.created", "response": {"id": response_id}},
        {"type": "response.output_item.done", "item": item},
        {
            "type": "response.completed",
            "response": {
                "id": response_id,
                "usage": {
                    "input_tokens": 0,
                    "input_tokens_details": None,
                    "output_tokens": 0,
                    "output_tokens_details": None,
                    "total_tokens": 0,
                },
            },
        },
    ]
    return "".join(map(event, events)).encode()


def message(text):
    return {
        "type": "message",
        "role": "assistant",
        "id": "aix-smoke-message",
        "content": [{"type": "output_text", "text": text}],
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        if self.path != "/v1/models":
            self.send_error(404)
            return
        body = b'{"data":[]}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/v1/responses":
            self.send_error(404)
            return
        try:
            content_length = int(self.headers["Content-Length"])
            request = json.loads(self.rfile.read(content_length))
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            self.server.failure = f"invalid request: {error}"
            self.send_error(400)
            return

        self.server.posts += 1
        mode = self.server.mode
        if self.server.posts == 1:
            if mode == "text":
                item = message("AIX_CODEX_TEXT_OK")
            else:
                arguments = {"cmd": f"printf {MARKER}", "login": False}
                if mode == "denied-escalation":
                    arguments["sandbox_permissions"] = "require_escalated"
                    arguments["justification"] = "Check approval denial in the smoke test."
                if mode == "restricted-patch":
                    arguments["cmd"] = (
                        "apply_patch <<'PATCH'\n"
                        "*** Begin Patch\n"
                        "*** Add File: aix-smoke-patch.txt\n"
                        f"+{MARKER}\n"
                        "*** End Patch\n"
                        "PATCH"
                    )
                item = {
                    "type": "function_call",
                    "call_id": CALL_ID,
                    "name": "exec_command",
                    "arguments": json.dumps(arguments),
                }
        elif self.server.posts == 2 and mode != "text":
            outputs = [
                entry.get("output", "")
                for entry in request.get("input", [])
                if entry.get("type") == "function_call_output"
                and entry.get("call_id") == CALL_ID
            ]
            output = "\n".join(map(str, outputs))
            if mode == "restricted":
                passed = "cannot enforce a native sandbox on AIX" in output
                passed = passed and MARKER not in output
            elif mode == "restricted-patch":
                patch_path = os.path.join(self.server.workspace, "aix-smoke-patch.txt")
                passed = bool(outputs) and not os.path.exists(patch_path)
                passed = passed and any(
                    word in output.lower()
                    for word in ("rejected", "blocked", "cannot enforce", "error")
                )
            elif mode == "denied-escalation":
                passed = bool(outputs) and MARKER not in output
                passed = passed and "approval" in output.lower()
            else:
                passed = MARKER in output
            self.server.passed = passed
            item = message("AIX_CODEX_TOOL_OK" if passed else "AIX_CODEX_TOOL_FAILED")
        else:
            self.server.failure = "unexpected extra request"
            item = message("AIX_CODEX_TOOL_FAILED")

        body = response(f"aix-smoke-{self.server.posts}", item)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("text", "restricted", "restricted-patch", "denied-escalation", "unsandboxed"),
        required=True,
    )
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--codex-bin", help="run this Codex executable against the fixture")
    args = parser.parse_args()
    server = HTTPServer(("127.0.0.1", args.port), Handler)
    server.mode = args.mode
    server.posts = 0
    server.passed = args.mode == "text"
    server.failure = None
    print(f"PORT:{server.server_port}", flush=True)
    expected = 1 if args.mode == "text" else 2
    if args.codex_bin:
        if os.geteuid() == 0:
            parser.error("run the Codex smoke test as an unprivileged user")
        codex_bin = os.path.abspath(args.codex_bin)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix="codex-aix-smoke-") as workspace:
                server.workspace = workspace
                env = os.environ.copy()
                env["CODEX_HOME"] = workspace
                env["NO_PROXY"] = "127.0.0.1,localhost"
                env["no_proxy"] = "127.0.0.1,localhost"
                if os.uname().sysname == "AIX":
                    env["PATH"] = "/opt/freeware/bin:/usr/bin:/etc:/usr/sbin:/usr/ucb:/sbin"
                    env["LC_ALL"] = "EN_US.UTF-8"
                for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "CHATGPT_API_KEY"):
                    env.pop(key, None)
                provider = (
                    '{name="local",base_url="http://127.0.0.1:'
                    f'{server.server_port}/v1",wire_api="responses"}}'
                )
                command = [
                    codex_bin,
                    "exec",
                    "--ignore-user-config",
                    "--ephemeral",
                    "--skip-git-repo-check",
                    "-C",
                    workspace,
                    "-s",
                    "danger-full-access" if args.mode == "unsandboxed" else "read-only",
                    "-m",
                    "test-model",
                    "-c",
                    'model_provider="local"',
                    "-c",
                    f"model_providers.local={provider}",
                    "-c",
                    "features.plugins=false",
                    "-c",
                    "check_for_update_on_startup=false",
                    "--json",
                    "Complete the scripted smoke test.",
                ]
                run = subprocess.run(
                    command,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=90,
                    check=False,
                )
        except subprocess.TimeoutExpired:
            server.failure = "Codex timed out"
            run = None
        finally:
            server.shutdown()
            thread.join()
        marker = "AIX_CODEX_TEXT_OK" if args.mode == "text" else "AIX_CODEX_TOOL_OK"
        cli_passed = run is not None and run.returncode == 0 and marker in run.stdout
        if not cli_passed and run is not None:
            print(run.stdout[-4000:], flush=True)
            print(run.stderr[-4000:], flush=True)
    else:
        server.timeout = 2
        deadline = time.monotonic() + 120
        while server.posts < expected and server.failure is None and time.monotonic() < deadline:
            server.handle_request()
        cli_passed = True
    server.server_close()
    passed = server.failure is None and server.posts == expected and server.passed and cli_passed
    print(f"RESULT:{'PASS' if passed else 'FAIL'} posts={server.posts}", flush=True)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
