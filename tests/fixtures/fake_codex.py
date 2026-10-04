"""Offline subprocess peer; exercise real pipes, handshake, and cleanup."""

import json
import os
import sys
import time
from pathlib import Path

Path(os.environ["FAKE_CODEX_PID_FILE"]).write_text(str(os.getpid()))
mode = os.environ.get("FAKE_CODEX_MODE", "success")
if mode == "timeout":
    time.sleep(60)
if mode == "eof":
    sys.exit(0)
assert sys.argv[1:] == ["app-server", "--listen", "stdio://"]
initialize = json.loads(sys.stdin.readline())
assert initialize["method"] == "initialize"
print(json.dumps({"id": 1, "result": {}}), flush=True)
assert json.loads(sys.stdin.readline())["method"] == "initialized"
request = json.loads(sys.stdin.readline())
assert request == {"id": 2, "method": "account/rateLimits/read"}
if mode == "malformed":
    print("not json", flush=True)
elif mode == "oversized":
    print("x" * 1000000, flush=True)
elif mode == "nonobject":
    print("[]", flush=True)
elif mode == "wrong_id":
    print('{"id":3,"result":{}}', flush=True)
elif mode == "bool_id":
    print('{"id":true,"result":{}}', flush=True)
elif mode == "rpc_error":
    print('{"id":2,"error":{"message":"secret-token-example"}}', flush=True)
elif mode == "no_result":
    print('{"id":2}', flush=True)
elif mode == "flood":
    for _ in range(100):
        print('{"method":"notification"}', flush=True)
else:
    print('{"method":"notification"}', flush=True)
    print(
        json.dumps(
            {
                "id": 2,
                "result": {
                    "rateLimits": {
                        "limitId": "codex",
                        "primary": {"windowDurationMins": 300, "usedPercent": 10},
                        "secondary": {"windowDurationMins": 10080, "usedPercent": 20},
                    }
                },
            }
        ),
        flush=True,
    )
time.sleep(60)  # Client must terminate/reap the peer, including successful reads.
