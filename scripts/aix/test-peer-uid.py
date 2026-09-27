#!/usr/bin/env python3
"""Check AIX getpeereid on the pathname Unix sockets used by IDE IPC."""

import ctypes
import os
import socket
import tempfile


def peer_uid(sock: socket.socket) -> int:
    uid = ctypes.c_uint()
    gid = ctypes.c_uint()
    getpeereid = ctypes.CDLL(None, use_errno=True).getpeereid
    getpeereid.argtypes = [
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_uint),
        ctypes.POINTER(ctypes.c_uint),
    ]
    getpeereid.restype = ctypes.c_int
    if getpeereid(sock.fileno(), ctypes.byref(uid), ctypes.byref(gid)) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return uid.value


with tempfile.TemporaryDirectory() as temp_dir:
    path = os.path.join(temp_dir, "peer.sock")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
        listener.bind(path)
        listener.listen(1)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(path)
            server, _ = listener.accept()
            with server:
                expected_uid = os.getuid()
                assert peer_uid(client) == expected_uid
                assert peer_uid(server) == expected_uid

print("AIX pathname Unix-socket peer UID: PASS")
